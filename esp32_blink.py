"""
ESP32-D0WD 开发板 — 双 LED 异步闪烁程序
============================================
硬件：
  LED2 (绿色) — GPIO32 — 低电平点亮 (VCC→LED→R10→GPIO32)
  LED3 (红色) — GPIO33 — 低电平点亮 (VCC→LED→R11→GPIO33)

闪烁频率：
  绿色 LED: 150ms ON / 150ms OFF  (~3.3 Hz, 快速闪烁)
  红色 LED: 500ms ON / 500ms OFF  (~1 Hz,   慢速闪烁)

用法：
  将此文件保存为 main.py 推送到 ESP32 以开机自启动，
  或直接通过 mpremote run 运行。
"""

from machine import Pin
import time

# --- 初始化 LED ---
# 手册 §4.2：LED2/3 为共阳接法，GPIO 输出低电平时 LED 点亮
# Pin(value=0) → LED 亮, Pin(value=1) → LED 灭
led_green = Pin(32, Pin.OUT, value=1)  # 初始状态：灭
led_red   = Pin(33, Pin.OUT, value=1)  # 初始状态：灭

# --- 闪烁参数 ---
# 使用非阻塞方式实现两个 LED 各自由独立的周期闪烁
GREEN_INTERVAL = 150  # 绿色 LED 半周期 (ms)
RED_INTERVAL   = 500  # 红色 LED 半周期 (ms)

# --- 主循环（非阻塞毫秒级调度）---
def main():
    """使用 ticks 实现的非阻塞双 LED 独立闪烁"""
    green_last = time.ticks_ms()
    red_last   = time.ticks_ms()

    # 初始状态：两灯都亮一下表示启动
    led_green.value(0)  # 绿灯亮
    led_red.value(0)    # 红灯亮
    time.sleep_ms(300)
    led_green.value(1)  # 绿灯灭
    led_red.value(1)    # 红灯灭

    print("ESP32-D0WD 双 LED 闪烁程序启动")
    print(f"  绿色 LED (GPIO32): {1000 // (GREEN_INTERVAL * 2)} Hz")
    print(f"  红色 LED (GPIO33): {1000 // (RED_INTERVAL * 2)} Hz")
    print("  按 Ctrl+C 停止")

    while True:
        now = time.ticks_ms()

        # 绿色 LED 独立计时
        if time.ticks_diff(now, green_last) >= GREEN_INTERVAL:
            # 翻转绿灯状态（0↔1，即亮↔灭）
            led_green.value(1 - led_green.value())
            green_last = now

        # 红色 LED 独立计时
        if time.ticks_diff(now, red_last) >= RED_INTERVAL:
            # 翻转红灯状态
            led_red.value(1 - led_red.value())
            red_last = now

        # 极短休眠，避免 CPU 满载
        time.sleep_ms(1)


# --- 若通过 mpremote run 执行，直接运行 ---
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Ctrl+C 后清理 GPIO，两灯均灭
        led_green.value(1)
        led_red.value(1)
        print("\n程序已停止，LED 已熄灭")
