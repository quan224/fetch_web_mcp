"""
浏览器持久化管理器

通过 CDP（Chrome DevTools Protocol）管理一个长期运行的浏览器实例。
按域名管理标签页，相同域名复用已有标签页跳转，不同域名开新标签页。

用法：
    with BrowserManager.context() as browser:
        page = browser.open("https://www.bilibili.com")
        page = browser.open("https://www.baidu.com")      # 新标签页
        page = browser.open("https://www.bilibili.com/v/") # 复用 bilibili 标签页
        pages = browser.list_pages()                        # 列出所有标签页
"""

import os
import sys
import subprocess
import time
import urllib.request
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright


class PopupHandler:
    """弹窗检测与自动处理器

    支持三种弹窗类型：
    1. JS 原生对话框（alert/confirm/prompt）→ 自动 dismiss
    2. HTML/CSS 广告弹窗 → 自动点击关闭按钮
    3. 新标签页弹窗（window.open 广告）→ 自动关闭新标签
    """

    # 广告弹窗关闭按钮选择器（按优先级排列）
    CLOSE_SELECTORS = [
        "[class*='close' i]:not([class*='closest'])",
        "[class*='dismiss' i]",
        "[class*='btn-close' i]",
        "[aria-label='Close']", "[aria-label='关闭']",
        "[title='Close']", "[title='关闭']",
        "button.close", ".modal-close", ".popup-close",
    ]

    # 弹窗容器选择器
    OVERLAY_SELECTORS = [
        "[role='dialog']",
        "[class*='modal' i]:not(nav):not(header)",
        "[class*='popup' i]:not(nav)",
        "[class*='dialog' i]:not(nav):not(header)",
        "[class*='overlay' i]:not(nav)",
        "[class*='lightbox' i]",
        "[class*='float-layer' i]",
        "[class*='popover' i]:not(nav):not(header):not([class*='wrap'])",
        "[class*='login-panel' i]",
        "[class*='drawer' i]:not(nav)",
        "[class*='mask' i]",
    ]

    # 登录弹窗关键词
    LOGIN_KEYWORDS = ["登录", "登 录", "注册", "Login", "Sign in", "账号", "密码"]

    @classmethod
    def setup_dialog_handler(cls, page):
        """注册 JS 原生对话框自动关闭（类型 1）"""
        page.on("dialog", lambda dialog: dialog.dismiss())

    @classmethod
    def close_stray_tabs(cls, context, known_pages):
        """关闭非预期的标签页（类型 3：window.open 广告弹窗）

        遍历 context 中的所有页面，不在 known_pages 中的视为广告弹窗并关闭。
        """
        closed = 0
        for page in context.pages:
            if page not in known_pages and not page.is_closed():
                try:
                    page.close()
                    closed += 1
                except Exception:
                    pass
        return closed

    @classmethod
    def detect_popup(cls, page):
        """检测页面是否有弹窗，返回 {"has_popup", "type", "info"}"""
        try:
            for sel in cls.OVERLAY_SELECTORS:
                try:
                    loc = page.locator(sel).first
                    if not loc.is_visible(timeout=300):
                        continue

                    popup_text = loc.inner_text(timeout=500)
                    has_password = page.locator("input[type='password']").is_visible(timeout=300)
                    is_login = has_password or any(kw in popup_text for kw in cls.LOGIN_KEYWORDS)

                    if is_login:
                        return {"has_popup": True, "type": "login",
                                "info": "检测到登录弹窗"}
                    close_btn = cls._find_close_button(loc)
                    return {"has_popup": True, "type": "ad",
                            "info": f"检测到广告弹窗{'，已找到关闭按钮' if close_btn else '，未找到关闭按钮'}"}
                except Exception:
                    continue

            return {"has_popup": False, "type": None, "info": ""}
        except Exception as e:
            return {"has_popup": False, "type": None, "info": f"检测异常: {e}"}

    @classmethod
    def _find_close_button(cls, scope):
        """在指定范围内查找关闭按钮"""
        for sel in cls.CLOSE_SELECTORS:
            try:
                loc = scope.locator(sel).first
                if loc.is_visible(timeout=200):
                    return loc
            except Exception:
                continue
        return None

    @classmethod
    def close_popup(cls, page):
        """尝试关闭页面弹窗（类型 2），返回 {"closed", "type", "info"}"""
        popup = cls.detect_popup(page)
        if not popup["has_popup"]:
            return {"closed": False, "type": None, "info": "未检测到弹窗"}

        if popup["type"] == "login":
            return {"closed": False, "type": "login",
                    "info": "检测到登录弹窗，未自动关闭（需手动登录）"}

        # 尝试点击关闭按钮
        for sel in cls.OVERLAY_SELECTORS:
            try:
                overlay = page.locator(sel).first
                if not overlay.is_visible(timeout=200):
                    continue
                close_btn = cls._find_close_button(overlay)
                if close_btn:
                    close_btn.click(timeout=2000)
                    time.sleep(0.5)
                    after = cls.detect_popup(page)
                    if not after["has_popup"]:
                        return {"closed": True, "type": "ad", "info": "已关闭广告弹窗"}
            except Exception:
                continue

        # 尝试 Escape 键关闭
        try:
            page.keyboard.press("Escape")
            time.sleep(0.5)
            after = cls.detect_popup(page)
            if not after["has_popup"]:
                return {"closed": True, "type": "ad", "info": "已通过 Escape 关闭弹窗"}
        except Exception:
            pass

        return {"closed": False, "type": "ad", "info": "无法自动关闭弹窗"}

    # 常见广告元素选择器，注入 CSS 隐藏
    AD_SELECTORS = [
        "[class*='ad-guanggao' i]",
        "[class*='ad-banner' i]",
        "[class*='ad-float' i]",
        "[class*='ad-sidebar' i]",
        "[class*='sponsor' i]",
        "[class*='bd-side-sponsrs' i]",
        "[id*='ad-']",
        "[id*='google_ads']",
        "ins.adsbygoogle",
        ".ad-placement",
    ]

    @classmethod
    def remove_ads(cls, page):
        """通过 JS 直接隐藏广告元素，并注入 CSS 防止后续加载的广告"""
        js_hide = """
        (selectors) => {
            let hidden = 0;
            selectors.forEach(sel => {
                try {
                    document.querySelectorAll(sel).forEach(el => {
                        el.style.setProperty('display', 'none', 'important');
                        hidden++;
                    });
                } catch(e) {}
            });
            return hidden;
        }
        """
        try:
            count = page.evaluate(js_hide, cls.AD_SELECTORS)
            # 同时注入 CSS 规则防止动态加载的广告
            selectors = ", ".join(cls.AD_SELECTORS)
            css = f"{selectors} {{ display: none !important; }}"
            try:
                page.add_style_tag(content=css)
            except Exception:
                pass
            return count > 0
        except Exception:
            return False

    @classmethod
    def handle_page_popups(cls, page):
        """对页面执行完整的弹窗检测+处理+广告清理流程"""
        results = []

        # 类型 1：JS 对话框通过事件监听自动处理，无需额外操作

        # 类型 2：HTML/CSS 弹窗
        popup = cls.detect_popup(page)
        if popup["has_popup"]:
            if popup["type"] == "login":
                results.append(f"[弹窗] {popup['info']}")
            else:
                close_result = cls.close_popup(page)
                results.append(f"[弹窗] {close_result['info']}")

        # 广告元素隐藏
        if cls.remove_ads(page):
            results.append("[广告] 已隐藏页面广告元素")

        return results

