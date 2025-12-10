# test_grbl.py
from grbl_c import GrblController

def main():
    # 这里的端口换成你实际查到的，比如 "/dev/ttyUSB0"
    grbl = GrblController(port="/dev/ttyUSB0", baudrate=115200)

    # 典型初始化：用 mm 单位，绝对坐标
    grbl.send_line("G21")  # mm
    grbl.send_line("G90")  # 绝对坐标

    # 如果有 ALARM，可以先解锁（注意安全）
    # grbl.send_line("$X")

    # 举例：Z 轴抬起 10mm（具体轴向你按自己机器定义）
    grbl.send_line("G0 Z10 F300")  # 快移到 Z=10，进给 300 mm/min
    grbl.send_line("G0 Z0 F300")   # 再回到 0

    grbl.close()

if __name__ == "__main__":
    main()
