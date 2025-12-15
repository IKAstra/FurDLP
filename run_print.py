#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""最终主程序（尽量只包含“创建对象 + 调用函数”的流程）。

运行方式：
    python3 run_print.py

你主要修改：
    FurDLP_pi_runner/config.py
"""

from config import Settings
from grbl_client import GrblClient
from display_control import HdmiDisplay
from projector_control import DlpProjector, ProjectorConfig
from gcode_executor import GcodeExecutor


def main() -> None:
    cfg = Settings()

    # 1) 初始化 GRBL 串口
    grbl = GrblClient(
        port=cfg.SERIAL_PORT,
        baudrate=cfg.BAUDRATE,
        timeout_s=cfg.SERIAL_TIMEOUT_S,
        reset_on_open=cfg.SERIAL_RESET_ON_OPEN,
    )

    if not cfg.DRY_RUN:
        if cfg.UNLOCK_BEFORE_PRINT:
            grbl.unlock()
        if cfg.HOME_BEFORE_PRINT:
            grbl.home()
    else:
        print("[DRY_RUN] skip unlock/home")

    # 2) 初始化 HDMI 显示
    display = HdmiDisplay(display_index=cfg.DISPLAY_INDEX, event_pump_hz=cfg.EVENT_PUMP_HZ)
    display.init()
    display.black()

    # 3) 初始化光机（I2C）
    projector = DlpProjector(ProjectorConfig(
        enabled=cfg.PROJECTOR_ENABLED and (not cfg.DRY_RUN),
        blue_brightness_percent=cfg.BLUE_BRIGHTNESS_PERCENT,
    ))
    projector.init()
    projector.off()

    # 4) 执行 gcode
    executor = GcodeExecutor(
        grbl=grbl,
        display=display,
        projector=projector,
        image_dir=cfg.IMAGE_DIR,
        dry_run=cfg.DRY_RUN,
        idle_timeout_s=cfg.GRBL_IDLE_TIMEOUT_S,
        idle_poll_s=cfg.GRBL_STATUS_POLL_S,
        event_pump_hz=cfg.EVENT_PUMP_HZ,
        post_exposure_black_delay_s=cfg.POST_EXPOSURE_BLACK_DELAY_S,
        pre_exposure_black_delay_s=cfg.PRE_EXPOSURE_BLACK_DELAY_S,

    )
    stats = executor.run_file(cfg.GCODE_FILE)

    # 5) 收尾
    projector.off()
    display.black()
    display.sleep_with_pump(2.0)
    display.close()
    grbl.close()

    print("\n=== DONE ===")
    print(stats)


if __name__ == "__main__":
    main()
