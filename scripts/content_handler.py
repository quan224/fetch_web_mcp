"""
页面内容获取 handler
  url          - 必填，目标网页地址（同域名会复用已有标签页）
  browser_path - 可选，浏览器可执行文件路径

获取页面的可见文本内容 + 可交互元素列表。
"""

from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager

# 在浏览器中执行的 JS：提取所有可交互元素
_EXTRACT_INTERACTABLES = """() => {
    const items = [];
    // 链接
    document.querySelectorAll('a[href]').forEach(el => {
        const text = el.innerText.trim().slice(0, 60);
        if (text) items.push({tag: 'a', text: text, href: el.href});
    });
    // 按钮
    document.querySelectorAll('button, input[type=submit], input[type=button], [role=button]').forEach(el => {
        const text = (el.innerText || el.value || '').trim().slice(0, 60);
        if (text) items.push({tag: 'button', text: text});
    });
    // 输入框
    document.querySelectorAll('input[type=text], input[type=search], input[type=email], input[type=password], textarea, select').forEach(el => {
        const info = {tag: el.tagName.toLowerCase(), type: el.type || ''};
        if (el.name) info.name = el.name;
        if (el.placeholder) info.placeholder = el.placeholder;
        items.push(info);
    });
    return items.slice(0, 200);
}"""


class ContentHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "content"

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
                text = page.inner_text("body")
                interactables = page.evaluate(_EXTRACT_INTERACTABLES)

                print(f"页面标题: {title}")
                print(f"内容长度: {len(text)}")
                print(f"标签页数: {len(mb.list_pages())}")
                print("===")

                # 文本内容
                print("[页面文本]")
                print(text)
                print("===")

                # 可交互元素
                links = [i for i in interactables if i.get('tag') == 'a']
                buttons = [i for i in interactables if i.get('tag') == 'button']
                inputs = [i for i in interactables if i.get('tag') not in ('a', 'button')]

                print(f"[可交互元素] 共 {len(interactables)} 个")
                if buttons:
                    print(f"  按钮({len(buttons)}):")
                    for b in buttons:
                        print(f"    - {b['text']}")
                if inputs:
                    print(f"  输入框({len(inputs)}):")
                    for inp in inputs:
                        desc = inp.get('placeholder') or inp.get('name') or inp.get('type', '')
                        print(f"    - <{inp['tag']}> {desc}")
                if links:
                    print(f"  链接({len(links)}):")
                    for a in links:
                        print(f"    - {a['text']}  →  {a['href'][:80]}")

        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(ContentHandler)
