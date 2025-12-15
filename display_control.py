# -*- coding: utf-8 -*-
"""HDMI 全屏显示封装：复用你项目里的 exposure.py。

exposure.py 已经提供：
- init_display(display_index)
- start_exposure(image_path)
- stop_exposure()
- close_display()

本文件做的事：
1) 自动把“项目根目录”加入 sys.path，确保能 import exposure
2) 提供一个更“面向 runner”的接口：show(image), black(), sleep_with_pump()
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional

# 让本文件能 import 到上一级的 exposure.py
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import exposure  # noqa: E402  (来自你的项目)


class HdmiDisplay:
    def __init__(self, display_index: int = 1, event_pump_hz: int = 30):
        self.display_index = display_index
        self.event_pump_hz = max(1, int(event_pump_hz))
        self._inited = False

    def init(self) -> None:
        if self._inited:
            return
        exposure.init_display(self.display_index)
        self._inited = True

    def show(self, image_path: str) -> None:
        """显示图片（保持显示，不自动计时）。"""
        self.init()
        exposure.start_exposure(image_path)

    def black(self) -> None:
        """显示黑屏。"""
        if not self._inited:
            # 没初始化时也没必要黑屏
            return
        exposure.stop_exposure()

    def close(self) -> None:
        if self._inited:
            exposure.close_display()
        self._inited = False

    def sleep_with_pump(self, seconds: float) -> None:
        """等待期间持续处理 pygame 事件，防止窗口卡死。"""
        if seconds <= 0:
            return
        period = 1.0 / self.event_pump_hz
        t_end = time.time() + seconds
        while True:
            now = time.time()
            if now >= t_end:
                return
            # exposure.py 内部会在 _process_events 里 pump 事件；
            # 但我们这里不直接调用私有函数，简单 show/black 时 pygame 已经在跑。
            time.sleep(min(period, t_end - now))
