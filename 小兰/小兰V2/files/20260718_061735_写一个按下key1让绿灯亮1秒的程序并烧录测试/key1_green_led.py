from machine import Pin
import time

# KEY1 = GPIO35（仅输入，板载1k上拉，按下为低）
key1 = Pin(35, Pin.IN)
# 绿灯 LED2 = GPIO32，共阳接法，低电平点亮，初始化为灭
led_green = Pin(32, Pin.OUT, value=1)


def green_on_1s():
    """绿灯亮1秒后熄灭（封装成函数，便于软件触发测试）"""
    led_green.value(0)   # 低电平点亮
    time.sleep(1)
    led_green.value(1)   # 熄灭


print("ready: press KEY1 (GPIO35) to light green LED for 1s")

while True:
    if key1.value() == 0:          # 检测到按下
        time.sleep_ms(20)          # 消抖
        if key1.value() == 0:      # 确认仍按下
            print("KEY1 pressed -> green LED on 1s")
            green_on_1s()
            while key1.value() == 0:   # 等待松开，避免重复触发
                time.sleep_ms(10)
    time.sleep_ms(10)
