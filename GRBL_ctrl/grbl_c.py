# grbl_controller.py
import serial
import time


class GrblController:
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200, timeout=1.0):
        """
        连接到 Arduino 上的 GRBL。
        port      : 串口设备名，例如 /dev/ttyACM0 或 /dev/ttyUSB0
        baudrate  : 波特率，GRBL 默认 115200
        timeout   : 读串口的超时时间（秒）
        """
        self.ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)

        # Arduino 上电后会 reset，等它醒一会儿
        time.sleep(2)

        # 读一下 GRBL 启动信息（一般会打印出版本）
        self._flush_startup()

        # 可以根据需要选择是否解锁（如果上电后 GRBL 是 ALARM 状态）
        # self.send_line("$X")

    def _flush_startup(self):
        """读掉启动时串口里残留的几行信息。"""
        while True:
            line = self.ser.readline().decode("ascii", errors="ignore").strip()
            if not line:
                break
            print(f"[GRBL启动] {line}")

    def send_line(self, line: str) -> str:
        """
        发送一行 G 代码到 GRBL，并等待返回 "ok" 或 "error:...".
        line: 不需要自己加换行，这里会自动在末尾加 '\n'
        返回: GRBL 的最后一行回复（例如 'ok' 或 'error:xx'）
        """
        # 确保末尾有换行
        if not line.endswith("\n"):
            line += "\n"

        # 写串口
        self.ser.write(line.encode("ascii"))
        self.ser.flush()

        # 等待 GRBL 回复
        while True:
            resp = self.ser.readline().decode("ascii", errors="ignore").strip()
            if not resp:
                continue  # 读到空行就继续等
            print(f"[GRBL] {resp}")

            # 通常 GRBL 每条指令最后会给一个 ok 或 error
            if resp.startswith("ok") or resp.startswith("error"):
                return resp

    def send_gcode_block(self, lines):
        """
        一次发送多行 G 代码（列表或任意可迭代对象），每行等 'ok' 再发下一行。
        """
        for line in lines:
            self.send_line(line)

    def close(self):
        """关闭串口连接。"""
        self.ser.close()
