# key440_note.py - KEY1 触发播放 3s 440Hz 音符, 自定义抛物线响度包络
#
# 规格 (用户给定):
#   采样点数 = 16 x 440 x 3 = 21120 (16 点/周期, 3 秒)
#   响度 A(t) = 1 - 10(t-0.3)^2   (0 < t < 0.3, 从 0.1 抛物线升至 1)
#          A(t) = 1 - 0.11(t-0.3)^2 (0.3 < t < 3, 从 1 缓降至 0.198)
#   占空比[i] = 473 + A(t)*388*sin(2*pi*i/16), 摆动 85..861 / 947
#
# RMT: 80MHz/12 → tick=0.15us; 每采样 947 tick → 采样率 7039.77Hz
#      16 点/周期 → 音高 439.99Hz
#
# 防哒声 (实测: 块间空隙恒 35us, 与块大小无关, 转换与播放重叠):
#   - 包络逐采样变化, 波形非周期 → 不能硬件循环, 只能分块流水
#   - "切口藏进谷底"已被实测证伪(2026-07-16, 21 声哒且尾部更响): 哒声的
#     本质是 35us 空隙丢失的平均电平(电荷亏空 ≈ 233tick x 偏置), 深度与
#     音量无关, 所以包络衰减后反而更露; 缓边沿补不回电荷
#   - 对策 = 电荷补偿: 每块最后一个采样的高电平加宽 233tick(=35us),
#     把亏空提前补上, 凹坑与补偿相邻 140us 内, 经膜片低通后相抵
#   - 播放期间零 flash 读取、零列表分配 (双缓冲列表就地填充)
#   - 首尾 10ms 直流斜坡防爆音
import gc
import math
import time
from array import array
from machine import Pin
import esp32

time.sleep(0.5)

FS = 7040.0
TICKS = 947
CENTER = 473
AMP = 388
N = 16 * 440 * 3            # 21120 采样
CHUNK = 1056                # 66 周期/块, 20 块整
RAMP_N = 70                 # 首尾直流斜坡 10ms

led = Pin(32, Pin.OUT, value=1)      # 绿 LED 低电平亮
key1 = Pin(34, Pin.IN)               # 板上 1k 上拉, 按下=0, 勿设 PULL_UP

# ---------- 开机合成: 21120 个占空比存入 RAM ----------
print("合成 %d 采样 (16点/周期 x 3s)..." % N)
led.value(0)
SIN16 = [math.sin(2.0 * math.pi * j / 16.0) for j in range(16)]
duty = array('H', bytearray(2 * N))
for i in range(N):
    t = i / FS
    if t < 0.3:
        a = 1.0 - 10.0 * (t - 0.3) * (t - 0.3)
    else:
        a = 1.0 - 0.11 * (t - 0.3) * (t - 0.3)
    duty[i] = int(CENTER + AMP * a * SIN16[i & 15] + 0.5)
led.value(1)

# 电荷补偿: 每个块尾采样高电平 +233tick, 抵消块间 35us 低电平亏空
COMP = 233
for pos in range(CHUNK - 1, N, CHUNK):
    d = duty[pos] + COMP
    duty[pos] = d if d < TICKS else TICKS - 1

gc.collect()
print("合成完成, 剩余内存:", gc.mem_free())

# 首尾直流斜坡与双缓冲块列表 (预分配, 播放期间零分配)
up = []
down = []
for i in range(RAMP_N):
    d = 1 + (CENTER - 1) * i // (RAMP_N - 1)
    up.append(d)
    up.append(TICKS - d)
    down.append(CENTER - (CENTER - 1) * i // (RAMP_N - 1))
    down.append(TICKS - down[-1])
up[-2] += COMP              # 斜坡→首块的接缝同样补偿
up[-1] -= COMP
bufA = [0] * (2 * CHUNK)
bufB = [0] * (2 * CHUNK)

rmt = esp32.RMT(0, pin=Pin(25), clock_div=12)


def fill(buf, pos):
    j = 0
    for i in range(pos, pos + CHUNK):
        d = duty[i]
        buf[j] = d
        buf[j + 1] = TICKS - d
        j += 2


def play():
    led.value(0)
    gc.collect()                     # 先腾空, 播放中不再有大回收
    rmt.write_pulses(up, True)       # 0→中心 斜坡
    bufs = (bufA, bufB)
    k = 0
    for pos in range(0, N, CHUNK):
        buf = bufs[k & 1]
        fill(buf, pos)               # 填充与上一块播放重叠进行
        rmt.write_pulses(buf, True)  # 等上块播完→接缝仅 35us 且藏在低电平段
        k += 1
    rmt.write_pulses(down, True)     # 中心→0 斜坡
    rmt.write_pulses((1,), False)    # 低电平空闲, Q3 截止
    led.value(1)


print("就绪: 按 KEY1(GPIO34) 播放 3s 440Hz 音符 (抛物线包络)")
while True:
    if key1.value() == 0:
        time.sleep_ms(20)
        if key1.value() == 0:
            play()
            while key1.value() == 0:
                time.sleep_ms(10)
    time.sleep_ms(10)
