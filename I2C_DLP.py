#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DLP4710 + DLPC3439：树莓派 I2C 控制（内部测试图 TPG + 仅蓝光）
- 关键思路：I2C 只负责配置“输入源=测试图/外部视频”和“LED 控制”，不传视频数据
- I2C 写事务格式：Address(36h) + Sub-Address(命令码) + 参数(0..N字节)  :contentReference[oaicite:2]{index=2}
"""

import time
from smbus import SMBus

# ========= 你的硬件参数（可改） =========
I2C_BUS = 1
I2C_ADDR = 0x1B  # 常见：文档默认 36h(8-bit写) => 7-bit = 0x36>>1 = 0x1B  :contentReference[oaicite:3]{index=3}

# 蓝灯默认“电流码值”（10-bit，0~1023）。注意：这是“码值”，不是直接 mA。
DEFAULT_BLUE_CODE = 300


# ========= 底层 I2C 发送模块 =========
def write_cmd(bus: SMBus, cmd: int, data=()):
    """
    发送一条 DLPC3439 I2C 写命令：
      - cmd：命令码（也叫 Sub-Address / OpCode）
      - data：参数字节数组（0..N）
    对应文档 I2C 写事务：Address + Sub-Address + Remaining Data Bytes  :contentReference[oaicite:4]{index=4}
    """
    bus.write_i2c_block_data(I2C_ADDR, cmd, list(data))
    time.sleep(0.002)  # 给芯片一点处理时间（简单做法）


def pack_10bit_le(code: int):
    """
    把 10-bit 码值（0..1023）拆成：LSByte + MSByte（小端）
    - 0x54（LED电流）里每个颜色用 2 字节，但有效只有 10 bit  :contentReference[oaicite:5]{index=5}
    - 高位未用必须写 0（只保留 MSByte 的低 2 bit） :contentReference[oaicite:6]{index=6}
    """
    code = int(code)
    if code < 0:
        code = 0
    if code > 1023:
        code = 1023
    lsb = code & 0xFF
    msb = (code >> 8) & 0x03
    return lsb, msb


# ========= 功能模块：输入源 / 测试图 =========
def set_input_source(bus: SMBus, mode: int):
    """
    0x05 Write Input Source Select：选择输入源/工作模式  :contentReference[oaicite:7]{index=7}
    Byte1 Operating Mode:
      00h = External Video Mode
      01h = Test Pattern Generator Mode
      02h = Splash Screen Mode
    """
    write_cmd(bus, 0x05, [mode])


def set_test_pattern(bus: SMBus, pattern: int, fg_color: int, bg_color: int = 0, border: bool = False,
                     p1: int = 0, p2: int = 0, p3: int = 0, p4: int = 0):
    """
    0x0B Write Test Pattern Select：选择内部测试图（TPG） :contentReference[oaicite:8]{index=8}
    参数结构：
      Byte1：b7=border，b3:0=pattern  :contentReference[oaicite:9]{index=9}
      Byte2：b6:4=前景色，b2:0=背景色  :contentReference[oaicite:10]{index=10}
      Byte3~6：可选参数（不同图案需要） :contentReference[oaicite:11]{index=11}

    常用 pattern（Byte1低4位）示例：
      00h Solid field（纯色）
      06h Grid（网格）
      07h Checkerboard（棋盘格）
      08h Color bars（色条）
    """
    b1 = (0x80 if border else 0x00) | (pattern & 0x0F)
    b2 = ((fg_color & 0x07) << 4) | (bg_color & 0x07)

    # 这里统一发 6 字节（Byte3~6 有些图案不用也没关系，I2C 支持可变长度 0→N :contentReference[oaicite:12]{index=12}）
    write_cmd(bus, 0x0B, [b1, b2, p1 & 0xFF, p2 & 0xFF, p3 & 0xFF, p4 & 0xFF])


def image_freeze(bus: SMBus, enable: bool):
    """
    0x1A Write Image Freeze：冻结/解冻画面（用来减少切换时闪烁/伪影） :contentReference[oaicite:13]{index=13}
      Byte1 bit0:
        1 = Freeze enabled
        0 = Freeze disabled
    """
    write_cmd(bus, 0x1A, [0x01 if enable else 0x00])


def set_curtain(bus: SMBus, enable: bool, color: int = 0):
    """
    0x16 Write Display Image Curtain：整屏幕布（常用：黑幕） :contentReference[oaicite:14]{index=14}
      bits3:1 = curtain color（0=黑，3=蓝等）
      bit0 = enable（1启用，0关闭）
    注意：Curtain 只是画面层面“变黑”，不等于关 LED。
    """
    param = ((color & 0x07) << 1) | (0x01 if enable else 0x00)
    write_cmd(bus, 0x16, [param])


# ========= 功能模块：LED（只开蓝） =========
def set_led_control_manual(bus: SMBus):
    """
    0x50 Write LED Output Control Method：
      00 = Manual RGB LED currents（禁用 CAIC，手动电流） :contentReference[oaicite:15]{index=15}
    """
    write_cmd(bus, 0x50, [0x00])


def set_led_enable_blue_only(bus: SMBus, enable: bool):
    """
    0x52 Write RGB LED Enable：使能 RGB LED  :contentReference[oaicite:16]{index=16}
      bit2 = Blue enable（1开/0关）
      bit1 = Green enable
      bit0 = Red enable
    只开蓝：0x04；全关：0x00
    """
    write_cmd(bus, 0x52, [0x04 if enable else 0x00])


def set_led_current_rgb(bus: SMBus, r_code: int, g_code: int, b_code: int):
    """
    0x54 Write RGB LED Current：设置 RGB 三路 LED 电流参数 :contentReference[oaicite:17]{index=17}
      Byte1-2：Red (LSByte, MSByte)
      Byte3-4：Green (LSByte, MSByte)
      Byte5-6：Blue (LSByte, MSByte)
    并且码值是 10-bit 分辨率（0~1023） :contentReference[oaicite:18]{index=18}
    """
    r_lsb, r_msb = pack_10bit_le(r_code)
    g_lsb, g_msb = pack_10bit_le(g_code)
    b_lsb, b_msb = pack_10bit_le(b_code)
    write_cmd(bus, 0x54, [r_lsb, r_msb, g_lsb, g_msb, b_lsb, b_msb])


# ========= “开机/关光”组合动作 =========
def wait_auto_init():
    """
    文档说明：只有 auto-initialization 完成后才接收 I2C 命令，通常 <500ms  :contentReference[oaicite:19]{index=19}
    这里用最简单的 sleep（更严谨可以接 HOST_IRQ 引脚做硬件检测）。
    """
    time.sleep(0.6)


def projector_on_tpg_blue(bus: SMBus, blue_code: int, pattern: int):
    """
    用内部测试图点亮（TPG）+ 仅蓝光：
    推荐顺序：
      Freeze -> 黑幕 -> 配测试图(0x0B) -> 选输入源TPG(0x05=01)
             -> LED手动(0x50) -> 设电流(0x54) -> 使能蓝灯(0x52)
             -> 关黑幕 -> Unfreeze
    """
    image_freeze(bus, True)  # 0x1A freeze :contentReference[oaicite:20]{index=20}
    set_curtain(bus, True, color=0)  # 0x16 黑幕 :contentReference[oaicite:21]{index=21}

    # 0x0B 测试图：前景蓝（3），背景黑（0） :contentReference[oaicite:22]{index=22}
    set_test_pattern(bus, pattern=pattern, fg_color=3, bg_color=0, border=False)

    # 0x05 选择 Test Pattern Generator Mode = 01h :contentReference[oaicite:23]{index=23}
    set_input_source(bus, 0x01)

    # LED：手动模式 + 蓝电流 + 只开蓝
    set_led_control_manual(bus)                   # 0x50 = 00 :contentReference[oaicite:24]{index=24}
    set_led_current_rgb(bus, 0, 0, blue_code)     # 0x54 10bit :contentReference[oaicite:25]{index=25}
    set_led_enable_blue_only(bus, True)           # 0x52 bit2=1 :contentReference[oaicite:26]{index=26}

    set_curtain(bus, False, color=0)  # 0x16 关黑幕
    image_freeze(bus, False)          # 0x1A unfreeze


def projector_off(bus: SMBus):
    """
    “关光”（不出光）：
      - 最关键：0x52 写 0x00 关闭 LED 使能（真正熄灯） :contentReference[oaicite:27]{index=27}
      - 可选：0x16 打开黑幕防止残影/闪一下 :contentReference[oaicite:28]{index=28}
    注意：这不是“断电关机”，只是 I2C 层面把光源关掉。
    """
    image_freeze(bus, True)
    set_led_enable_blue_only(bus, False)     # 0x52 -> 0x00
    set_led_current_rgb(bus, 0, 0, 0)        # 0x54 -> 全0（可选但建议）
    set_curtain(bus, True, color=0)          # 黑幕
    image_freeze(bus, False)


# ========= 主程序：交互菜单 =========
def main():
    print("DLP4710 I2C 控制（内部测试图 + 仅蓝光）")
    print(f"I2C bus={I2C_BUS}, addr=0x{I2C_ADDR:02X}")
    print("上电后先等待 0.6s（auto-init 完成后才收命令）")

    bus = SMBus(I2C_BUS)
    blue_code = DEFAULT_BLUE_CODE

    try:
        wait_auto_init()

        while True:
            print("\n========= 菜单 =========")
            print(f"[1] 开机：纯蓝（Solid field），blue_code={blue_code}")
            print(f"[2] 开机：蓝/黑棋盘格（Checkerboard），blue_code={blue_code}")
            print(f"[3] 开机：色条（Color bars），blue_code={blue_code}（注意：色条会包含非蓝信息，但你只开蓝灯）")
            print("[4] 设置蓝灯电流码值（0~1023）")
            print("[5] 关光（LED off）")
            print("[q] 退出（会先关光）")

            cmd = input("请输入：").strip().lower()

            if cmd == "1":
                # pattern=0x00 Solid field :contentReference[oaicite:29]{index=29}
                projector_on_tpg_blue(bus, blue_code=blue_code, pattern=0x00)
                print("已开机：纯蓝测试图 + 蓝灯开启")

            elif cmd == "2":
                # pattern=0x07 Checkerboard :contentReference[oaicite:30]{index=30}
                projector_on_tpg_blue(bus, blue_code=blue_code, pattern=0x07)
                print("已开机：蓝/黑棋盘格 + 蓝灯开启")

            elif cmd == "3":
                # pattern=0x08 Color bars :contentReference[oaicite:31]{index=31}
                projector_on_tpg_blue(bus, blue_code=blue_code, pattern=0x08)
                print("已开机：色条 + 蓝灯开启（色条里非蓝部分会因只开蓝灯而呈现不同效果）")

            elif cmd == "4":
                s = input("请输入 blue_code（0~1023）：").strip()
                try:
                    v = int(s)
                    if v < 0 or v > 1023:
                        raise ValueError
                    blue_code = v
                    # 如果正在亮灯，你也可以实时刷新电流：
                    set_led_current_rgb(bus, 0, 0, blue_code)  # 0x54
                    print(f"已设置 blue_code={blue_code}")
                except ValueError:
                    print("输入无效，请输入 0~1023 的整数")

            elif cmd == "5":
                projector_off(bus)
                print("已关光：LED disable + 黑幕")

            elif cmd == "q":
                projector_off(bus)
                print("已退出（已关光）")
                break

            else:
                print("未知指令")

    finally:
        try:
            bus.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
