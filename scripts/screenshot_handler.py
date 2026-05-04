"""
页面截图 handler

参数:
  url          - 必填，目标网页地址
  selector     - 可选，CSS 选择器（截取特定元素，不传则截取整个页面）
  browser_path - 可选，浏览器可执行文件路径
"""

import os
from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager, SCREENSHOT_DIR


class ScreenshotHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "screenshot"

    @classmethod
    def handle(cls, prop_info: SPropInfo):
        if not len(prop_info.value):
            print("错误: 请提供URL参数")
            return

        url = prop_info.value[0]
        selector = prop_info.value[1] if len(prop_info.value) >= 2 and prop_info.value[1] else None
        browser_path = prop_info.value[2] if len(prop_info.value) >= 3 else None
        is_headless = prop_info.value[3].lower() == "true" if len(prop_info.value) >= 4 else False

        try:
            with BrowserManager.context(browser_path, is_headless) as mb:
                page = mb.open(url)
                title = page.title()

                # 截图保存到 screenshot 目录
                screenshot_dir = SCREENSHOT_DIR
                os.makedirs(screenshot_dir, exist_ok=True)
                import re
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', title)[:50]
                filename = f"screenshot_{safe_name}.png"
                filepath = os.path.join(screenshot_dir, filename)

                if selector:
                    # 截取特定元素
                    locator = page.locator(selector).first
                    if locator.count() == 0:
                        print(f"错误: 未找到匹配 '{selector}' 的元素")
                        return
                    locator.screenshot(path=filepath)
                    print(f"元素截图已保存: {filepath}")
                else:
                    # 截取整个页面
                    page.screenshot(path=filepath, full_page=True)
                    print(f"页面截图已保存: {filepath}")

                print(f"页面: {title}")

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(ScreenshotHandler)
