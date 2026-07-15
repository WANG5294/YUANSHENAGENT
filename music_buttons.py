# ESP32-D0WD：三按键音乐盒 + 红绿呼吸灯随节拍
# 硬件（依据《修正ESP32_D0WD_硬件开发手册》）：
#   按键: GPIO5 / GPIO12 / GPIO14（J4 排针，外接开关到 GND，内部上拉，按下=0）
#   蜂鸣器: GPIO25（J11 跳线帽需插上，NPN 驱动，PWM 高电平发声）
#   LED: 绿 GPIO32 / 红 GPIO33，低电平点亮 → PWM duty 0=最亮, 1023=灭
import time
from machine import Pin, PWM

key_low = Pin(5, Pin.IN, Pin.PULL_UP)   # 按钮1 → 低音区旋律
key_mid = Pin(12, Pin.IN, Pin.PULL_UP)  # 按钮2 → 中音区旋律
key_high = Pin(14, Pin.IN, Pin.PULL_UP) # 按钮3 → 高音区旋律

buzzer = PWM(Pin(25), freq=440, duty=0)          # 初始静音
led_green = PWM(Pin(32), freq=1000, duty=1023)   # 初始灭
led_red = PWM(Pin(33), freq=1000, duty=1023)     # 初始灭

# 音符频率表（十二平均律）
C4, D4, E4, F4, G4, A4, B4 = 262, 294, 330, 349, 392, 440, 494
C5, D5, E5, F5, G5, A5, B5 = 523, 587, 659, 698, 784, 880, 988
C6, D6, E6, G6, A6 = 1047, 1175, 1319, 1568, 1760

# 三段旋律：(频率, 时长ms)，音区各不相同
MELODY_LOW = [  # 小星星片段，低音区
    (C4, 400), (C4, 400), (G4, 400), (G4, 400),
    (A4, 400), (A4, 400), (G4, 800),
]
MELODY_MID = [  # 欢乐颂片段，中音区
    (E5, 300), (E5, 300), (F5, 300), (G5, 300),
    (G5, 300), (F5, 300), (E5, 300), (D5, 300), (C5, 600),
]
MELODY_HIGH = [  # 高音区上行欢快音型
    (C6, 200), (D6, 200), (E6, 200), (G6, 400),
    (E6, 200), (G6, 400), (A6, 200), (G6, 600),
]

def all_leds_off():
    led_green.duty(1023)
    led_red.duty(1023)

def play_note(freq, dur_ms, led):
    """播放一个音符，同时让指定 LED 在这一拍内完成一次呼吸（暗→亮→暗）"""
    buzzer.freq(freq)
    buzzer.duty(512)          # 50% 占空比，最大音量
    steps = max(dur_ms // 20, 4)
    half = steps / 2
    for i in range(steps):
        # 三角波亮度 0→1→0，映射到低电平点亮的 duty（1023=灭, 0=最亮）
        b = i / half if i < half else (steps - i) / half
        led.duty(1023 - int(b * 1023))
        time.sleep_ms(20)
    buzzer.duty(0)            # 音符间静音，形成节拍感
    led.duty(1023)
    time.sleep_ms(50)

def play_melody(melody):
    for idx, (freq, dur) in enumerate(melody):
        # 红绿灯逐拍交替呼吸：偶数拍绿灯，奇数拍红灯
        led = led_green if idx % 2 == 0 else led_red
        play_note(freq, dur, led)
    all_leds_off()

all_leds_off()
while True:
    if key_low.value() == 0:
        play_melody(MELODY_LOW)
    elif key_mid.value() == 0:
        play_melody(MELODY_MID)
    elif key_high.value() == 0:
        play_melody(MELODY_HIGH)
    else:
        time.sleep_ms(20)
