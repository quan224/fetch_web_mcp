"""
关闭标签页 handler

参数:
  url          - 必填，按域名匹配要关闭的标签页
  browser_path - 可选，浏览器可执行文件路径
"""

from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager


class ClosePageHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "close_page"

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
                if mb.close_page(url):
                    print(f"已关闭: {url}")
                    # 显示剩余标签页
                    pages = mb.list_pages()
                    if pages:
                        print(f"剩余 {len(pages)} 个标签页:")
                        for i, p in enumerate(pages, 1):
                            print(f"  [{i}] {p['domain']} - {p['title']}")
                    else:
                        print("已无标签页")
                else:
                    print(f"未找到匹配的标签页: {url}")

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(ClosePageHandler)
