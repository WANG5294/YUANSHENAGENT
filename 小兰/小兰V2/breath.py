# breath.py - 呼吸灯: KEY1 绿灯(周期3s), KEY2 红灯(周期5s)
# 亮度 = sin(2*pi*t/T) + 1, 范围 0(最暗)~2(最亮)
# LED 低电平点亮 -> duty = 1023*(1 - 亮度/2)
from machine import Pin, PWM
import math
import time

PIN_GREEN = 32
PIN_RED = 33
PIN_KEY1 = 35
PIN_KEY2 = 34

T_GREEN = 3.0   # 绿灯呼吸周期(秒)
T_RED = 5.0     # 红灯呼吸周期(秒)

def _make_led(pin):
    # 初始全灭: 低电平点亮, 故 duty=1023(全高)=灭
    return PWM(Pin(pin), freq=1000, duty=1023)

def _set_brightness(pwm, bright):
    # bright: 0~2 (sin+1), 0最暗 2最亮
    if bright < 0: bright = 0
    if bright > 2: bright = 2
    duty = int(1023 * (1.0 - bright / 2.0))
    pwm.duty(duty)

def breathe(pwm, period, duration):
    """让 pwm 灯以 period 周期正弦呼吸, 持续 duration 秒。"""
    t0 = time.ticks_ms()
    while True:
        el = time.ticks_diff(time.ticks_ms(), t0) / 1000.0
        if el >= duration:
            break
        phase = (el % period) / period          # 0~1
        bright = math.sin(2 * math.pi * phase) + 1.0   # 0~2
        _set_brightness(pwm, bright)
        time.sleep_ms(10)
    pwm.duty(1023)   # 结束灭

def breathe_green(duration=9.0):
    print("green breathe T=3s")
    breathe(_make_led(PIN_GREEN), T_GREEN, duration)

def breathe_red(duration=15.0):
    print("red breathe T=5s")
    breathe(_make_led(PIN_RED), T_RED, duration)

def _pressed(pin):
    if pin.value() == 0:
        time.sleep_ms(20)
        return pin.value() == 0
    return False

def _wait_release(pin):
    while pin.value() == 0:
        time.sleep_ms(10)

def main():
    key1 = Pin(PIN_KEY1, Pin.IN)
    key2 = Pin(PIN_KEY2, Pin.IN)
    green = _make_led(PIN_GREEN)
    red = _make_led(PIN_RED)
    print("ready: KEY1=green(3s) KEY2=red(5s)")
    while True:
        if _pressed(key1):
            print("KEY1 -> green breathe")
            breathe(green, T_GREEN, 9.0)   # 3个周期
            _wait_release(key1)
        elif _pressed(key2):
            print("KEY2 -> red breathe")
            breathe(red, T_RED, 15.0)      # 3个周期
            _wait_release(key2)
        time.sleep_ms(10)

if __name__ == "__main__":
    main()
