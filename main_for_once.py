import os
import sys
import time

import exposure  # 你之前写好的模块：init_display / start_exposure / stop_exposure / close_display


# ============ 配置区域（默认参数） ============

IMAGE_FOLDER     = "/home/ikastra/Desktop/FurDLP/shuangqu"
BOTTOM_LAYERS    = 5      # 前 N 层（默认 5 层作为底层）
BOTTOM_EXPOSURE  = 2.0    # 底层每层曝光时间 M（秒）
NORMAL_EXPOSURE  = 0.5    # 其余层每层曝光时间 P（秒）
DARK_TIME        = 0.5    # 每层结束后黑屏时间（秒）
DISPLAY_INDEX    = 1      # 使用的显示器编号（0/1）

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

# ============ 控制一层曝光时间，停止时间 ============
def expose_one_layer(path, exposure_time, dark_time):
    """
    控制一次“单层”的曝光流程：
    1) 让光机显示这一层图片
    2) 曝光 exposure_time 秒
    3) 停止曝光（黑屏）
    4) 黑屏保持 dark_time 秒（可选）

    以后你在真正的主函数里，只要调用这个函数，就完成一层的曝光控制。
    """
    # 1) 开始曝光：显示这一层图像
    exposure.start_exposure(path)

    # 2) 曝光持续 exposure_time 秒
    time.sleep(exposure_time)

    # 3) 停止曝光：黑屏
    exposure.stop_exposure()

    # 4) 黑屏保持一小段时间（可选）
    if dark_time > 0:
        time.sleep(dark_time)

# ============ 核心函数：只控制 HDMI 曝光 ============

def run_sequence(folder,
                 bottom_layers,      # 前 N 层
                 bottom_exposure,    # N 层的曝光时间 M
                 normal_exposure,    # 之后层的曝光时间 P
                 dark_time,          # 黑屏时间
                 display_index):
    """
    在指定显示器上，按照文件夹中的图片顺序，逐张曝光。
    不包含电机控制，只负责 HDMI 输出。

    bottom_layers      : 前多少层算“底层”（用 bottom_exposure)
    bottom_exposure    : 底层每层曝光时间
    normal_exposure    : 其余层每层曝光时间
    dark_time          : 每层结束后的黑屏时间
    """
    # 初始化显示
    exposure.init_display(display_index=display_index)

    # 准备所有层的路径
    layer_paths = get_layer_paths(folder)
    total_layers = len(layer_paths)

    # 防止 N 比总层数还大
    if bottom_layers > total_layers:
        bottom_layers = total_layers

    # 逐层曝光
    for idx, path in enumerate(layer_paths, start=1):
        print(f"==== 处理第 {idx}/{total_layers} 层 ====")

        # 前 N 层用 bottom_exposure，之后用 normal_exposure
        if idx <= bottom_layers:
            current_exposure = bottom_exposure
        else:
            current_exposure = normal_exposure

        expose_one_layer(path, current_exposure, dark_time)

    # 结束后关闭显示
    exposure.close_display()
    print("所有层曝光完成。")



# ============ 程序入口 ============

if __name__ == "__main__":
    folder          = IMAGE_FOLDER
    bottom_layers   = BOTTOM_LAYERS
    bottom_exposure = BOTTOM_EXPOSURE
    normal_exposure = NORMAL_EXPOSURE
    dark_time       = DARK_TIME
    display         = DISPLAY_INDEX

    # 命令行参数覆盖（可选）：
    # 用法示例：
    #   python3 main.py  /home/pi/layers  8  2.5  0.8  0.5  1
    #
    # 对应：
    #   参数1: 图像目录
    #   参数2: 底层层数 N（前 N 层）
    #   参数3: 底层曝光时间 M（秒）
    #   参数4: 普通层曝光时间 P（秒）
    #   参数5: 黑屏时间（秒）
    #   参数6: 显示器编号
    if len(sys.argv) >= 2:
        folder = sys.argv[1]
    if len(sys.argv) >= 3:
        bottom_layers = int(sys.argv[2])
    if len(sys.argv) >= 4:
        bottom_exposure = float(sys.argv[3])
    if len(sys.argv) >= 5:
        normal_exposure = float(sys.argv[4])
    if len(sys.argv) >= 6:
        dark_time = float(sys.argv[5])
    if len(sys.argv) >= 7:
        display = int(sys.argv[6])

    print(f"使用目录：{folder}")
    print(f"底层层数：{bottom_layers}")
    print(f"底层曝光：{bottom_exposure} 秒")
    print(f"普通层曝光：{normal_exposure} 秒")
    print(f"黑屏时间：{dark_time} 秒")
    print(f"显示器编号：{display}")

    run_sequence(folder,
                 bottom_layers,
                 bottom_exposure,
                 normal_exposure,
                 dark_time,
                 display)
