# ESP32-D0WD 开发板：红绿双灯不同频率闪烁
# 依据《修正ESP32_D0WD_硬件开发手册》：
#   LED2 绿灯 = GPIO32，LED3 红灯 = GPIO33
#   共阳接法，低电平点亮：value(0)=亮，value(1)=灭
# 绿灯 1 Hz（每 500ms 翻转），红灯约 3.3 Hz（每 150ms 翻转）
import time
from machine import Pin

green = Pin(32, Pin.OUT, value=1)  # 初始灭
red   = Pin(33, Pin.OUT, value=1)  # 初始灭

GREEN_HALF_PERIOD_MS = 500  # 绿灯翻转间隔 -> 1 Hz 慢闪
RED_HALF_PERIOD_MS = 150    # 红灯翻转间隔 -> 约 3.3 Hz 快闪

next_green = time.ticks_ms()
next_red = time.ticks_ms()

while True:
    now = time.ticks_ms()
    if time.ticks_diff(now, next_green) >= 0:
        green.value(not green.value())
        next_green = time.ticks_add(next_green, GREEN_HALF_PERIOD_MS)
    if time.ticks_diff(now, next_red) >= 0:
        red.value(not red.value())
        next_red = time.ticks_add(next_red, RED_HALF_PERIOD_MS)
    time.sleep_ms(5)
