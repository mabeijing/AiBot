import socket
import subprocess
import sys
import time

from typing import List, Optional, Tuple

from loguru import logger


class _Point:

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __getitem__(self, item: int):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            raise IndexError("list index out of range")

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"

    # def __init__(self, x, y, driver: "WinBotMain"):
    #     self.x = x
    #     self.y = y
    #     self.__driver = driver
    #
    # def click(self, offset_x: float = 0, offset_y: float = 0):
    #     """
    #     点击坐标
    #     :param offset_x: 坐标 x 轴偏移量；
    #     :param offset_y: 坐标 y 轴偏移量；
    #     :return:
    #     """
    #     self.__driver.click(self, offset_x=offset_x, offset_y=offset_y)
    #
    # def get_points_center(self, other_point: "_Point") -> "_Point":
    #     """
    #     获取两个坐标点的中间坐标
    #     :param other_point: 其他的坐标点
    #     :return:
    #     """
    #     return self.__class__(x=self.x + (other_point.x - self.x) / 2, y=self.y + (other_point.y - self.y) / 2,
    #                           driver=self.__driver)


_Region = Tuple[float, float, float, float]
_Algorithm = Tuple[int, int, int]
_SubColors = List[Tuple[int, int, str]]


class WinBotMain:
    wait_timeout = 3  # seconds
    interval_timeout = 0.5  # seconds

    log_path = ""
    log_level = "DEBUG"
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | " \
                 "<level>{level: <8}</level> | " \
                 "<cyan>{module}.{function}:{line}</cyan> | " \
                 "<level>{message}</level>"  # 日志内容

    def __init__(self, port):
        self.log = logger

        self.log.remove()
        self.log.add(sys.stdout, level=self.log_level.upper(), format=self.log_format)

        if self.log_path:
            self.log.add(self.log_path, level=self.log_level.upper(), rotation="12:00", retention="15 days",
                         format=self.log_format)

        address_info = socket.getaddrinfo("127.0.0.1", port, socket.AF_INET, socket.SOCK_STREAM)[0]
        family, socket_type, proto, _, socket_address = address_info
        self.__sock = socket.socket(family, socket_type, proto)
        self.__sock.connect(socket_address)

    @classmethod
    def build(cls, port: int) -> "WinBotMain":
        subprocess.Popen(["WindowsDriver.exe", str(port)])
        return WinBotMain(port)

    def __send_data(self, *args) -> str:
        args_len = ""
        args_text = ""

        for argv in args:
            if argv is None:
                argv = ""
            elif isinstance(argv, bool) and argv:
                argv = "true"
            elif isinstance(argv, bool) and not argv:
                argv = "false"

            argv = str(argv)
            args_text += argv
            args_len += str(len(argv)) + "/"

        data = (args_len.strip("/") + "\n" + args_text).encode("utf8")

        self.log.debug(rf"---> {data}")
        self.__sock.sendall(data)
        data_length, data = self.__sock.recv(65535).split(b"/", 1)

        while int(data_length) > len(data):
            data += self.__sock.recv(65535)
        self.log.debug(rf"<--- {data}")

        return data.decode("utf8").strip()

    # #############
    #   窗口操作   #
    # #############
    def find_window(self, class_name: str = None, window_name: str = None) -> Optional[str]:
        """
        查找窗口句柄，仅查找顶级窗口，不包含子窗口
        :param class_name: 窗口类名
        :param window_name: 窗口名
        :return:
        """
        response = self.__send_data("findWindow", class_name, window_name)
        if response == "null":
            return None
        return response

    def find_windows(self, class_name: str = None, window_name: str = None) -> List[str]:
        """
        查找窗口句柄数组，仅查找顶级窗口，不包含子窗口
        class_name 和 window_name 都为 None，则返回所有窗口句柄
        :param class_name: 窗口类名
        :param window_name: 窗口名
        :return:
        """
        response = self.__send_data("findWindows", class_name, window_name)
        if response == "null":
            return []
        return response.split("|")

    def find_sub_window(self, hwnd: str, class_name: str = None, window_name: str = None) -> Optional[str]:
        """
        查找子窗口句柄
        :param hwnd: 当前窗口句柄
        :param class_name: 窗口类名
        :param window_name: 窗口名
        :return:
        """
        response = self.__send_data("findSubWindow", hwnd, class_name, window_name)
        if response == "null":
            return None
        return response

    def find_parent_window(self, hwnd: str) -> Optional[str]:
        """
        查找父窗口句柄
        :param hwnd: 当前窗口句柄
        :return:
        """
        response = self.__send_data("findParentWindow", hwnd)
        if response == "null":
            return None
        return response

    def get_window_name(self, hwnd: str) -> Optional[str]:
        """
        获取窗口名称
        :param hwnd: 当前窗口句柄
        :return:
        """
        response = self.__send_data("getWindowName", hwnd)
        if response == "null":
            return None
        return response

    def show_window(self, hwnd: str, show: bool) -> bool:
        """
        显示/隐藏窗口
        :param hwnd: 当前窗口句柄
        :param show: 是否显示窗口
        :return:
        """
        return self.__send_data("showWindow", hwnd, show) == "true"

    def set_window_top(self, hwnd: str) -> bool:
        """
        设置窗口到最顶层
        :param hwnd: 当前窗口句柄
        :return:
        """
        return self.__send_data("setWindowTop", hwnd) == "true"

    # #############
    #   键鼠操作   #
    # #############
    def move_mouse(self, hwnd: str, x: float, y: float, mode: bool = False) -> bool:
        """
        移动鼠标
        :param hwnd: 当前窗口句柄
        :param x: 横坐标
        :param y: 纵坐标
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作
        :return:
        """
        return self.__send_data("moveMouse", hwnd, x, y, mode) == "true"

    def scroll_mouse(self, hwnd: str, x: float, y: float, count: int, mode: bool = False) -> bool:
        """
        滚动鼠标
        :param hwnd: 当前窗口句柄
        :param x: 横坐标
        :param y: 纵坐标
        :param count: 鼠标滚动次数, 负数下滚鼠标, 正数上滚鼠标
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作
        :return:
        """
        return self.__send_data("rollMouse", hwnd, x, y, count, mode) == "true"

    def click_mouse(self, hwnd: str, x: float, y: float, typ: int, mode: bool = False) -> bool:
        """
        鼠标点击
        :param hwnd: 当前窗口句柄
        :param x: 横坐标
        :param y: 纵坐标
        :param typ: 点击类型，单击左键:1 单击右键:2 按下左键:3 弹起左键:4 按下右键:5 弹起右键:6 双击左键:7 双击右键:8
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作
        :return:
        """
        return self.__send_data("clickMouse", hwnd, x, y, typ, mode) == "true"

    def send_keys(self, text: str) -> bool:
        """
        输入文本
        :param text: 输入的文本
        :return:
        """
        return self.__send_data("sendKeys", text) == "true"

    def send_keys_by_hwnd(self, hwnd: str, text: str) -> bool:
        """
        后台输入文本(杀毒软件可能会拦截)
        :param hwnd: 窗口句柄
        :param text: 输入的文本
        :return:
        """
        return self.__send_data("sendKeysByHwnd", hwnd, text) == "true"

    def send_vk(self, vk: int, typ: int) -> bool:
        """
        输入虚拟键值(VK)
        :param vk: VK键值
        :param typ: 输入类型，按下弹起:1 按下:2 弹起:3
        :return:
        """
        return self.__send_data("sendVk", vk, typ) == "true"

    def send_vk_by_hwnd(self, hwnd: str, vk: int, typ: int) -> bool:
        """
        后台输入虚拟键值(VK)
        :param hwnd: 窗口句柄
        :param vk: VK键值
        :param typ: 输入类型，按下弹起:1 按下:2 弹起:3
        :return:
        """
        return self.__send_data("sendVkByHwnd", hwnd, vk, typ) == "true"

    # #############
    #   图色操作   #
    # #############
    def save_screenshot(self, hwnd: str, save_path: str, region: _Region = None, algorithm: _Algorithm = None,
                        mode: bool = False) -> bool:
        """
        截图
        :param hwnd: 窗口句柄；
        :param save_path: 图片存储路径；
        :param region: 截图区域，默认全屏；
        :param algorithm: 处理截图所用算法和参数，默认保存原图；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :return:

        # 区域相关参数
        region = (0, 0, 0, 0) 按元素顺序分别代表：起点x、起点y、终点x、终点y，最终得到一个矩形。
        # 算法相关参数
        algorithm = (0, 0, 0) # 按元素顺序分别代表：algorithm_type 算法类型、threshold 阈值、max_val 最大值。
        threshold 和 max_val 同为 255 时灰度处理.
        0   THRESH_BINARY      算法，当前点值大于阈值 threshold 时，取最大值 max_val，否则设置为 0；
        1   THRESH_BINARY_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则设置为最大值 max_val；
        2   THRESH_TOZERO      算法，当前点值大于阈值 threshold 时，不改变，否则设置为 0；
        3   THRESH_TOZERO_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则不改变；
        4   THRESH_TRUNC       算法，当前点值大于阈值 threshold 时，设置为阈值 threshold，否则不改变；
        5   ADAPTIVE_THRESH_MEAN_C      算法，自适应阈值；
        6   ADAPTIVE_THRESH_GAUSSIAN_C  算法，自适应阈值；
        """
        if not region:
            region = [0, 0, 0, 0]

        if not algorithm:
            algorithm_type, threshold, max_val = [0, 0, 0]
        else:
            algorithm_type, threshold, max_val = algorithm
            if algorithm_type in (5, 6):
                threshold = 127
                max_val = 255

        return self.__send_data("saveScreenshot", hwnd, save_path, *region, algorithm_type, threshold, max_val,
                                mode) == "true"

    def get_color(self, hwnd: str, x: float, y: float, mode: bool = False) -> Optional[str]:
        """
        获取指定坐标点的色值，返回色值字符串(#008577)或者 None
        :param hwnd: 窗口句柄；
        :param x: x 坐标；
        :param y: y 坐标；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :return:
        """
        response = self.__send_data("getColor", hwnd, x, y, mode)
        if response == "null":
            return None
        return response

    def find_color(self, hwnd: str, color: str, sub_colors: _SubColors = None, region: _Region = None,
                   similarity: float = 0.9, mode: bool = False, wait_time: float = None, interval_time: float = None):
        """
        获取指定色值的坐标点，返回坐标或者 None
        :param hwnd: 窗口句柄；
        :param color: 颜色字符串，必须以 # 开头，例如：#008577；
        :param sub_colors: 辅助定位的其他颜色；
        :param region: 在指定区域内找色，默认全屏；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:

        # 区域相关参数
        region = (0, 0, 0, 0) 按元素顺序分别代表：起点x、起点y、终点x、终点y，最终得到一个矩形。
        # 算法相关参数
        algorithm = (0, 0, 0) # 按元素顺序分别代表：algorithm_type 算法类型、threshold 阈值、max_val 最大值。
        threshold 和 max_val 同为 255 时灰度处理.
        0   THRESH_BINARY      算法，当前点值大于阈值 threshold 时，取最大值 max_val，否则设置为 0；
        1   THRESH_BINARY_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则设置为最大值 max_val；
        2   THRESH_TOZERO      算法，当前点值大于阈值 threshold 时，不改变，否则设置为 0；
        3   THRESH_TOZERO_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则不改变；
        4   THRESH_TRUNC       算法，当前点值大于阈值 threshold 时，设置为阈值 threshold，否则不改变；
        5   ADAPTIVE_THRESH_MEAN_C      算法，自适应阈值；
        6   ADAPTIVE_THRESH_GAUSSIAN_C  算法，自适应阈值；
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if not region:
            region = [0, 0, 0, 0]

        if sub_colors:
            sub_colors_str = ""
            for sub_color in sub_colors:
                offset_x, offset_y, color_str = sub_color
                sub_colors_str += f"{offset_x}{offset_y}{color_str}\n"
            # 去除最后一个 \n
            sub_colors_str = sub_colors_str.strip()
        else:
            sub_colors_str = "null"

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("findColor", hwnd, color, sub_colors_str, *region, similarity, mode)
            # 找色失败
            if response == "-1.0|-1.0":
                time.sleep(interval_time)
            else:
                # 找色成功
                x, y = response.split("|")
                return _Point(x=float(x), y=float(y))
        # 超时
        return None

    def find_images(self, hwnd: str, image_path, region: _Region = None, algorithm: _Algorithm = None,
                    similarity: float = 0.9, mode: bool = False, wait_time: float = None,
                    interval_time: float = None) -> List[_Point]:
        """
        寻找图片坐标，在当前屏幕中寻找给定图片的坐标，返回坐标列表
        :param hwnd: 窗口句柄；
        :param image_path: 图片的绝对路径；
        :param region: 从指定区域中找图，默认全屏；
        :param algorithm: 处理屏幕截图所用的算法，默认原图，注意：给定图片处理时所用的算法，应该和此方法的算法一致；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:

        # 区域相关参数
        region = (0, 0, 0, 0) 按元素顺序分别代表：起点x、起点y、终点x、终点y，最终得到一个矩形。
        # 算法相关参数
        algorithm = (0, 0, 0) # 按元素顺序分别代表：algorithm_type 算法类型、threshold 阈值、max_val 最大值。
        threshold 和 max_val 同为 255 时灰度处理.
        0   THRESH_BINARY      算法，当前点值大于阈值 threshold 时，取最大值 max_val，否则设置为 0；
        1   THRESH_BINARY_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则设置为最大值 max_val；
        2   THRESH_TOZERO      算法，当前点值大于阈值 threshold 时，不改变，否则设置为 0；
        3   THRESH_TOZERO_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则不改变；
        4   THRESH_TRUNC       算法，当前点值大于阈值 threshold 时，设置为阈值 threshold，否则不改变；
        5   ADAPTIVE_THRESH_MEAN_C      算法，自适应阈值；
        6   ADAPTIVE_THRESH_GAUSSIAN_C  算法，自适应阈值；
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if not region:
            region = [0, 0, 0, 0]

        if not algorithm:
            algorithm_type, threshold, max_val = [0, 0, 0]
        else:
            algorithm_type, threshold, max_val = algorithm
            if algorithm_type in (5, 6):
                threshold = 127
                max_val = 255

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("findImage", hwnd, image_path, *region, similarity, algorithm_type, threshold,
                                        max_val, mode)
            # 找图失败
            if response == "-1.0|-1.0":
                time.sleep(interval_time)
                continue
            else:
                # 找图成功，返回图片左上角坐标
                # 分割出多个图片的坐标
                image_points = response.split("/")
                point_list = []
                for point_str in image_points:
                    x, y = point_str.split("|")
                    point_list.append(_Point(x=float(x), y=float(y)))
                return point_list
        # 超时
        return []

    def find_dynamic_image(self, hwnd: str, interval_ti: int, region: _Region = None, mode: bool = False,
                           wait_time: float = None, interval_time: float = None) -> List[_Point]:
        """
        找动态图，对比同一张图在不同时刻是否发生变化，返回坐标列表
        :param hwnd: 窗口句柄；
        :param interval_ti: 前后时刻的间隔时间，单位毫秒；
        :param region: 在指定区域找图，默认全屏；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if not region:
            region = [0, 0, 0, 0]

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("findAnimation", hwnd, interval_ti, *region, mode)
            # 找图失败
            if response == "-1.0|-1.0":
                time.sleep(interval_time)
                continue
            else:
                # 找图成功，返回图片左上角坐标
                # 分割出多个图片的坐标
                image_points = response.split("/")
                point_list = []
                for point_str in image_points:
                    x, y = point_str.split("|")
                    point_list.append(_Point(x=float(x), y=float(y)))
                return point_list
        # 超时
        return []

    # ##############
    #   OCR 相关   #
    # ##############

    def get_text(self, hwnd_or_image_path: str, region: _Region = None, scale: float = 1.0,
                 mode: bool = False) -> List[str]:
        """
        通过 OCR 识别屏幕中的文字，返回文字列表
        :param hwnd_or_image_path: 识别区域，默认全屏；
        :param region: 识别区域，默认全屏；
        :param scale: 图片缩放率，默认为 1.0，1.0 以下为缩小，1.0 以上为放大；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :return:
        """

    def find_text(self, hwnd_or_image_path: str, region: _Region = None, scale: float = 1.0,
                  mode: bool = False) -> List[str]:
        """
        通过 OCR 识别屏幕中的文字，返回文字列表
        :param hwnd_or_image_path: 识别区域，默认全屏；
        :param region: 识别区域，默认全屏；
        :param scale: 图片缩放率，默认为 1.0，1.0 以下为缩小，1.0 以上为放大；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :return:
        """

    # ##############
    #   元素操作   #
    # ##############

    def get_element_name(self, hwnd: str, xpath: str, wait_time: float = None, interval_time: float = None) \
            -> Optional[str]:
        """
        获取元素名称
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("getElementName", hwnd, xpath)
            if response == "null":
                time.sleep(interval_time)
                continue
            else:
                return response
        # 超时
        return None

    def get_element_value(self, hwnd: str, xpath: str, wait_time: float = None, interval_time: float = None) \
            -> Optional[str]:
        """
        获取元素文本
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("getElementValue", hwnd, xpath)
            if response == "null":
                time.sleep(interval_time)
                continue
            else:
                return response
        # 超时
        return None

    def get_element_rect(self, hwnd: str, xpath: str, wait_time: float = None, interval_time: float = None) \
            -> Optional[Tuple[_Point, _Point]]:
        """
        获取元素矩形大小
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("getElementRect", hwnd, xpath)
            if response == "-1|-1|-1|-1":
                time.sleep(interval_time)
                continue
            else:
                x1, y1, x2, y2 = response.split("|")
                return _Point(x=float(x1), y=float(y1)), _Point(x=float(x2), y=float(y2))
        # 超时
        return None

    def get_element_window(self, hwnd: str, xpath: str, wait_time: float = None, interval_time: float = None) \
            -> Optional[str]:
        """
        获取元素窗口句柄
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("getElementWindow", hwnd, xpath)
            if response == "null":
                time.sleep(interval_time)
                continue
            else:
                return response
        # 超时
        return None

    def click_element(self, hwnd: str, xpath: str, typ: int, wait_time: float = None,
                      interval_time: float = None) -> bool:
        """
        获取元素窗口句柄
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param typ: 操作类型，单击左键:1 单击右键:2 按下左键:3 弹起左键:4 按下右键:5 弹起右键:6 双击左键:7 双击右键:8
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data('clickElement', hwnd, xpath, typ)
            if response == "false":
                time.sleep(interval_time)
                continue
            else:
                return True
        # 超时
        return False

    def set_element_focus(self, hwnd: str, xpath: str, wait_time: float = None, interval_time: float = None) -> bool:
        """
        设置元素作为焦点
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data('setElementFocus', hwnd, xpath)
            if response == "false":
                time.sleep(interval_time)
                continue
            else:
                return True
        # 超时
        return False

    def set_element_value(self, hwnd: str, xpath: str, value: str,
                          wait_time: float = None, interval_time: float = None) -> bool:
        """
        设置元素文本
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param value: 要设置的内容
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data('setElementValue', hwnd, xpath, value)
            if response == "false":
                time.sleep(interval_time)
                continue
            else:
                return True
        # 超时
        return False

    def scroll_element(self, hwnd: str, xpath: str, horizontal: int, vertical: int,
                       wait_time: float = None, interval_time: float = None) -> bool:
        """
        滚动元素
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param horizontal: 水平百分比 -1不滚动
        :param vertical: 垂直百分比 -1不滚动
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data('setElementScroll', hwnd, xpath, horizontal, vertical)
            if response == "false":
                time.sleep(interval_time)
                continue
            else:
                return True
        # 超时
        return False

    def close_window(self, hwnd: str, xpath: str) -> bool:
        """
        关闭窗口
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :return:
        """
        return self.__send_data('closeWindow', hwnd, xpath) == 'true'

    def set_element_state(self, hwnd: str, xpath: str, state: str) -> bool:
        """
        设置窗口状态
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param state: 0正常 1最大化 2 最小化
        :return:
        """
        return self.__send_data('setWindowState', hwnd, xpath, state) == 'true'

    # ###############
    #   系统剪切板   #
    # ###############
    def set_clipboard_text(self, text: str) -> bool:
        """
        设置剪切板内容
        :param text: 要设置的内容
        :return:
        """
        return self.__send_data("setClipboardText", text) == 'true'

    def get_clipboard_text(self) -> str:
        """
        设置剪切板内容
        :return:
        """
        return self.__send_data("getClipboardText")

    # #############
    #   启动进程   #
    # #############

    def start_process(self, cmd: str, show_window=True, is_wait=False) -> bool:
        """
        执行cmd命令
        :param cmd: 命令
        :param show_window: 是否显示窗口，默认显示
        :param is_wait: 是否等待程序结束， 默认不等待
        :return:
        """
        raise NotImplementedError()

    def download_file(self, url: str, file_path: str, is_wait: bool) -> bool:
        """

        :param url: 文件地址
        :param file_path: 文件保存的路径
        :param is_wait: 是否等待下载完成
        :return:
        """
        raise NotImplementedError()
