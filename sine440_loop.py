# sine440_loop.py - 440Hz 正弦 (18点/周期), RMT 硬件循环无缝版
#
# 修复 sine440_fs7920.py 的"每 250ms 一声哒"缺陷:
#   旧版把波形铺成 1980 采样的大块反复 write_pulses, 每块 3960 个整数的
#   转换拷贝期间输出闲置在低电平 → 占空比偏置突然跌 0 又跳回 = 一声哒;
#   13 块 = 开头1 + 接缝12 + 结尾1 = 14 声, 与听感完全吻合
# 本版: 一个周期 18 采样 = 36 条脉冲 < RMT 通道硬件内存(64条),
#   loop(True) 后写入一次, 硬件自己无限循环 —— 零 CPU、零拷贝、零接缝;
#   v1.18 语义: loop(False) 会让当前圈播完再停, 下一次 write_pulses 正常接管
# 首尾仍加 10ms 直流斜坡防爆音 (小列表转换仅数十微秒, 接缝不可闻)
#
# RMT: 80MHz/101 → tick=1.2625us; 每采样 100 tick → 采样率 7920.8Hz
#   18 点一循环 → 音高 440.04Hz
import math
import time
from machine import Pin
import esp32

time.sleep(0.5)

TICKS = 100                 # 每采样 tick 数
CENTER = 50                 # 占空比中心 (PWM-DAC 零点)
AMP = 41                    # 振幅 → duty 摆动 9..91
DUR = 3.0                   # 播放时长 s
RAMP_N = 79                 # 首尾直流斜坡 10ms ≈ 79 采样

# 一个周期 18 个点 → 36 条脉冲, 常驻 RMT 硬件内存循环
period = []
for i in range(18):
    d = CENTER + int(round(AMP * math.sin(2.0 * math.pi * i / 18.0)))
    period.append(d)
    period.append(TICKS - d)

# 首尾直流斜坡 0→CENTER / CENTER→0
up, down = [], []
for i in range(RAMP_N):
    d = 1 + (CENTER - 1) * i // (RAMP_N - 1)
    up.append(d)
    up.append(TICKS - d)
    down.append(CENTER - (CENTER - 1) * i // (RAMP_N - 1))
    down.append(TICKS - down[-1])

rmt = esp32.RMT(0, pin=Pin(25), clock_div=101)

print("播放 440Hz 正弦(18点/周期, 硬件循环) %.1fs..." % DUR)
rmt.write_pulses(up, True)          # 斜坡把膜片送到偏置位
rmt.loop(True)
rmt.write_pulses(period, True)      # 36 条入硬件内存, 自循环, 立即返回
time.sleep(DUR)
rmt.loop(False)                     # 当前圈播完即停
rmt.write_pulses(down, True)        # 斜坡送回 0, 防结尾爆音
rmt.write_pulses((1,), False)       # 留在低电平空闲
time.sleep_ms(100)
rmt.deinit()
Pin(25, Pin.OUT, value=0)           # 确保 Q3 截止

print("结束。应当全程听不到任何哒声")
