# note440_envelope.py — 阶段1: 单音符音量包络测试 (440 Hz, 800 ms)
# 硬件依据: 修正ESP32_D0WD_硬件开发手册.md §4.1
#   GPIO25 — J11跳线(需插上) — R13 — Q3(NPN 8050) — 外接扬声器
#   KEY1=GPIO34, KEY2=GPIO35: 仅输入, 板上 1kΩ 上拉, 按下=0 (勿设 PULL_UP)
#
# 方案 (原代码是 A 类 tone 式 PWM, 本脚本改为逐采样生成):
#   MicroPython 纯 Python 循环做不到 15~22kHz 实时合成, 因此
#   1) 预计算: 逐采样生成 sin(2π·440t)·A(t), 量化为 7bit 占空比(中心=64), 存入 bytearray
#   2) 播放:   RMT 外设硬件定时输出, tick=0.5us (80MHz/40),
#              每个采样输出一个 128tick 的 PWM 周期 => 采样率 15625 Hz
#              write_pulses 会等上一段播完才开始新一段, 故可"硬件播这块, Python 备下块"
#   3) 防爆音: PWM-DAC 的"静音"是 50% 直流偏置, 载波突然出现/消失本身就是"啪";
#              在音符前后各加 10ms 直流斜坡 (0 -> 64 -> 0)
#
# 包络 A(t): 0~8ms 线性起音 / 8~680ms 指数衰减 tau=350ms / 680~800ms 线性收尾
# 按键: KEY1 = 正弦波+包络    KEY2 = 方波+同样包络 (听泛音差异, 方波偏亮偏硬)
# 验收: 1.起音无"啪"  2.响后逐渐变弱  3.结束不被突然切断

import math
import time
import gc
from machine import Pin
import esp32

time.sleep(0.5)              # 等待外设上电稳定 (手册 §7.1)

RATE = 15625                 # 采样率 Hz = 2MHz / 128
TICKS = 128                  # 每采样的载波 tick 数
FREQ = 440.0
DUR = 0.8                    # 音符总时长 s
N = int(RATE * DUR)          # 12500 采样
PRE = int(0.010 * RATE)      # 前置直流斜坡 10ms (防起始爆音)
POST = PRE                   # 后置直流斜坡 10ms (防结尾爆音)

ATK_N = int(0.008 * RATE)    # 起音 8ms = 125 采样
REL_S = int(0.68 * RATE)     # 释放起点 = 10625
DECAY = math.exp(-1.0 / (0.35 * RATE))   # 每采样衰减系数, tau=350ms

CHUNK = 2500                 # 每次喂给 RMT 的采样数 (160ms/块, 共6块)


def synth(tbl):
    """逐采样生成占空比缓冲: 值域 1..127, 中心 64; tbl 为一个周期的波形表 (-63..63)"""
    total = PRE + N + POST
    buf = bytearray(total)
    step = round(FREQ * (256 * 65536) / RATE)   # 相位步进 (高8位查表)
    t0 = time.ticks_ms()
    for i in range(PRE):                        # 0 -> 中心64
        buf[i] = 1 + (63 * i) // PRE
    acc = 0
    a = 0.0
    a_rel = 0.0
    rel_n = N - REL_S
    base = PRE
    for i in range(N):
        if i < ATK_N:
            a = i / ATK_N                       # 线性起音
        elif i < REL_S:
            a *= DECAY                          # 指数衰减
        else:
            if i == REL_S:
                a_rel = a                       # 衰减到达释放点时的幅度
            a = a_rel * (N - i) / rel_n         # 线性收尾到 0
        amp = int(a * 128)
        s = 64 + ((tbl[(acc >> 16) & 0xFF] * amp) >> 7)
        acc = (acc + step) & 0xFFFFFF
        if s < 1:
            s = 1                               # RMT 时长为 0 表示序列结束, 必须避开
        elif s > 127:
            s = 127
        buf[base + i] = s
    for i in range(POST):                       # 中心64 -> 0
        buf[base + N + i] = 64 - (63 * i) // POST
    print("synth: %d samples, %d ms" % (total, time.ticks_diff(time.ticks_ms(), t0)))
    return buf


class Player:
    def __init__(self):
        # idle_level 默认低电平: 静音时 Q3 截止, 扬声器无电流
        self.rmt = esp32.RMT(0, pin=Pin(25), clock_div=40)
        self.dl = [0] * (2 * CHUNK)   # 复用的时长表 (write_pulses 内部会拷贝)

    def _wait(self):
        while not self.rmt.wait_done():
            time.sleep_ms(5)

    def play(self, buf):
        """分块喂 RMT; write_pulses 自带"等上块播完"语义, 块间隙为 C 层耗时"""
        stats = []
        pos = 0
        n = len(buf)
        while pos < n:
            m = min(CHUNK, n - pos)
            dl = self.dl if m == CHUNK else [0] * (2 * m)
            j = 0
            for i in range(pos, pos + m):
                v = buf[i]
                dl[j] = v
                dl[j + 1] = TICKS - v
                j += 2
            t0 = time.ticks_us()
            self.rmt.write_pulses(dl, True)
            stats.append(time.ticks_diff(time.ticks_us(), t0))
            pos += m
        self._wait()
        return stats

def main():
    print("预计算 440Hz + ADSR 包络 ...")
    tbl_sin = [round(63.0 * math.sin(2 * math.pi * i / 256)) for i in range(256)]
    buf_sin = synth(tbl_sin)
    tbl_sq = [63 if i < 128 else -63 for i in range(256)]
    buf_sq = synth(tbl_sq)
    del tbl_sin, tbl_sq
    gc.collect()
    print("mem_free:", gc.mem_free())
    p = Player()
    print("播放 (正弦+包络) ...")
    st = p.play(buf_sin)
    print("write_pulses 各块耗时 us:", st)
    print("就绪: KEY1=正弦+包络  KEY2=方波+同样包络")
    k1 = Pin(34, Pin.IN)
    k2 = Pin(35, Pin.IN)
    while True:
        if k1.value() == 0:
            time.sleep_ms(20)                   # 消抖 (手册 §4.3)
            if k1.value() == 0:
                p.play(buf_sin)
                while k1.value() == 0:
                    time.sleep_ms(10)
        elif k2.value() == 0:
            time.sleep_ms(20)
            if k2.value() == 0:
                p.play(buf_sq)
                while k2.value() == 0:
                    time.sleep_ms(10)
        time.sleep_ms(10)


main()
