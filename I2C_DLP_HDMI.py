#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
树莓派 + Python + SMBus 通过 I2C 控制 DLPC3439 (DLP4710)：

功能：
1. 初始化光机（外部视频源 + 只用蓝光 + 关幕布）
2. 运行后在命令行交互：
   - b <0-1023> : 直接设置蓝光电流参数（亮度）
   - p <0-100>  : 按百分比设置蓝光亮度
   - on         : 打开蓝 LED（只开蓝）
   - off        : 关闭所有 LED（红绿蓝全关）
   - q          : 退出程序

注意：本代码 **不等待 HOST_IRQ**，假定上电初始化已经完成。
"""

import time
import smbus  # sudo apt-get install python3-smbus

# ------------------------------
# 1. 全局配置：I2C 地址与总线编号
# ------------------------------

# DLPC3439 的 7-bit I2C 地址（Arduino 里 0x36 >> 1 = 0x1B）
DLP_I2C_ADDR = 0x1B

# 树莓派上 I2C 总线，一般是 /dev/i2c-1
I2C_BUS_NUM = 1

# 默认蓝光电流参数（10bit，示例取 0x0200，对应中等亮度）
DEFAULT_BLUE_CURRENT = 0x0200

# 创建 SMBus 对象
bus = smbus.SMBus(I2C_BUS_NUM)


# ------------------------------
# 2. 工具函数：高/低字节
# ------------------------------

def low_byte(x: int) -> int:
    """取 16bit 数的低 8 位"""
    return x & 0xFF


def high_byte(x: int) -> int:
    """取 16bit 数的高 8 位"""
    return (x >> 8) & 0xFF


# ------------------------------
# 3. 通用 I2C 写命令
# ------------------------------

def dlp_write_cmd(cmd: int, data_bytes):
    """
    向 DLPC3439 发送一条 I2C 命令。

    cmd:       命令码 / OpCode，例如 0x50, 0x52, 0x54 等
    data_bytes: 要写入的参数字节 list/tuple
    """
    if data_bytes is None:
        data_bytes = []

    data_list = [int(b) & 0xFF for b in data_bytes]
    bus.write_i2c_block_data(DLP_I2C_ADDR, cmd, data_list)

    # 对应 Arduino 里的 delay(2)
    time.sleep(0.002)


# ------------------------------
# 4. LED 相关控制函数
# ------------------------------

def dlp_set_led_control_manual():
    """
    使用命令 0x50：Write LED Output Control Method
    设置为手动 RGB LED 电流控制（关闭 CAIC 自动算法）。

    Byte0 b1:0 = 00 -> Manual RGB LED currents
    """
    led_control_method = 0x00  # 手动模式，禁用 CAIC
    dlp_write_cmd(0x50, [led_control_method])


def dlp_enable_blue_only():
    """
    使用命令 0x52：Write RGB LED Enable
    只使能蓝色 LED（bit2 = 1，其余为 0）。
    """
    led_enable = 0b00000100  # Blue=1, Green=0, Red=0
    dlp_write_cmd(0x52, [led_enable])


def dlp_all_leds_off():
    """
    使用命令 0x52：Write RGB LED Enable
    关闭所有 LED（红绿蓝全 0）。
    """
    led_enable = 0b00000000
    dlp_write_cmd(0x52, [led_enable])


def dlp_set_blue_current(raw_value: int):
    """
    使用命令 0x54：Write RGB LED Current
    只设置蓝色通道的电流参数，红绿通道为 0。

    参数:
        raw_value: 0 ~ 1023 (10bit)，对应 DLPA 的电流步进值。
                   注意这是“参数值”不是 mA，具体换算看电源芯片手册。
    """
    # 限幅，避免越界
    if raw_value < 0:
        raw_value = 0
    if raw_value > 0x03FF:
        raw_value = 0x03FF

    red = 0x0000
    green = 0x0000
    blue = int(raw_value)  # 10bit 存在 16bit 低 10 位即可

    params = [
        low_byte(red),   high_byte(red),
        low_byte(green), high_byte(green),
        low_byte(blue),  high_byte(blue),
    ]
    dlp_write_cmd(0x54, params)


def dlp_set_blue_brightness_percent(percent: float):
    """
    按百分比设置蓝光亮度（0~100%），内部换算成 10bit 电流参数再写 0x54。

    这里简单假设：
        0%  -> 参数 0
        100% -> 参数 0x03FF (1023)
    真正的电流上限仍然受电源芯片和硬件设计限制。
    """
    if percent < 0:
        percent = 0
    if percent > 100:
        percent = 100

    max_param = 0x03FF  # 10bit 最大值
    raw = int(max_param * (percent / 100.0))
    dlp_set_blue_current(raw)


# ------------------------------
# 5. 只使用蓝光的初始化流程
# ------------------------------

def dlp_setup_blue_only():
    """
    复用上面的函数，完成“只用蓝光”的基础配置：
    1) LED 输出控制方式设为手动 (0x50)
    2) 设置 RGB 电流（蓝 = DEFAULT_BLUE_CURRENT，红绿 = 0）
    3) 只使能蓝 LED (0x52)
    """

    # 1) 手动模式
    dlp_set_led_control_manual()

    # 2) 设置初始蓝光电流
    dlp_set_blue_current(DEFAULT_BLUE_CURRENT)

    # 3) 只开蓝灯
    dlp_enable_blue_only()


# ------------------------------
# 6. 外部视频源设置（与之前保持一致）
# ------------------------------

def dlp_setup_external_video_1920x1080_RGB888():
    """
    和你原来的 Arduino 代码对应：
    - 命令 0x2E: 设置输入图像大小
    - 命令 0x07: 设置外部视频格式 (0x43 = Parallel RGB888 24bit 1clk/pixel)
    - 命令 0x12: 设置显示尺寸
    - 命令 0x05: 选择 External Video Mode
    """

    width = 1920
    height = 1080

    # 1) 输入图像大小 (0x2E)
    params_size = [
        low_byte(width),  high_byte(width),
        low_byte(height), high_byte(height),
    ]
    dlp_write_cmd(0x2E, params_size)

    # 2) 外部视频格式 (0x07)
    fmt = 0x43  # Parallel, 24-bit RGB888, 1 clk/pixel
    dlp_write_cmd(0x07, [fmt])

    # 3) 显示尺寸 (0x12)
    params_disp = [
        low_byte(width),  high_byte(width),
        low_byte(height), high_byte(height),
    ]
    dlp_write_cmd(0x12, params_disp)

    # 4) 选择输入源为 External Video Mode (0x05)
    src = 0x00  # 00h = External Video Mode
    dlp_write_cmd(0x05, [src])


# ------------------------------
# 7. 关闭幕布（Curtain）
# ------------------------------

def dlp_disable_curtain():
    """
    命令 0x16：Write Display Image Curtain
    b0 = 0 表示 curtain disabled。
    """
    curtain_param = 0x00  # 颜色随便，b0=0 即关闭
    dlp_write_cmd(0x16, [curtain_param])


# ------------------------------
# 8. 主流程 + 命令行交互
# ------------------------------

def main():
    print("开始配置 DLPC3439（不等待 HOST_IRQ）...")

    # 1) 先关闭幕布，避免纯色遮挡
    dlp_disable_curtain()

    # 2) LED 配置：手动模式 + 只开蓝光 + 初始亮度
    dlp_setup_blue_only()

    # 3) 配置外部视频源
    dlp_setup_external_video_1920x1080_RGB888()

    print("初始化完成：外部视频源 = 1920x1080 RGB888，仅蓝光点亮。")
    print("现在进入交互模式：")
    print("  b <0-1023>  : 设置蓝光电流参数（原始值，10bit）")
    print("  p <0-100>   : 按百分比设置蓝光亮度")
    print("  on          : 打开蓝 LED（只开蓝）")
    print("  off         : 关闭所有 LED")
    print("  q           : 退出程序\n")

    try:
        while True:
            cmd = input("请输入命令: ").strip()

            if not cmd:
                continue

            lower = cmd.lower()

            if lower == "q":
                print("退出程序。")
                break

            elif lower == "on":
                dlp_enable_blue_only()
                print("已使能蓝 LED（红绿关闭）。")

            elif lower == "off":
                dlp_all_leds_off()
                print("已关闭所有 LED。")

            elif lower.startswith("b "):
                # 直接设置 0-1023 电流参数
                try:
                    val_str = cmd.split()[1]
                    val = int(val_str, 0)  # 支持十进制/十六进制(0x...)
                    dlp_set_blue_current(val)
                    print(f"已将蓝光电流参数设置为 {val} (0x{val:04X})。")
                    # 确保蓝光通道是开启的
                    dlp_enable_blue_only()
                except (IndexError, ValueError):
                    print("格式错误，用法示例：b 512 或 b 0x200")

            elif lower.startswith("p "):
                # 按百分比设置亮度
                try:
                    val_str = cmd.split()[1]
                    percent = float(val_str)
                    dlp_set_blue_brightness_percent(percent)
                    print(f"已将蓝光亮度设置为约 {percent:.1f}%。")
                    dlp_enable_blue_only()
                except (IndexError, ValueError):
                    print("格式错误，用法示例：p 50  （表示 50% 亮度）")

            else:
                print("未知命令，请输入 on / off / b <0-1023> / p <0-100> / q")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，程序结束。")


if __name__ == "__main__":
    main()
