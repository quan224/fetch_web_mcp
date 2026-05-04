"""
页面滚动 handler

参数:
  url          - 必填，目标网页地址
  direction    - 必填，滚动方向 "up" 或 "down"
  distance     - 可选，滚动像素数（默认 500）
  browser_path - 可选，浏览器可执行文件路径
"""

from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager


class ScrollHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "scroll"

    @classmethod
    def handle(cls, prop_info: SPropInfo):
        if not len(prop_info.value):
            print("错误: 请提供URL参数")
            return

        url = prop_info.value[0]
        direction = prop_info.value[1] if len(prop_info.value) >= 2 else "down"
        distance = int(prop_info.value[2]) if len(prop_info.value) >= 3 and prop_info.value[2] else 500
        browser_path = prop_info.value[3] if len(prop_info.value) >= 4 else None
        is_headless = prop_info.value[4].lower() == "true" if len(prop_info.value) >= 5 else False

        if direction not in ("up", "down"):
            print(f"错误: direction 只支持 'up' 或 'down'，收到 '{direction}'")
            return

        try:
            with BrowserManager.context(browser_path, is_headless) as mb:
                page = mb.open(url)

                # 获取滚动前的位置
                scroll_before = page.evaluate("window.scrollY")

                # 执行滚动
                sign = -1 if direction == "up" else 1
                page.evaluate(f"window.scrollBy(0, {sign * distance})")

                scroll_after = page.evaluate("window.scrollY")
                actual_distance = abs(scroll_after - scroll_before)

                print(f"方向: {direction}")
                print(f"请求距离: {distance}px")
                print(f"实际滚动: {actual_distance}px")
                print(f"当前位置: {scroll_after}px")

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(ScrollHandler)
