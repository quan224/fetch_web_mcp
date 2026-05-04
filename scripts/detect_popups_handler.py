"""
弹窗检测 handler

扫描页面中所有弹窗元素（对话框、模态框、overlay 等），
返回每个弹窗的类型、内容摘要、关闭按钮选择器等信息，
由 AI 决定关闭哪些。

参数:
  url          - 必填，目标网页地址
  browser_path - 可选，浏览器可执行文件路径
"""

import json
from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager, PopupHandler


class DetectPopupsHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "detect_popups"

    @classmethod
    def handle(cls, prop_info: SPropInfo):
        if not len(prop_info.value):
            print("错误: 请提供URL参数")
            return

        url = prop_info.value[0]
        browser_path = prop_info.value[1] if len(prop_info.value) >= 2 else None
        is_headless = prop_info.value[2].lower() == "true" if len(prop_info.value) >= 3 else False

        try:
            with BrowserManager.context(browser_path, is_headless) as mb:
                page = mb.open(url)
                popups = []

                for sel in PopupHandler.OVERLAY_SELECTORS:
                    try:
                        count = page.locator(sel).count()
                        for i in range(count):
                            loc = page.locator(sel).nth(i)
                            if not loc.is_visible(timeout=500):
                                continue

                            # 过滤：检查元素是否为 fixed/absolute 定位且有较高 z-index
                            is_popup = loc.evaluate("""(el) => {
                                const style = getComputedStyle(el);
                                const pos = style.position;
                                const zIndex = parseInt(style.zIndex) || 0;
                                // fixed 或 absolute 定位，且 z-index > 10
                                if ((pos === 'fixed' || pos === 'absolute') && zIndex > 10) return true;
                                // fixed 定位即使没有高 z-index 也可能是弹窗
                                if (pos === 'fixed') return true;
                                // 检查是否有遮罩层（背景半透明覆盖）
                                if (el.offsetWidth > window.innerWidth * 0.3 && el.offsetHeight > window.innerHeight * 0.3) return true;
                                return false;
                            }""")
                            if not is_popup:
                                continue

                            # 获取弹窗信息
                            text = ""
                            try:
                                text = loc.inner_text(timeout=500)[:200]
                            except Exception:
                                pass

                            # 判断是否登录弹窗
                            has_password = False
                            try:
                                pwd = loc.locator("input[type='password']")
                                has_password = pwd.count() > 0 and pwd.first.is_visible(timeout=300)
                            except Exception:
                                pass

                            is_login = has_password or any(kw in text for kw in PopupHandler.LOGIN_KEYWORDS)

                            # 查找关闭按钮
                            close_sel = None
                            for cs in PopupHandler.CLOSE_SELECTORS:
                                try:
                                    btn = loc.locator(cs).first
                                    if btn.is_visible(timeout=200):
                                        close_sel = cs
                                        break
                                except Exception:
                                    continue

                            # 生成弹窗内元素的唯一选择器（用于 close_popup 定位）
                            popup_sel = f"{sel} >> nth={i}"

                            popups.append({
                                "index": len(popups),
                                "selector": popup_sel,
                                "type": "login" if is_login else "ad_or_dialog",
                                "text_preview": text[:100] if text else "",
                                "close_button_selector": close_sel,
                                "has_close_button": close_sel is not None,
                            })
                    except Exception:
                        continue

                if not popups:
                    print("未检测到弹窗")
                else:
                    print(json.dumps(popups, ensure_ascii=False, indent=2))

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(DetectPopupsHandler)
