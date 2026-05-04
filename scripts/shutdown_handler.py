"""
关闭浏览器 handler

参数:
  browser_path - 可选（本工具不使用此参数，保持接口一致）

彻底关闭浏览器进程，释放 CDP 调试端口。
"""

from fetch_web import SPropInfo, HandlerBase, HandleCommandFactory
from browser_manager import BrowserManager


class ShutdownHandler(HandlerBase):

    @classmethod
    def handle_type(cls):
        return "shutdown"

    @classmethod
    def handle(cls, prop_info: SPropInfo):
        try:
            if BrowserManager.shutdown():
                print("浏览器已关闭，CDP 端口已释放")
            else:
                print("未找到运行中的浏览器实例")
        except Exception as e:
            print(f"错误: {e}")


HandleCommandFactory.register_handle(ShutdownHandler)
