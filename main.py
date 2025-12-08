import os
import sys
import time

import exposure  # 你之前写好的模块：init_display / start_exposure / stop_exposure / close_display


# ============ 配置区域（默认参数） ============

IMAGE_FOLDER = "/home/ikastra/Desktop/FurDLP/shuangqu"  # 默认图像目录
EXPOSURE_TIME = 0.5              # 默认每层曝光时间（秒）
DARK_TIME = 0.5                   # 默认黑屏时间（秒），0 表示不用黑屏间隔
DISPLAY_INDEX = 1                 # 默认使用的显示器编号（0 或 1）


# ============ 工具函数：读取并排序图片路径 ============

def get_layer_paths(folder):
    """
    从给定文件夹中找到所有 .png 图片，
    按“数字大小”排序，返回完整路径列表。
    假设文件名形如:1.png, 2.png, 10.png, 101.png ...
    """
    try:
        files = os.listdir(folder)
    except FileNotFoundError:
        print(f"错误：找不到目录 {folder}")
        sys.exit(1)

    # 只要 .png
    image_files = [f for f in files if f.lower().endswith(".png")]
    if not image_files:
        print(f"错误：目录 {folder} 中没有找到任何 .png 图片")
        sys.exit(1)

    # 按数字排序，例如 1,2,10,11...
    def numeric_key(name):
        base, _ = os.path.splitext(name)  # "12.png" -> "12"
        return int(base)                  # "12" -> 12

    image_files.sort(key=numeric_key)

    # 拼完整路径
    layer_paths = [os.path.join(folder, f) for f in image_files]

    print("将按以下顺序播放图片：")
    for p in layer_paths:
        print("  ", p)

    return layer_paths


# ============ 核心函数：只控制 HDMI 曝光 ============

def run_sequence(folder, exposure_time, dark_time, display_index):
    """
    在指定显示器上，按照文件夹中的图片顺序，逐张曝光。
    不包含电机控制，只负责 HDMI 输出。
    """
    # 初始化显示
    exposure.init_display(display_index=display_index)

    # 准备所有层的路径
    layer_paths = get_layer_paths(folder)

    # 逐层曝光
    for idx, path in enumerate(layer_paths, start=1):
        print(f"==== 处理第 {idx}/{len(layer_paths)} 层 ====")

        # 1) 开始曝光：显示这一层图像
        exposure.start_exposure(path)

        # 2) 曝光持续 exposure_time 秒
        time.sleep(exposure_time)

        # 3) 停止曝光：黑屏
        exposure.stop_exposure()

        # 4) 黑屏保持一小段时间（可选）
        if dark_time > 0:
            time.sleep(dark_time)

    # 结束后关闭显示
    exposure.close_display()
    print("所有层曝光完成。")


# ============ 程序入口 ============

if __name__ == "__main__":
    # 先用默认配置
    folder = IMAGE_FOLDER
    exposure_time = EXPOSURE_TIME
    dark_time = DARK_TIME
    display = DISPLAY_INDEX

    # 也可以支持命令行参数进行覆盖（可选）
    # 用法示例：
    #   python3 projector_hdmi.py /home/pi/layers 4.5 0 0.2
    #
    # 含义：
    #   参数1: 图像目录
    #   参数2: 每层曝光时间（秒）
    #   参数3: 显示器编号（0 或 1）
    #   参数4: 每层之间的黑屏时间（秒）
    if len(sys.argv) >= 2:
        folder = sys.argv[1]
    if len(sys.argv) >= 3:
        exposure_time = float(sys.argv[2])
    if len(sys.argv) >= 4:
        display = int(sys.argv[3])
    if len(sys.argv) >= 5:
        dark_time = float(sys.argv[4])

    print(f"使用目录：{folder}")
    print(f"曝光时间：{exposure_time} 秒")
    print(f"显示器编号：{display}")
    print(f"黑屏时间：{dark_time} 秒")

    run_sequence(folder, exposure_time, dark_time, display)