DEBUG_PORT = 9222


def get_base_dir():
    """获取程序根目录，兼容 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
SCRIPT_DIR = BASE_DIR
USER_DATA_DIR = os.path.join(BASE_DIR, "__browser_profile")
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshot")
CDP_URL = f"http://localhost:{DEBUG_PORT}"


class ManagedBrowser:
    """对 Browser 的封装，提供按域名管理标签页的能力"""

    def __init__(self, browser, context):
        self._browser = browser
        self._context = context
        # domain → Page 的映射
        self._pages = {}
        # 从浏览器中恢复已有标签页的映射
        self._restore_pages()

    def _restore_pages(self):
        """连接浏览器时，扫描已有标签页重建 domain → page 映射"""
        for page in self._context.pages:
            try:
                url = page.url
                if url and url not in ("about:blank", ""):
                    domain = self._get_domain(url)
                    if domain and domain not in self._pages:
                        self._pages[domain] = page
            except Exception:
                pass

    def _get_domain(self, url):
        return urlparse(url).hostname or ""

    def open(self, url, wait_until="load", timeout=30000):
        """
        打开 URL。同域名复用已有标签页，不同域名新建标签页。
        返回对应的 Page 对象。
        """
        domain = self._get_domain(url)

        # 同域名 → 复用已有标签页跳转
        if domain in self._pages:
            page = self._pages[domain]
            if not page.is_closed():
                current_url = page.url.rstrip("/")
                target_url = url.rstrip("/")
                if current_url != target_url:
                    page.goto(url, wait_until=wait_until, timeout=timeout)
                return page

        # 查找 context 中已有的空闲标签页（空白页）
        existing = None
        for p in self._context.pages:
            if p not in self._pages.values() and not p.is_closed():
                existing = p
                break

        # 有空白页就复用，没有就新建
        if existing:
            page = existing
        else:
            page = self._context.new_page()

        page.goto(url, wait_until=wait_until, timeout=timeout)
        self._pages[domain] = page
        return page

    def get_page(self, url):
        """根据 URL 的域名获取已有标签页，没有返回 None"""
        domain = self._get_domain(url)
        page = self._pages.get(domain)
        if page and not page.is_closed():
            return page
        return None

    def list_pages(self):
        """
        列出所有标签页信息。
        返回列表，每项包含 domain, url, title。
        """
        result = []
        for domain, page in self._pages.items():
            if page.is_closed():
                continue
            try:
                result.append({
                    "domain": domain,
                    "url": page.url,
                    "title": page.title(),
                })
            except Exception:
                result.append({"domain": domain, "url": "(unknown)", "title": "(unknown)"})
        return result

    def close_page(self, url):
        """关闭指定域名的标签页"""
        domain = self._get_domain(url)
        page = self._pages.pop(domain, None)
        if page and not page.is_closed():
            page.close()
            return True
        return False


class BrowserManager:

    @classmethod
    def _is_cdp_available(cls):
        try:
            urllib.request.urlopen(f"http://localhost:{DEBUG_PORT}/json/version", timeout=2)
            return True
        except Exception:
            return False

    @classmethod
    def shutdown(cls):
        """通过 CDP 端口获取浏览器进程 PID 并终止"""
        # 查找占用 debug 端口的进程并终止
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, timeout=5
            )
            output = result.stdout.decode("gbk", errors="ignore")
            for line in output.splitlines():
                if f":{DEBUG_PORT}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
                    return True
        except Exception:
            pass

        return False

    @classmethod
    def _detect_browser(cls):
        """自动检测本地浏览器路径（Edge 优先，其次 Chrome）"""
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return None

    @classmethod
    def _start_browser(cls, browser_path=None, is_headless=False):
        exe_path = browser_path or cls._detect_browser() or "chrome"
        cmd = [
            exe_path,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={USER_DATA_DIR}",
            "--no-first-run",
        ]
        if is_headless:
            cmd.append("--headless=new")
        devnull = open(os.devnull, "w")
        subprocess.Popen(
            cmd,
            stdin=devnull, stdout=devnull, stderr=devnull,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        for _ in range(20):
            time.sleep(0.5)
            if cls._is_cdp_available():
                return True
        return False

    @classmethod
    def _connect(cls, pw):
        try:
            return pw.chromium.connect_over_cdp(CDP_URL)
        except Exception:
            return None

    @classmethod
    def _get_or_create_context(cls, browser):
        if browser.contexts:
            return browser.contexts[0]
        return browser.new_context()

    @classmethod
    def context(cls, browser_path=None, is_headless=False):
        """
        获取 ManagedBrowser 实例。

        使用方式：
            with BrowserManager.context() as mb:
                page = mb.open("https://www.bilibili.com")
                page = mb.open("https://www.baidu.com")
                info = mb.list_pages()
        """
        return _BrowserContext(browser_path, is_headless)


class _BrowserContext:

    def __init__(self, browser_path=None, is_headless=False):
        self.browser_path = browser_path
        self.is_headless = is_headless
        self._pw_cm = None
        self.managed = None

    def __enter__(self):
        self._pw_cm = sync_playwright()
        pw = self._pw_cm.__enter__()

        browser = BrowserManager._connect(pw)
        if browser is None:
            if not BrowserManager._start_browser(self.browser_path, self.is_headless):
                self._pw_cm.__exit__(None, None, None)
                raise RuntimeError("浏览器启动超时")
            time.sleep(1)
            browser = BrowserManager._connect(pw)

        if browser is None:
            self._pw_cm.__exit__(None, None, None)
            raise RuntimeError("无法连接浏览器")

        ctx = BrowserManager._get_or_create_context(browser)
        self.managed = ManagedBrowser(browser, ctx)
        return self.managed

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.managed and self.managed._browser:
            try:
                self.managed._browser.close()
            except Exception:
                pass
        if self._pw_cm:
            self._pw_cm.__exit__(exc_type, exc_val, exc_tb)
