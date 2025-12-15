# -*- coding: utf-8 -*-
"""GRBL 串口客户端：逐行发送 + 等待 ok/error + 轮询状态。

要点：
1) 发送一行命令 -> 等待返回 ok/error
2) 需要“确认运动结束”时：发送 '?' 读取状态，直到 <Idle|...>
"""

from __future__ import annotations

import time
import serial
from dataclasses import dataclass
from typing import Optional


@dataclass
class GrblStatus:
    raw: str
    state: Optional[str]  # Idle/Run/Hold/Alarm/...（解析不出来就 None）


class GrblClient:
    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout_s: float = 1.0,
        reset_on_open: bool = True,
    ):
        self.ser = serial.Serial(port, baudrate=baudrate, timeout=timeout_s)
        # Arduino 打开串口通常会复位，给它一点时间吐出欢迎信息
        if reset_on_open:
            time.sleep(2.0)
        self.drain()

    def close(self) -> None:
        try:
            self.ser.close()
        except Exception:
            pass

    def drain(self) -> None:
        """清空串口输入缓存。"""
        try:
            while self.ser.in_waiting:
                self.ser.read(self.ser.in_waiting)
        except Exception:
            pass

    def _readline(self, timeout_s: float = 5.0) -> str:
        """读一行（去 \r\n），超时抛异常。"""
        t0 = time.time()
        buf = b""
        while True:
            if time.time() - t0 > timeout_s:
                raise TimeoutError("GRBL 读取超时（没有收到完整行）")
            ch = self.ser.read(1)
            if not ch:
                continue
            if ch in (b"\n", b"\r"):
                if buf:
                    break
                continue
            buf += ch
        return buf.decode("utf-8", errors="ignore").strip()

    def write_line(self, line: str) -> None:
        """写入一行（自动加 \n）。"""
        payload = (line.strip() + "\n").encode("utf-8")
        self.ser.write(payload)

    def send_line_wait_ok(self, line: str) -> str:
        """发送一行给 GRBL，并等待 ok/error 返回。返回最后一行响应。"""
        clean = line.strip()
        if not clean:
            return ""

        self.write_line(clean)

        # 有的命令会返回多行（比如 $$），这里简单读取直到 ok 或 error
        last = ""
        while True:
            resp = self._readline(timeout_s=10.0)
            last = resp
            low = resp.lower()
            if low == "ok":
                return resp
            if low.startswith("error") or low.startswith("alarm"):
                raise RuntimeError(f"GRBL 返回错误：{resp} （命令：{clean}）")
            # 其它行：继续读（例如 welcome banner/feedback）

    def soft_reset(self) -> None:
        """软复位 Ctrl-X。"""
        self.ser.write(b"\x18")
        time.sleep(0.5)
        self.drain()

    def unlock(self) -> None:
        """$X 解锁。"""
        self.send_line_wait_ok("$X")

    def home(self) -> None:
        """$H 回零（需要 homing enabled）。"""
        self.send_line_wait_ok("$H")

    def get_status(self) -> GrblStatus:
        """发送 '?' 获取状态，返回解析结果。"""
        self.write_line("?")
        line = self._readline(timeout_s=2.0)
        # 典型格式：<Idle|MPos:0.000,0.000,0.000|FS:0,0>
        state = None
        if line.startswith("<") and "|" in line:
            try:
                state = line[1:].split("|", 1)[0]
            except Exception:
                state = None
        return GrblStatus(raw=line, state=state)

    def wait_until_idle(self, timeout_s: float = 120.0, poll_s: float = 0.10) -> None:
        """阻塞直到状态为 Idle。"""
        t0 = time.time()
        while True:
            st = self.get_status()
            if st.state == "Idle":
                return
            if st.state == "Alarm":
                raise RuntimeError(f"GRBL 处于 ALARM：{st.raw}")
            if time.time() - t0 > timeout_s:
                raise TimeoutError(f"等待 GRBL Idle 超时。最后状态：{st.raw}")
            time.sleep(poll_s)
