# sine440_fs880.py - 把采样率从 20000Hz 降到 880Hz 会怎样?
#
# 880Hz 采样 = 每个 440Hz 周期只有 2 个点 (正好踩在奈奎斯特 2 倍极限上):
#   A段: duty = 62 + 52*sin(2*pi*440*i/880) = 62 + 52*sin(pi*i) = 全是 62!
#        正弦信息全部丢失, 只剩 880Hz 载波自己的通断声
#   B段: 采样相位挪 1/4 周期 → 62 + 52*cos(pi*i) = 114,10,114,10...
#        摆幅拉满, 但只是 440Hz 方波 (2 个点画不出曲线, 只能画台阶)
#
# 载波问题: 20kHz 时膜片跟不上单个脉冲, 载波隐形; 880Hz 膜片完全跟得上,
#   载波直接被听见 → PWM-DAC "用惯性抹掉开关细节" 的前提在这里不成立
#
# RMT: 80MHz/200 → tick=2.5us; 每采样 455 tick → 879.12Hz (880 无法整除, 差 0.1%)
import math
import time
from machine import Pin
import esp32

time.sleep(0.5)

TICKS = 455       # 每采样 tick 数, 455*2.5us = 1137.5us → 采样率约 879Hz
CENTER = 62 * 455 // 125   # 占空比中心, 按 20kHz 版等比放大 = 225
AMP = 52 * 455 // 125      # 振幅等比放大 = 189
DUR = 2.0

rmt = esp32.RMT(0, pin=Pin(25), clock_div=200)
n = int(DUR * 879)         # 每段采样数


def play(phase, name):
    print(name)
    dl = []
    for i in range(n):
        d = CENTER + int(round(AMP * math.sin(math.pi * i + phase)))
        if d < 1:
            d = 1
        elif d > TICKS - 1:
            d = TICKS - 1
        dl.append(d)
        dl.append(TICKS - d)
        if len(dl) >= 4000:            # 分块送, 免得列表过大
            rmt.write_pulses(dl, True)
            dl = []
    if dl:
        rmt.write_pulses(dl, True)
    rmt.write_pulses((1,), False)      # 回到低电平空闲
    time.sleep_ms(800)


play(0.0, "A段: 原公式 sin(pi*i), 每点都是中心值 → 预测只闻 880Hz 载波")
play(math.pi / 2, "B段: 相位挪 1/4 周期 cos(pi*i) → 预测 440Hz 方波蜂鸣")

print("结束。两段听到的都不是圆润的正弦 —— 2 点/周期画不出曲线")
