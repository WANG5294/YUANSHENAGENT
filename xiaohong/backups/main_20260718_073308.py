from machine import Pin, PWM
import time

# ========== 引脚定义 ==========
# 8个小灯 GPIO (低电平点亮)
LED_PINS = [5, 12, 14, 18, 19, 21, 22, 23]
leds = [Pin(p, Pin.OUT, value=1) for p in LED_PINS]  # 初始全灭

# 按键
KEY1 = Pin(35, Pin.IN)   # 丝印 KEY1 = GPIO35
KEY2 = Pin(34, Pin.IN)   # 丝印 KEY2 = GPIO34
BOOT = Pin(0, Pin.IN, Pin.PULL_UP)

# 蜂鸣器
buzzer = PWM(Pin(25), freq=440, duty=0)

# ========== 音阶映射 ==========
# 灯索引: 0=G05(do) 1=G12(re) 2=G14(mi) 3=G18(fa)
#          4=G19(sol) 5=G21(la) 6=G22(si) 7=G23(高do)
NOTES = {
    'do':   0,  # C4  262Hz
    're':   1,  # D4  294Hz
    'mi':   2,  # E4  330Hz
    'fa':   3,  # F4  349Hz
    'sol':  4,  # G4  392Hz
    'la':   5,  # A4  440Hz
    'si':   6,  # B4  494Hz
    'doh':  7,  # C5  523Hz
}
NOTE_FREQ = [262, 294, 330, 349, 392, 440, 494, 523]

# 《小星星》旋律 (音名, 时值ms)
TWINKLE = [
    ('do', 400), ('do', 400), ('sol', 400), ('sol', 400),
    ('la', 400), ('la', 400), ('sol', 800),
    ('fa', 400), ('fa', 400), ('mi', 400), ('mi', 400),
    ('re', 400), ('re', 400), ('do', 800),
    ('sol', 400), ('sol', 400), ('fa', 400), ('fa', 400),
    ('mi', 400), ('mi', 400), ('re', 800),
    ('sol', 400), ('sol', 400), ('fa', 400), ('fa', 400),
    ('mi', 400), ('mi', 400), ('re', 800),
    ('do', 400), ('do', 400), ('sol', 400), ('sol', 400),
    ('la', 400), ('la', 400), ('sol', 800),
    ('fa', 400), ('fa', 400), ('mi', 400), ('mi', 400),
    ('re', 400), ('re', 400), ('do', 800),
]


def all_leds_off():
    for led in leds:
        led.value(1)


def led_on(idx):
    """点亮指定索引的灯（低电平有效）"""
    all_leds_off()
    leds[idx].value(0)


def buzz_on(freq):
    buzzer.freq(freq)
    buzzer.duty(512)


def buzz_off():
    buzzer.duty(0)


def key1_mode():
    """KEY1: 灯循环, 扬声器不发声"""
    buzz_off()
    all_leds_off()
    idx = 0
    while not BOOT.value():  # BOOT按下为0, 按下停止
        led_on(idx)
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < 1000:
            if BOOT.value() == 0:
                all_leds_off()
                return
            time.sleep_ms(20)
        idx = (idx + 1) % 8


def key2_mode():
    """KEY2: 播放小星星, 发声+灯同步"""
    buzz_off()
    all_leds_off()
    for note_name, duration_ms in TWINKLE:
        idx = NOTES[note_name]
        freq = NOTE_FREQ[idx]
        led_on(idx)
        buzz_on(freq)
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < duration_ms:
            if KEY1.value() == 0 or BOOT.value() == 0:
                buzz_off()
                all_leds_off()
                return
            time.sleep_ms(20)
        buzz_off()
        # 音与音之间短间隔
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < 50:
            if KEY1.value() == 0 or BOOT.value() == 0:
                all_leds_off()
                return
            time.sleep_ms(10)
    all_leds_off()


# ========== 主循环 ==========
def if __name__ == '__main__':
    main():
    all_leds_off()
    buzz_off()
    while True:
        if KEY1.value() == 0:
            time.sleep_ms(30)  # 消抖
            if KEY1.value() == 0:
                key1_mode()
                # 等KEY1释放
                while KEY1.value() == 0:
                    time.sleep_ms(20)
        elif KEY2.value() == 0:
            time.sleep_ms(30)
            if KEY2.value() == 0:
                key2_mode()
                while KEY2.value() == 0:
                    time.sleep_ms(20)
        time.sleep_ms(50)


main()
