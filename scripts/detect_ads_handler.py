"""
广告元素检测 handler

扫描页面中所有广告元素，返回每个广告的选择器、尺寸、位置等信息，
由 AI 决定隐藏哪些。

参数:
  url          - 必填，目标网页地址
  browser_path - 可选，浏览器可执行文件路径
"""

import json
from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager, PopupHandler


class DetectAdsHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "detect_ads"

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
                ads = []

                for sel in PopupHandler.AD_SELECTORS:
                    try:
                        count = page.locator(sel).count()
                        for i in range(count):
                            loc = page.locator(sel).nth(i)

                            # 获取元素信息
                            info = loc.evaluate("""(el) => {
                                const rect = el.getBoundingClientRect();
                                return {
                                    tag: el.tagName.toLowerCase(),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height),
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                    className: (el.className || '').substring(0, 100),
                                    id: el.id || '',
                                    text: (el.innerText || '').substring(0, 80),
                                    visible: rect.width > 0 && rect.height > 0,
                                };
                            }""")

                            if not info.get("visible"):
                                continue

                            ads.append({
                                "index": len(ads),
                                "selector": f"{sel} >> nth={i}",
                                "css_selector": sel,
                                "nth": i,
                                **info,
                            })
                    except Exception:
                        continue

                if not ads:
                    print("未检测到广告元素")
                else:
                    print(json.dumps(ads, ensure_ascii=False, indent=2))

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(DetectAdsHandler)
