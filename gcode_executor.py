# -*- coding: utf-8 -*-
"""GCode 执行器：逐行读取并分发到 GRBL / HDMI / I2C。

规则（与你的约定一致）：
- ';' 后面注释全部丢弃
- M6054 "xx.png" : 只更新当前图片名（不发给 GRBL）
- M106 S255       : 等 GRBL Idle -> 显示当前图片 -> 光机开灯
- M106 S0         : 光机关灯 -> 黑屏
- G4 Pxxxx        : 树莓派 sleep(xxxx/1000)
- 其它            : 发给 GRBL，等待 ok/error

注意：
- GRBL 的 'ok' 不等于“走完”，所以在真正曝光（M106 S255）前要 wait_until_idle()
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any

from grbl_client import GrblClient
from display_control import HdmiDisplay
from projector_control import DlpProjector


_RE_M6054 = re.compile(r"^M6054\s+\"?([^\"\s]+)\"?\s*$", re.IGNORECASE)
_RE_M106 = re.compile(r"^M106\s+S([0-9\.]+)\s*$", re.IGNORECASE)
_RE_G4P = re.compile(r"^G4\s+P([0-9\.]+)\s*$", re.IGNORECASE)


@dataclass
class RunStats:
    gcode_lines_total: int = 0
    gcode_lines_sent_grbl: int = 0
    dwell_count: int = 0
    exposure_on_count: int = 0
    exposure_off_count: int = 0
    image_select_count: int = 0


class GcodeExecutor:
    def __init__(
        self,
        grbl: GrblClient,
        display: HdmiDisplay,
        projector: DlpProjector,
        image_dir: str,
        dry_run: bool = False,
        idle_timeout_s: float = 180.0,
        idle_poll_s: float = 0.10,
        event_pump_hz: int = 30,
        post_exposure_black_delay_s: float = 0.0,
        pre_exposure_black_delay_s: float = 0.0, 
    ):
        self.grbl = grbl
        self.display = display
        self.projector = projector
        self.image_dir = image_dir
        self.dry_run = dry_run
        self.idle_timeout_s = idle_timeout_s
        self.idle_poll_s = idle_poll_s
        self.event_pump_hz = event_pump_hz
        self.post_exposure_black_delay_s = float(post_exposure_black_delay_s)
        self._exposure_active = False
        self.pre_exposure_black_delay_s = float(pre_exposure_black_delay_s)



        self.current_image: Optional[str] = None
        self.stats = RunStats()

    @staticmethod
    def _strip_comment(line: str) -> str:
        if ";" in line:
            line = line.split(";", 1)[0]
        return line.strip()

    def _handle_m6054(self, line: str) -> bool:
        m = _RE_M6054.match(line)
        if not m:
            return False
        name = m.group(1)
        # 允许 gcode 里只写 12 或 12.png，两种都兼容
        if not name.lower().endswith(".png") and not name.lower().endswith(".bmp") and not name.lower().endswith(".jpg") and not name.lower().endswith(".jpeg"):
            name = name + ".png"
        self.current_image = os.path.join(self.image_dir, name)
        self.stats.image_select_count += 1
        print(f"[M6054] 选择图片: {self.current_image}")
        return True

    def _handle_m106(self, line: str) -> bool:
        m = _RE_M106.match(line)
        if not m:
            return False
        s_val = float(m.group(1))
        if s_val >= 1.0:  # 约定：S255 表示“开灯+显示”
            # S>=1：开始曝光（显示图片 + 开灯）
            self.stats.exposure_on_count += 1

            if self.current_image is None:
                raise RuntimeError("收到 M106 S255 但还没有 M6054 选择图片")

            print(f"[M106] 开始曝光：{self.current_image}")
            if not self.dry_run:
                # 1) 确保电机已停（你原来就有）
                self.grbl.wait_until_idle(timeout_s=self.idle_timeout_s, poll_s=self.idle_poll_s)

                # 2) 曝光前：强制黑屏+关灯，再等待 1~2 秒
                self.projector.off()
                self.display.black()
                if self.pre_exposure_black_delay_s > 0:
                    print(f"[M106] 曝光前黑屏等待 {self.pre_exposure_black_delay_s:.2f} s")
                    self.display.sleep_with_pump(self.pre_exposure_black_delay_s)

                # 3) 开始本层曝光：显示图片 + 开灯
                self.display.show(self.current_image)
                self.projector.on()
            else:
                print("[DRY_RUN] would wait_until_idle()")
                print("[DRY_RUN] would projector.off() and display.black()")
                if self.pre_exposure_black_delay_s > 0:
                    print(f"[DRY_RUN] would sleep {self.pre_exposure_black_delay_s:.2f}s")
                print("[DRY_RUN] would display.show(current_image) and projector.on()")

            return True

            """
            self.stats.exposure_on_count += 1
            if self.current_image is None:
                raise RuntimeError("遇到 M106 S255 但还没有 M6054 选择图片")

            print("[M106] 准备曝光：等待 GRBL Idle...")
            if not self.dry_run:
                self.grbl.wait_until_idle(timeout_s=self.idle_timeout_s, poll_s=self.idle_poll_s)
                self.display.show(self.current_image)
                self.projector.on()
                self._exposure_active = True
            else:
                print(f"[DRY_RUN] would show {self.current_image} and projector.on()")
            return True
            """

        # S0：黑屏 + 关灯
        # S0：黑屏 + 关灯
        self.stats.exposure_off_count += 1

        was_active = self._exposure_active  # 记录：这次 S0 是否是“曝光结束”
        self._exposure_active = False       # 无论如何，先标记为不在曝光中

        print("[M106] 结束曝光：黑屏+关灯")
        if not self.dry_run:
            self.projector.off()
            self.display.black()

            # 只有在“刚刚确实曝光过”的情况下，才额外黑屏等待
            if was_active and self.post_exposure_black_delay_s > 0:
                print(f"[M106] 黑屏额外等待 {self.post_exposure_black_delay_s:.2f} s")
                self.display.sleep_with_pump(self.post_exposure_black_delay_s)
        else:
            print("[DRY_RUN] would projector.off() and display.black()")
            if was_active and self.post_exposure_black_delay_s > 0:
                print(f"[DRY_RUN] would sleep {self.post_exposure_black_delay_s:.2f}s")

        return True

    def _handle_g4(self, line: str) -> bool:
        m = _RE_G4P.match(line)
        if not m:
            return False
        ms = float(m.group(1))
        sec = ms / 1000.0
        self.stats.dwell_count += 1
        print(f"[G4] dwell {ms:.0f} ms")
        if not self.dry_run:
            self.display.sleep_with_pump(sec)
        else:
            print(f"[DRY_RUN] would sleep {sec:.3f}s")
        return True

    def _send_to_grbl(self, line: str) -> None:
        if self.dry_run:
            print(f"[DRY_RUN][GRBL] {line}")
            return
        self.grbl.send_line_wait_ok(line)
        self.stats.gcode_lines_sent_grbl += 1

    def run_file(self, gcode_path: str) -> RunStats:
        self.stats = RunStats()
        print(f"=== RUN GCODE: {gcode_path} ===")
        with open(gcode_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                self.stats.gcode_lines_total += 1
                line = self._strip_comment(raw)
                if not line:
                    continue

                # 先处理树莓派侧的“工艺指令”
                if self._handle_m6054(line):
                    continue
                if self._handle_m106(line):
                    continue
                if self._handle_g4(line):
                    continue

                # 剩下的交给 GRBL（运动/坐标等）
                self._send_to_grbl(line)

        return self.stats
