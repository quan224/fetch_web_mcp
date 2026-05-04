"""
填写输入框 handler

参数:
  url          - 必填，目标网页地址
  selector     - 必填，输入框的 CSS 选择器
  value        - 必填，要填写的文本内容
  browser_path - 可选，浏览器可执行文件路径
"""

from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager


class FillHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "fill"

    @classmethod
    def handle(cls, prop_info: SPropInfo):
        if len(prop_info.value) < 3:
            print("错误: 请提供 url、selector 和 value 参数")
            return

        url = prop_info.value[0]
        selector = prop_info.value[1]
        value = prop_info.value[2]
        browser_path = prop_info.value[3] if len(prop_info.value) >= 4 else None
        is_headless = prop_info.value[4].lower() == "true" if len(prop_info.value) >= 5 else False

        try:
            with BrowserManager.context(browser_path, is_headless) as mb:
                page = mb.open(url)
                locator = page.locator(selector).first

                if locator.count() == 0:
                    print(f"错误: 未找到匹配 '{selector}' 的元素")
                    return

                tag_name = locator.evaluate("el => el.tagName.toLowerCase()")
                if tag_name not in ("input", "textarea", "select"):
                    print(f"警告: 目标元素是 <{tag_name}>，不是输入框")

                locator.fill(value)
                print(f"已填写: \"{value}\"")
                print(f"选择器: {selector}")

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(FillHandler)
