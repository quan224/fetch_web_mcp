"""
关闭弹窗 handler

根据选择器关闭页面中指定的弹窗，支持三种关闭方式：
1. 点击关闭按钮（需提供 close_button_selector）
2. 按 Escape 键关闭
3. 直接隐藏弹窗元素

参数:
  url                   - 必填，目标网页地址
  selector              - 必填，弹窗选择器（来自 detect_popups 返回的 selector）
  close_button_selector - 可选，关闭按钮选择器（来自 detect_popups 返回的 close_button_selector）
  method                - 可选，关闭方式: "button"（点击按钮）, "escape"（按 Escape）, "hide"（直接隐藏），默认 "button"
  browser_path          - 可选，浏览器可执行文件路径
"""

import time
from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager


class ClosePopupHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "close_popup"

    @classmethod
    def handle(cls, prop_info: SPropInfo):
        if len(prop_info.value) < 2:
            print("错误: 请提供 url 和 selector 参数")
            return

        url = prop_info.value[0]
        selector = prop_info.value[1]
        close_button_selector = prop_info.value[2] if len(prop_info.value) >= 3 and prop_info.value[2] else None
        method = prop_info.value[3] if len(prop_info.value) >= 4 and prop_info.value[3] else "button"
        browser_path = prop_info.value[4] if len(prop_info.value) >= 5 else None
        is_headless = prop_info.value[5].lower() == "true" if len(prop_info.value) >= 6 else False

        try:
            with BrowserManager.context(browser_path, is_headless) as mb:
                page = mb.open(url)

                # 解析 selector 中的 nth
                css_sel = selector.split(" >> nth=")[0]
                nth = int(selector.split(" >> nth=")[1]) if " >> nth=" in selector else 0
                popup_loc = page.locator(css_sel).nth(nth)

                if method == "button":
                    # 方式 1：点击关闭按钮（先在弹窗内找，再到页面找）
                    clicked = False
                    if close_button_selector:
                        # 优先在弹窗元素内查找
                        try:
                            btn = popup_loc.locator(close_button_selector).first
                            if btn.is_visible(timeout=1000):
                                btn.click(timeout=2000)
                                clicked = True
                                time.sleep(0.5)
                                print(f"已点击关闭按钮: {close_button_selector}")
                        except Exception:
                            pass

                        # 弹窗内没找到，尝试页面范围
                        if not clicked:
                            try:
                                btn = page.locator(close_button_selector).first
                                if btn.is_visible(timeout=1000):
                                    btn.click(timeout=2000)
                                    clicked = True
                                    time.sleep(0.5)
                                    print(f"已点击关闭按钮: {close_button_selector}")
                            except Exception:
                                pass

                    # 关闭按钮失败，自动 fallback 到 Escape
                    if not clicked:
                        try:
                            page.keyboard.press("Escape")
                            time.sleep(0.5)
                            print("关闭按钮不可用，已按 Escape 键")
                        except Exception as e:
                            print(f"Escape 也失败: {e}")

                elif method == "escape":
                    # 方式 2：按 Escape
                    try:
                        page.keyboard.press("Escape")
                        time.sleep(0.5)
                        print("已按 Escape 键")
                    except Exception as e:
                        print(f"按 Escape 失败: {e}")

                elif method == "hide":
                    # 方式 3：直接隐藏元素
                    try:
                        popup_loc.evaluate("el => el.style.setProperty('display', 'none', 'important')")
                        print(f"已隐藏弹窗元素: {selector}")
                    except Exception as e:
                        print(f"隐藏弹窗失败: {e}")

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(ClosePopupHandler)
