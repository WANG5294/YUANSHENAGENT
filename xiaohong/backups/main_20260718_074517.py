from machine import Pin
import time

# ========== 引脚定义 ==========
# 按键（仅输入，板载上拉，按下=0）
KEY1 = Pin(35, Pin.IN)   # 丝印 KEY1
KEY2 = Pin(34, Pin.IN)   # 丝印 KEY2
BOOT = Pin(0, Pin.IN, Pin.PULL_UP)  # BOOT键

# 外接LED引脚（高电平点亮：GPIO → LED → 电阻 → GND）
LED_PINS = [5, 12, 14, 18, 19, 21, 22, 23]
leds = [Pin(p, Pin.OUT, value=0) for p in LED_PINS]  # 初始全灭

NUM_LEDS = len(LED_PINS)  # 8

def all_off():
    """熄灭所有LED"""
    for led in leds:
        led.value(0)

def set_led(index, on):
    """点亮/熄灭指定索引的LED"""
    if 0 <= index < NUM_LEDS:
        leds[index].value(1 if on else 0)

def show_count(n):
    """点亮前n个LED，其余熄灭"""
    for i in range(NUM_LEDS):
        leds[i].value(1 if i < n else 0)

def debounce(pin):
    """消抖检测，返回True表示确认按下"""
    if pin.value() == 0:
        time.sleep_ms(20)
        return pin.value() == 0
    return False

def wait_release(pin):
    """等待按键释放"""
    while pin.value() == 0:
        time.sleep_ms(10)

# ========== 模式1：流水灯循环 ==========
def running_light():
    """流水灯：G05→G12→...→G23→G05... 每个亮1秒，BOOT停止"""
    print("[MODE1] 流水灯开始，按BOOT停止")
    idx = 0
    while True:
        # 检查BOOT停止
        if BOOT.value() == 0:
            time.sleep_ms(20)
            if BOOT.value() == 0:
                all_off()
                wait_release(BOOT)
                print("[MODE1] BOOT停止，退出流水灯")
                return
        # 点亮当前LED
        all_off()
        set_led(idx, True)
        print("[MODE1] LED G{:02d} ON (index={})".format(LED_PINS[idx], idx))
        # 亮1秒，期间持续检测BOOT
        elapsed = 0
        while elapsed < 1000:
            if BOOT.value() == 0:
                time.sleep_ms(20)
                if BOOT.value() == 0:
                    all_off()
                    wait_release(BOOT)
                    print("[MODE1] BOOT停止，退出流水灯")
                    return
            time.sleep_ms(10)
            elapsed += 10
        idx = (idx + 1) % NUM_LEDS

# ========== 模式2：KEY2计时亮灯 ==========
def key2_mode():
    """按下KEY2后开始计时，亮灯数 = (秒数) % 8"""
    print("[MODE2] KEY2计时模式开始")
    start = time.ticks_ms()
    last_sec = -1
    while True:
        # 检查BOOT停止
        if BOOT.value() == 0:
            time.sleep_ms(20)
            if BOOT.value() == 0:
                all_off()
                wait_release(BOOT)
                print("[MODE2] BOOT停止，退出计时模式")
                return
        elapsed_s = time.ticks_diff(time.ticks_ms(), start) // 1000
        if elapsed_s != last_sec:
            last_sec = elapsed_s
            count = elapsed_s % 8
            show_count(count)
            print("[MODE2] {}s elapsed, {} LEDs ON".format(elapsed_s, count))
        time.sleep_ms(50)

# ========== 主循环 ==========
def main():
    all_off()
    print("=" * 40)
    print("LED 控制系统就绪")
    print("KEY1: 流水灯循环 (BOOT停止)")
    print("KEY2: 计时亮灯 (秒数%%8)")
    print("=" * 40)
    while True:
        if debounce(KEY1):
            wait_release(KEY1)
            running_light()
        elif debounce(KEY2):
            wait_release(KEY2)
            key2_mode()
        time.sleep_ms(10)

main()
