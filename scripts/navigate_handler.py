"""
页面导航 handler
  url          - 必填，要导航到的网页地址
  browser_path - 可选，浏览器可执行文件路径
"""

from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager


class NavigateHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "navigate"

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
                title = page.title()
                print(f"状态码: ok")
                print(f"页面标题: {title}")
                # 显示所有标签页
                pages = mb.list_pages()
                if len(pages) > 1:
                    print(f"已打开 {len(pages)} 个标签页: {', '.join(p['domain'] for p in pages)}")
        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(NavigateHandler)
