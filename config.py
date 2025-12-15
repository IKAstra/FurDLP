# -*- coding: utf-8 -*-
"""树莓派打印参数配置（你主要改这个文件）。

这套 runner 约定：
- gcode 逐行读取，先去掉 ';' 之后的注释
- M6054: 只用于“选择当前层图片”（不发给 GRBL）
- M106 S255: 显示当前图片 + 打开光机蓝灯（不发给 GRBL）
- M106 S0: 黑屏 + 关闭光机 LED（不发给 GRBL）
- G4 Pxxxx: 树莓派 sleep（不发给 GRBL）
- 其它 G/\$/etc: 发给 GRBL，逐行等待 ok/error
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    # ========= 路径 =========
    # 图片文件夹：里面放 1.png / 2.png / ... 或你 slicer 输出的名字
    IMAGE_DIR: str = "/home/ikastra/Desktop/FurDLP_gpt_zh/shuangqu"
    # slicer 生成的 gcode 路径
    GCODE_FILE: str = "/home/ikastra/Desktop/FurDLP_gpt_zh/shuangqu/run.gcode"

    # ========= 串口/GRBL =========
    SERIAL_PORT: str = "/dev/ttyUSB0"   # 常见：/dev/ttyACM0 或 /dev/ttyUSB0
    BAUDRATE: int = 115200
    SERIAL_TIMEOUT_S: float = 1.0
    SERIAL_RESET_ON_OPEN: bool = True     # 打开串口时 Arduino 是否会自动复位（大多会）

    # 在开始打印前是否发送 $X 解锁
    UNLOCK_BEFORE_PRINT: bool = True
    # 是否发送 $H 回零（需要你在 GRBL 开启 homing）
    HOME_BEFORE_PRINT: bool = False

    # “曝光前等待到位”的超时时间
    GRBL_IDLE_TIMEOUT_S: float = 180.0
    # 轮询状态间隔
    GRBL_STATUS_POLL_S: float = 0.10

    # ========= HDMI 显示 =========
    # exposure.init_display(display_index=?) 的参数
    # 0/1 取决于你 HDMI 投影屏是系统里的第几个 display
    DISPLAY_INDEX: int = 1

    # ========= 光机 I2C =========
    # 如果你只想先调运动/显示，不想碰 I2C，设为 False
    PROJECTOR_ENABLED: bool = True
    # 可选：启动时把蓝灯亮度设为某个百分比 (0-100)，None 表示不设置（用 I2C_DLP_HDMI.py 默认）
    BLUE_BRIGHTNESS_PERCENT: Optional[float] = None

    # ========= 安全/调试 =========
    # True：只打印日志，不动电机、不点灯（强烈建议第一次先 True 跑一遍）
    DRY_RUN: bool = False

    # 在长时间 G4 dwell 时，pygame 事件泵频率（避免窗口假死）
    EVENT_PUMP_HZ: int = 30
    # 曝光后等待时间
    POST_EXPOSURE_BLACK_DELAY_S: float = 1
    # 每层开始曝光（M106 S255）前，黑屏额外等待的时间（秒）
    PRE_EXPOSURE_BLACK_DELAY_S: float = 3
