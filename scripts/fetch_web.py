import sys
import os

# 强制 UTF-8 输出（兼容 PyInstaller 打包）
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


class SPropInfo:

    def __init__(self):
        self.handle_type=""
        self.value=[]


class HandlerBase:

    @classmethod
    def handle_type(cls):
        return ""
    
    @classmethod
    def handle(cls, prop_info):
        pass


class HandleCommandFactory:

    HANDLERS = {}

    @classmethod
    def register_handle(cls, handler):
        if handler.handle_type() and handler.handle_type() not in cls.HANDLERS:
            cls.HANDLERS[handler.handle_type()]=handler

    @classmethod
    def handle(cls, prop_info):
        handler = cls.HANDLERS.get(prop_info.handle_type, None)
        if handler:
            handler.handle(prop_info)
        else:
            print("错误: 未知命令")
            sys.exit(1)


# 确保被其他模块 import 时拿到的是同一个实例
# 必须放在类定义之后、handler import 之前
sys.modules['fetch_web'] = sys.modules['__main__']

# 静态导入所有 handler（兼容 PyInstaller 打包）
from click_handler import ClickHandler
from close_ads_handler import CloseAdsHandler
from close_page_handler import ClosePageHandler
from close_popup_handler import ClosePopupHandler
from content_handler import ContentHandler
from detect_ads_handler import DetectAdsHandler
from detect_popups_handler import DetectPopupsHandler
from extract_handler import ExtractHandler
from fill_handler import FillHandler
from list_handler import ListHandler
from navigate_handler import NavigateHandler
from screenshot_handler import ScreenshotHandler
from scroll_handler import ScrollHandler
from shutdown_handler import ShutdownHandler

# 注册所有 handler
for _h in [ClickHandler, CloseAdsHandler, ClosePageHandler, ClosePopupHandler,
           ContentHandler, DetectAdsHandler, DetectPopupsHandler, ExtractHandler,
           FillHandler, ListHandler, NavigateHandler, ScreenshotHandler,
           ScrollHandler, ShutdownHandler]:
    HandleCommandFactory.register_handle(_h)

def main():
    import json as _json
    if len(sys.argv) < 2:
        print("错误: 参数错误")
        sys.exit(1)

    prop_info = SPropInfo()

    # 支持通过 JSON 文件传参（避免命令行中文编码问题）
    arg1 = sys.argv[1]
    if arg1.endswith(".json") and os.path.isfile(arg1):
        with open(arg1, 'r', encoding='utf-8') as f:
            args = _json.load(f)
        prop_info.handle_type = args[0]
        prop_info.value = args[1:]
    else:
        prop_info.handle_type = arg1
        prop_info.value = sys.argv[2:]

    HandleCommandFactory.handle(prop_info)

main()
