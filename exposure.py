import os
import sys
import time

import pygame

# 这几个变量会在 init_display 里被赋值，后面的函数都会用到
screen = None
screen_width = None
screen_height = None
clock = None


def init_display(display_index=1):
    """
    初始化显示器和 pygame,全屏打开一个窗口。
    整个程序生命周期里只需要调用一次。
    :param display_index: 使用的显示器编号(0 或 1)
    """
    global screen, screen_width, screen_height, clock

    # 告诉 SDL/pygame，做全屏时用哪块屏幕
    os.environ["SDL_VIDEO_FULLSCREEN_DISPLAY"] = str(display_index)

    pygame.init()
    pygame.mouse.set_visible(False)  # 不要鼠标指针

    # 全屏窗口，分辨率就是当前这块屏的原生分辨率
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    screen_width, screen_height = screen.get_size()
    print(f"[exposure] 当前屏幕分辨率: {screen_width} x {screen_height}")

    clock = pygame.time.Clock()


def _process_events():
    """
    内部函数：处理退出事件。
    如果检测到窗口关闭或按下 ESC,就退出程序。
    """
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit(0)


def _load_image(path):
    """
    内部函数：加载一张图片，并自动按屏幕大小拉伸（如果尺寸不匹配的话）。
    返回 pygame 的 Surface 对象。
    """
    global screen_width, screen_height

    try:
        image = pygame.image.load(path)
    except pygame.error as e:
        print(f"[exposure] 加载图片失败: {path}, 错误: {e}")
        return None

    image = image.convert()  # 转成和屏幕相同的像素格式，加速显示

    img_w, img_h = image.get_size()
    if (img_w, img_h) != (screen_width, screen_height):
        print(f"[exposure] 警告: 图片尺寸 {img_w}x{img_h} != 屏幕 {screen_width}x{screen_height}，将进行拉伸。")
        image = pygame.transform.scale(image, (screen_width, screen_height))

    return image


def start_exposure(image_path):
    """
    开始曝光：在屏幕上显示指定图片，不负责计时。
    你可以在外部用 time.sleep() 控制曝光时长。
    """
    global screen

    if screen is None:
        raise RuntimeError("请先调用 init_display() 再 start_exposure()")

    _process_events()  # 先把积压的按键/退出事件处理一下

    image = _load_image(image_path)
    if image is None:
        return

    # 画图 + 刷新
    screen.blit(image, (0, 0))
    pygame.display.flip()


def stop_exposure():
    """
    停止曝光：把屏幕清成黑色。
    """
    global screen

    if screen is None:
        raise RuntimeError("请先调用 init_display() 再 stop_exposure()")

    _process_events()

    # (0, 0, 0) 是黑色
    screen.fill((0, 0, 0))
    pygame.display.flip()


def expose_image(image_path, exposure_time):
    """
    方便函数：显示一张图片 exposure_time 秒，然后自动黑屏。
    你可以选择不用这个，而是自己在外面控制 time.sleep。
    """
    start_exposure(image_path)

    start = time.time()
    while time.time() - start < exposure_time:
        # 期间仍然处理 ESC 等事件，避免窗口假死
        _process_events()
        clock.tick(60)

    stop_exposure()


def close_display():
    """
    关闭显示器，退出 pygame。在程序结束前调用一次。
    """
    pygame.quit()
    print("[exposure] 显示已关闭。")
