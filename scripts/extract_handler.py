"""
数据提取 handler
  url          - 必填，目标网页地址
  selector     - 必填，CSS 选择器（提取该选择器匹配的所有元素）
  browser_path - 可选，浏览器可执行文件路径

对匹配的每个元素提取：文本内容、href、src 等常用属性。
"""

from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager


class ExtractHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "extract"

    @classmethod
    def handle(cls, prop_info: SPropInfo):
        if len(prop_info.value) < 2:
            print("错误: 请提供 url 和 selector 参数")
            return

        url = prop_info.value[0]
        selector = prop_info.value[1]
        browser_path = prop_info.value[2] if len(prop_info.value) >= 3 else None
        is_headless = prop_info.value[3].lower() == "true" if len(prop_info.value) >= 4 else False

        try:
            with BrowserManager.context(browser_path, is_headless) as mb:
                page = mb.open(url)
                title = page.title()
                elements = page.query_selector_all(selector)

                print(f"页面: {title}")
                print(f"选择器: {selector}")
                print(f"匹配数: {len(elements)}")
                print("===")

                for i, el in enumerate(elements, 1):
                    text = el.inner_text().strip()
                    # 提取常用属性
                    attrs = {}
                    for attr in ("href", "src", "data-src", "alt", "title", "value", "class"):
                        val = el.get_attribute(attr)
                        if val:
                            attrs[attr] = val

                    print(f"[{i}] {text[:200]}")
                    if attrs:
                        for k, v in attrs.items():
                            print(f"      {k}: {v[:120]}")

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(ExtractHandler)
