# sine440_pure.py - 纯 440Hz 正弦波, 每个周期就是一条完整的正弦函数曲线
#
# 原理 (PWM-DAC, 与 GUOJIGE2 同一套路):
#   RMT tick=0.4us(80MHz/32), 每个采样输出一个 125tick 的 PWM 周期 → 采样率 20000Hz
#   每个采样的占空比 = 62 + 52*sin(2*pi*440*t): 占空比序列描出正弦曲线,
#   喇叭膜片跟不上 20kHz 的单个脉冲, 只跟随占空比的起伏 → 听到纯正弦
#
# 无缝循环: 440/20000 = 11/500, 即 500 个采样 = 恰好 11 个正弦周期,
#   预计算 2500 采样(55 周期, 125ms)反复送 RMT 即可, 板上零实时计算
#
# 对照: 之前的 duty 阶梯是"方波"(谐波齐全, 蜂鸣器味);
#       这个是"正弦"(只有 440Hz 单一成分), 同音高, 音色应明显更圆润
import math
import time
from machine import Pin
import esp32

time.sleep(0.5)

FS = 20000        # 采样率
TICKS = 125       # 每采样载波 tick 数 (2.5MHz/125 = 20kHz)
CENTER = 62       # 占空比中心 = PWM-DAC 的零点
AMP = 52          # 正弦振幅 → 占空比在 10..114 之间摆动
DUR = 3.0         # 播放时长 s
RAMP_MS = 10      # 首尾直流斜坡, 防爆音

LOOP_N = 2500     # 2500 采样 = 恰好 55 个 440Hz 周期, 尾首相接无缝

print("预计算 %d 采样 (55 个正弦周期)..." % LOOP_N)
dl = []
for i in range(LOOP_N):
    d = CENTER + int(round(AMP * math.sin(2.0 * math.pi * 440.0 * i / FS)))
    if d < 1:
        d = 1
    elif d > TICKS - 1:
        d = TICKS - 1
    dl.append(d)          # 高电平 tick 数
    dl.append(TICKS - d)  # 低电平 tick 数

# 首尾直流斜坡 0->CENTER / CENTER->0 (载波突现/突失本身就是"啪")
n_ramp = RAMP_MS * FS // 1000
up, down = [], []
for i in range(n_ramp):
    d = 1 + (CENTER - 1) * i // (n_ramp - 1)
    up.append(d)
    up.append(TICKS - d)
    down.append(CENTER - (CENTER - 1) * i // (n_ramp - 1))
    down.append(TICKS - down[-1])

rmt = esp32.RMT(0, pin=Pin(25), clock_div=32)

print("播放 440Hz 纯正弦 %.1fs..." % DUR)
rmt.write_pulses(up, True)
reps = int(DUR * FS) // LOOP_N          # 3s / 125ms = 24 段
for _ in range(reps):
    rmt.write_pulses(dl, True)          # v1.18: 自动等上一段播完, 无缝衔接
rmt.write_pulses(down, True)
rmt.write_pulses((1,), False)           # 留在低电平空闲, Q3 截止
time.sleep_ms(200)

print("结束。对比感受: 和之前 duty 阶梯的方波比, 音色是否更圆润、不刺耳?")
