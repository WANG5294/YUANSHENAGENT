# ESP32-D0WD:板载三按键音乐盒(KEY1 / KEY2 / BOOT 播放不同音乐)
# 硬件(依据《修正ESP32_D0WD_硬件开发手册》):
#   KEY1 = GPIO34(仅输入,板上 R9 1kΩ 上拉,按下=0)
#   KEY2 = GPIO35(仅输入,板上 R12 1kΩ 上拉,按下=0)
#   BOOT = GPIO0 (板上 10kΩ 上拉,按下=0;仅运行时作输入,不影响已启动的程序)
#   蜂鸣器 = GPIO25(J11 跳线帽插上,NPN 驱动,PWM 高电平发声)
#   LED: 绿 GPIO32 / 红 GPIO33,低电平点亮
import time
from machine import Pin, PWM

key1 = Pin(34, Pin.IN)              # 仅输入引脚,无内部上拉,依赖板上 R9
key2 = Pin(35, Pin.IN)              # 仅输入引脚,无内部上拉,依赖板上 R12
boot = Pin(0, Pin.IN, Pin.PULL_UP)  # 板上也有外部上拉

buzzer = PWM(Pin(25), freq=440, duty=0)  # 初始静音
led_green = Pin(32, Pin.OUT, value=1)    # 1=灭(低电平点亮)
led_red = Pin(33, Pin.OUT, value=1)

# 音符频率表(十二平均律)
C4, D4, E4, F4, G4, A4, B4 = 262, 294, 330, 349, 392, 440, 494
C5, D5, E5, F5, G5, A5, B5 = 523, 587, 659, 698, 784, 880, 988
C6, D6, E6, G6, A6 = 1047, 1175, 1319, 1568, 1760

MELODY_STAR = [  # KEY1:小星星
    (C5, 400), (C5, 400), (G5, 400), (G5, 400),
    (A5, 400), (A5, 400), (G5, 800),
    (F5, 400), (F5, 400), (E5, 400), (E5, 400),
    (D5, 400), (D5, 400), (C5, 800),
]
MELODY_ODE = [  # KEY2:欢乐颂
    (E5, 300), (E5, 300), (F5, 300), (G5, 300),
    (G5, 300), (F5, 300), (E5, 300), (D5, 300),
    (C5, 300), (C5, 300), (D5, 300), (E5, 300),
    (E5, 450), (D5, 150), (D5, 600),
]
MELODY_JINGLE = [  # BOOT:铃儿响叮当
    (E5, 250), (E5, 250), (E5, 500),
    (E5, 250), (E5, 250), (E5, 500),
    (E5, 250), (G5, 250), (C5, 375), (D5, 125), (E5, 750),
]

def play_note(freq, dur_ms, led):
    buzzer.freq(freq)
    buzzer.duty(512)      # 50% 占空比,压电蜂鸣器最大音量
    led.value(0)          # 低电平点亮
    time.sleep_ms(dur_ms)
    buzzer.duty(0)        # 音符间静音,形成节拍感
    led.value(1)
    time.sleep_ms(50)

def play_melody(melody):
    for idx, (freq, dur) in enumerate(melody):
        led = led_green if idx % 2 == 0 else led_red
        play_note(freq, dur, led)
    led_green.value(1)
    led_red.value(1)

while True:
    if key1.value() == 0:
        play_melody(MELODY_STAR)
    elif key2.value() == 0:
        play_melody(MELODY_ODE)
    elif boot.value() == 0:
        play_melody(MELODY_JINGLE)
    else:
        time.sleep_ms(20)
