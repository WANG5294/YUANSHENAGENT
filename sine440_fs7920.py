# sine440_fs7920.py - 采样率 7920Hz, 每个 440Hz 周期取 18 个点
#
# 阶梯系列第 3 档: 2点(全毁) → 10点(有形+明显哨音) → 18点(本档) → 45点@20kHz(干净)
# 预测: 主音圆润度与 10 点相近, 但镜像哨音升到 7920±440 = 7480/8360Hz,
#   更高更弱 (人耳灵敏度下降 + 台阶保持的 sinc 滚降压制更强)
#
# RMT: 80MHz/101 → tick=1.2625us; 每采样 100 tick → 7920.8Hz
#   18 点一循环 → 音高 440.04Hz (差 0.2 音分, 完全听不出)
import math
import time
from machine import Pin
import esp32

time.sleep(0.5)

TICKS = 100                 # 每采样 tick 数 → 采样率 7920.8Hz
CENTER = 50                 # 占空比中心 (62/125 等比缩放)
AMP = 41                    # 52/125 等比缩放 → duty 摆动 9..91
DUR = 3.0

period = []
for i in range(18):
    d = CENTER + int(round(AMP * math.sin(2.0 * math.pi * i / 18.0)))
    period.append(d)
print("18 点占空比表:", period)

# 110 个周期(1980 采样, 250ms)铺成一块, 反复发送
dl = []
for _ in range(110):
    for d in period:
        dl.append(d)
        dl.append(TICKS - d)

rmt = esp32.RMT(0, pin=Pin(25), clock_div=101)
reps = int(DUR * 7920.8) // 1980 + 1
print("播放 440Hz 正弦(18点/周期) %.1fs..." % DUR)
for _ in range(reps):
    rmt.write_pulses(dl, True)
rmt.write_pulses((1,), False)
time.sleep_ms(200)

print("结束。和 10 点版比: 哨音是否更高更弱? 主音是否一样圆?")
