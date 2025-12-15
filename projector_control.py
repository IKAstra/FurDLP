# -*- coding: utf-8 -*-
"""DLP 光机 I2C 控制封装：复用你项目里的 I2C_DLP_HDMI.py。

你项目里主要用到这些函数：
- dlp_setup_external_video_1920x1080_RGB888()
- dlp_setup_blue_only()
- dlp_set_blue_brightness_percent(pct)
- dlp_enable_blue_only()
- dlp_all_leds_off()
- dlp_disable_curtain()   # 可选（如果你要幕布打开）
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Optional

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    import I2C_DLP_HDMI as dlp  # noqa: E402
except Exception as e:  # pragma: no cover
    dlp = None
    _IMPORT_ERR = e
else:
    _IMPORT_ERR = None


@dataclass
class ProjectorConfig:
    enabled: bool = True
    blue_brightness_percent: Optional[float] = None


class DlpProjector:
    def __init__(self, cfg: ProjectorConfig):
        self.cfg = cfg
        self._ready = False

    def init(self) -> None:
        """初始化光机：设置外部视频输入 + 蓝光模式 +（可选）设置亮度。"""
        if not self.cfg.enabled:
            return
        if dlp is None:
            raise RuntimeError(f"无法 import I2C_DLP_HDMI.py：{_IMPORT_ERR}")

        if self._ready:
            return

        # 根据你现有文件的设计：先设置外部视频模式，再设蓝光 only
        dlp.dlp_setup_external_video_1920x1080_RGB888()
        dlp.dlp_setup_blue_only()

        if self.cfg.blue_brightness_percent is not None:
            dlp.dlp_set_blue_brightness_percent(float(self.cfg.blue_brightness_percent))

        # 默认先关灯，避免误曝光
        dlp.dlp_all_leds_off()
        self._ready = True

    def on(self) -> None:
        if not self.cfg.enabled:
            return
        self.init()
        dlp.dlp_enable_blue_only()

    def off(self) -> None:
        if not self.cfg.enabled:
            return
        self.init()
        dlp.dlp_all_leds_off()
