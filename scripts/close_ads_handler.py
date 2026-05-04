"""
隐藏广告元素 handler

根据选择器隐藏页面中指定的广告元素（设置 display: none）。
支持隐藏单个广告或全部广告。

参数:
  url          - 必填，目标网页地址
  selector     - 可选，要隐藏的广告选择器（来自 detect_ads 返回的 selector）。
                 不传则隐藏所有匹配 AD_SELECTORS 的广告。
  browser_path - 可选，浏览器可执行文件路径
"""

from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager, PopupHandler


class CloseAdsHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "close_ads"

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

                if selector:
                    # 隐藏指定的广告元素
                    # 解析 "selector >> nth=N" 格式
                    parts = selector.split(" >> nth=")
                    css_sel = parts[0]
                    nth = int(parts[1]) if len(parts) > 1 else 0

                    hidden = page.evaluate("""([cssSel, nth]) => {
                        const els = document.querySelectorAll(cssSel);
                        if (nth < els.length) {
                            els[nth].style.setProperty('display', 'none', 'important');
                            return 1;
                        }
                        return 0;
                    }""", [css_sel, nth])

                    if hidden:
                        print(f"已隐藏广告: {selector}")
                    else:
                        print(f"未找到广告元素: {selector}")
                else:
                    # 隐藏所有匹配的广告
                    hidden = page.evaluate("""(selectors) => {
                        let count = 0;
                        selectors.forEach(sel => {
                            try {
                                document.querySelectorAll(sel).forEach(el => {
                                    el.style.setProperty('display', 'none', 'important');
                                    count++;
                                });
                            } catch(e) {}
                        });
                        return count;
                    }""", PopupHandler.AD_SELECTORS)

                    if hidden > 0:
                        print(f"已隐藏 {hidden} 个广告元素")
                    else:
                        print("未检测到广告元素")

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(CloseAdsHandler)
