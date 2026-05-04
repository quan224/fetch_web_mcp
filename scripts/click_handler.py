"""
点击页面内容 handler

参数:
  url          - 必填，目标网页地址（同域名会复用已有标签页）
  clicked_item - 必填，要点击的元素定位器，支持以下 Playwright 选择器格式:
      1. CSS 选择器:   "button.submit"、"a[href='/login']"、"#btn-ok"
      2. 文本内容:      "点击这里"、"Submit"（精确匹配按钮/链接上的文字）
      3. 文本模糊匹配: "text=登录"（包含"登录"文字的元素）
      4. XPath:         "//button[@type='submit']"
      5. 组合选择器:    "div.card >> text=详情"（先定位 div.card，再在其中匹配文字）
      6. 无障碍角色:    "role=button[name='确认']"
      7. 测试属性:      "[data-testid='submit-btn']"
  browser_path - 可选，浏览器可执行文件路径
"""

import time
from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager


class ClickHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "click"

    @classmethod
    def handle(cls, prop_info: SPropInfo):
        if not len(prop_info.value):
            print("错误: 请提供URL参数")
            return

        url = prop_info.value[0]
        clicked_item = prop_info.value[1]
        browser_path = prop_info.value[2] if len(prop_info.value) >= 3 else None
        is_headless = prop_info.value[3].lower() == "true" if len(prop_info.value) >= 4 else False

        try:
            with BrowserManager.context(browser_path, is_headless) as mb:
                page = mb.open(url)
                locator = page.locator(clicked_item).first

                # 检查元素是否存在
                if locator.count() == 0:
                    print(f"错误: 未找到匹配 '{clicked_item}' 的元素")
                    return

                # 获取元素信息用于反馈
                tag_name = locator.evaluate("el => el.tagName.toLowerCase()")
                href = locator.evaluate(
                    "el => { const a = el.closest('a') || (el.tagName === 'A' ? el : null); return a ? a.href : ''; }"
                )
                text_content = locator.inner_text().strip()[:80]

                print(f"元素: <{tag_name}> \"{text_content}\"")
                if href:
                    print(f"链接: {href}")

                # 滚动到可见区域
                locator.scroll_into_view_if_needed()
                # 确保元素可见
                if not locator.is_visible():
                    print("警告: 元素存在但不可见，尝试强制点击")

                # 记录点击前状态
                url_before = page.url
                pages_count_before = len(mb._context.pages)

                # 执行点击
                try:
                    locator.click(timeout=5000)
                except Exception as click_err:
                    print(f"点击失败: {click_err}")
                    return

                print("点击已执行")

                # 只有链接元素才需要等待导航
                is_link = bool(href)
                if not is_link:
                    return

                # 等待导航生效
                time.sleep(1.5)

                # 检查是否有新标签页（target="_blank" 场景）
                pages_count_after = len(mb._context.pages)
                if pages_count_after > pages_count_before:
                    new_page = mb._context.pages[-1]
                    try:
                        new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except Exception:
                        pass
                    new_url = new_page.evaluate("document.location.href")
                    new_title = new_page.title()
                    print(f"新标签页: {new_title}")
                    print(f"URL: {new_url}")
                    domain = mb._get_domain(new_url)
                    if domain:
                        mb._pages[domain] = new_page
                    return

                # 从 DOM 获取真实 URL（CDP 模式下 page.url 可能不同步）
                url_after = page.evaluate("document.location.href")
                if url_after.rstrip("/") != url_before.rstrip("/"):
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except Exception:
                        pass
                    print(f"页面已跳转: {page.title()}")
                    print(f"URL: {url_after}")
                else:
                    print("链接点击未触发导航（可能需要登录，或被页面拦截）")

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(ClickHandler)
