# sine440_fs4400.py - 采样率 4400Hz, 每个 440Hz 周期取 10 个点
#
# 10 点/周期 (奈奎斯特极限的 5 倍): 正弦轮廓已能勾出来, 但是 10 级台阶
# 预测: 440Hz 主音比方波圆润, 但叠着刺耳高频 —— 4400Hz 载波及其镜像
#   (4400±440 = 3960/4840Hz) 都在听域内, 膜片跟得上, 无人滤除
# 对照组: 2 点(全毁) → 10 点(有形但有毛刺) → 45 点@20kHz(干净)
#
# RMT: 80MHz/200 → tick=2.5us; 每采样 91 tick → 4395.6Hz (4400 无法整除, 差0.1%)
#   10 点一循环 → 音高 439.56Hz, 比 440 低 1.7 音分, 人耳不可辨
import math
import time
from machine import Pin
import esp32

time.sleep(0.5)

TICKS = 91                  # 每采样 tick 数, 91*2.5us=227.5us → 采样率 4395.6Hz
CENTER = 45                 # 62*91/125, 占空比中心等比缩放
AMP = 37                    # 52*91/125, 振幅等比缩放 → duty 摆动 8..82
DUR = 3.0

# 一个周期 10 个点的正弦查表
period = []
for i in range(10):
    d = CENTER + int(round(AMP * math.sin(2.0 * math.pi * i / 10.0)))
    period.append(d)
print("10 点占空比表:", period)

# 铺成 200 个周期(2000 采样, 455ms)的脉冲块, 反复发送
dl = []
for _ in range(200):
    for d in period:
        dl.append(d)
        dl.append(TICKS - d)

rmt = esp32.RMT(0, pin=Pin(25), clock_div=200)
reps = int(DUR * 4395.6) // 2000 + 1
print("播放 440Hz 正弦(10点/周期) %.1fs..." % DUR)
for _ in range(reps):
    rmt.write_pulses(dl, True)      # v1.18: 等上一块播完再接, 无缝
rmt.write_pulses((1,), False)       # 回低电平空闲
time.sleep_ms(200)

print("结束。对比: 主音是否已比方波圆润? 是否听到一层高频哨音(载波)?")
