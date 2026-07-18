from machine import Pin
import time

# 绿灯接 GPIO32，低电平点亮
led_green = Pin(32, Pin.OUT, value=1)  # 初始灭

def blink(times, on_ms=300, off_ms=300):
    for _ in range(times):
        led_green.value(0)   # 亮
        time.sleep_ms(on_ms)
        led_green.value(1)   # 灭
        time.sleep_ms(off_ms)

blink(2)
print("绿灯闪烁2次完成")
