from machine import Pin, PWM
import time

# ---------- 硬件初始化 ----------
key1 = Pin(35, Pin.IN)            # KEY1，板载上拉，按下=0
key2 = Pin(34, Pin.IN)            # KEY2，板载上拉，按下=0

led_green = Pin(32, Pin.OUT, value=1)   # 绿灯，低电平亮，初始灭
led_red   = Pin(33, Pin.OUT, value=1)   # 红灯，低电平亮，初始灭

buzzer = PWM(Pin(25), freq=440, duty=0) # 蜂鸣器，初始静音

# ---------- 小星星曲谱 ----------
# 音名 -> 频率 (Hz)
NOTE = {
    'C4': 262, 'D4': 294, 'E4': 330, 'F4': 349,
    'G4': 392, 'A4': 440, 'B4': 494, 'C5': 523,
    '-': 0,   # 休止符
}

# 小星星: 一闪一闪亮晶晶...
# (音名, 拍数)  1拍 = BEAT ms
SONG = [
    ('C4',1),('C4',1),('G4',1),('G4',1),
    ('A4',1),('A4',1),('G4',2),
    ('F4',1),('F4',1),('E4',1),('E4',1),
    ('D4',1),('D4',1),('C4',2),
    ('G4',1),('G4',1),('F4',1),('F4',1),
    ('E4',1),('E4',1),('D4',2),
    ('G4',1),('G4',1),('F4',1),('F4',1),
    ('E4',1),('E4',1),('D4',2),
    ('C4',1),('C4',1),('G4',1),('G4',1),
    ('A4',1),('A4',1),('G4',2),
    ('F4',1),('F4',1),('E4',1),('E4',1),
    ('D4',1),('D4',1),('C4',2),
]

BEAT = 300  # 一拍毫秒数

def both_pressed():
    """检测两键是否同时按下（带消抖）"""
    return key1.value() == 0 and key2.value() == 0

def play_song_with_blink():
    """播放小星星，同时两灯轮流闪烁；松开任意键立即退出"""
    for name, beats in SONG:
        if not both_pressed():          # 任意键松开则中断
            break
        freq = NOTE[name]
        dur = BEAT * beats
        if freq == 0:
            buzzer.duty(0)
        else:
            buzzer.freq(freq)
            buzzer.duty(512)
        # 在音符持续时间内做轮流闪烁，同时检测按键
        half = dur // 2
        led_red.value(0); led_green.value(1)   # 红亮绿灭
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < half:
            if not both_pressed():
                break
            time.sleep_ms(10)
        led_red.value(1); led_green.value(0)   # 红灭绿亮
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < dur - half:
            if not both_pressed():
                break
            time.sleep_ms(10)
    buzzer.duty(0)
    led_red.value(1); led_green.value(1)

def all_off():
    led_red.value(1)
    led_green.value(1)
    buzzer.duty(0)

# ---------- 主循环 ----------
print("ready: KEY1=red, KEY2=green, BOTH=song+blink")
all_off()

while True:
    k1 = key1.value() == 0
    k2 = key2.value() == 0

    if k1 and k2:
        time.sleep_ms(20)               # 消抖确认
        if both_pressed():
            play_song_with_blink()
            all_off()
            # 等待松开，避免重复触发
            while both_pressed():
                time.sleep_ms(20)
    elif k1:
        led_red.value(0)                # 红灯亮
        led_green.value(1)
        buzzer.duty(0)
    elif k2:
        led_green.value(0)              # 绿灯亮
        led_red.value(1)
        buzzer.duty(0)
    else:
        all_off()

    time.sleep_ms(20)
