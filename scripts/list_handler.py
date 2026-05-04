"""
标签页列表 handler
  browser_path - 可选，浏览器可执行文件路径

列出当前浏览器中所有打开的标签页。
"""

from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager


class ListHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "list_pages"

    @classmethod
    def handle(cls, prop_info: SPropInfo):
        browser_path = prop_info.value[0] if len(prop_info.value) >= 1 else None
        is_headless = prop_info.value[1].lower() == "true" if len(prop_info.value) >= 2 else False

        try:
            with BrowserManager.context(browser_path, is_headless) as mb:
                pages = mb.list_pages()
                if not pages:
                    print("当前没有打开的标签页")
                else:
                    print(f"共 {len(pages)} 个标签页:")
                    for i, p in enumerate(pages, 1):
                        print(f"  [{i}] {p['domain']} - {p['title']}")
        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(ListHandler)
