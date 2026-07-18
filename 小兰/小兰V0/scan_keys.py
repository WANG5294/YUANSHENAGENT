# 探测按键和 LED 引脚
# 常见 ESP32 开发板引脚猜测

from machine import Pin
import time

# 常见按键引脚（输入，带上拉）
key_pins = [0, 2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33, 34, 35, 36, 39]

# 常见 LED 引脚（输出）
led_pins = [2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33]

print("=== 按键引脚扫描（按下时电平变化）===")
print("请依次按下 KEY1 和 KEY2，观察哪个引脚电平变化...")
print("扫描中，按 Ctrl-C 停止")
print()

# 初始化所有候选引脚为输入（带上拉）
pins = {}
for p in key_pins:
    try:
        pins[p] = Pin(p, Pin.IN, Pin.PULL_UP)
    except:
        pass

# 记录初始状态
last_state = {}
for p, pin in pins.items():
    try:
        last_state[p] = pin.value()
    except:
        pass

try:
    while True:
        for p, pin in pins.items():
            try:
                v = pin.value()
                if v != last_state[p]:
                    print(f"GPIO {p}: {last_state[p]} -> {v} {'<-- 按下!' if v == 0 else ''}")
                    last_state[p] = v
            except:
                pass
        time.sleep_ms(50)
except KeyboardInterrupt:
    print("\n扫描结束")
