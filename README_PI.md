# FurDLP Raspberry Pi Runner（逐行 gcode 执行）

## 你需要的文件
你的项目根目录有：
- `exposure.py`
- `I2C_DLP_HDMI.py`
- 你的图片目录（例如 `shuangqu/`）
- 你的 `run.gcode`

把本文件夹 `FurDLP_pi_runner/` 放在同一层。

## 安装依赖
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-smbus i2c-tools
pip3 install -r requirements.txt
sudo raspi-config  # Interface Options -> I2C -> Enable
sudo reboot
```

## 配置
编辑 `config.py`：
- `IMAGE_DIR`：图片目录
- `GCODE_FILE`：gcode 文件路径
- `SERIAL_PORT`：Arduino 串口
- `DISPLAY_INDEX`：投影屏编号
- `PROJECTOR_ENABLED`：是否启用 I2C

## 运行
```bash
python3 run_print.py
```

## gcode 约定
- `;` 后为注释
- `M6054 "12.png"`：选择图片
- `M106 S255`：显示图片 + 开灯
- `G4 P50000`：等待 50 秒（曝光时长）
- `M106 S0`：黑屏 + 关灯
