#!/usr/bin/env python3
# gen_guojige2.py — PC 端生成《国际歌》第一句的复合波形采样文件 (配套板端 GUOJIGE2.py)
#
# 波形 (基频 + 3 个泛音, 高次泛音随时间更快消失, 接近琴弦受敲击后的音色变化):
#   x(t) = [ sin(2πft) + 0.30·e^(−t/0.30)·sin(4πft)
#          + 0.15·e^(−t/0.18)·sin(6πft) + 0.07·e^(−t/0.10)·sin(8πft) ] / 1.52
# 响度包络 A(t) (同 GUOJIGE.py): Ta=8ms 线性起音 / Td=350ms 指数衰减 /
#   末端 Tr=120ms 线性收尾; Tend=音符自身时值, Toff=Tend−Tr
# 输出采样 = 64 + round(63 · A(t) · x(t)), 钳位 1..127 (7bit PWM 占空比, 中心 64)
#
# 产物:
#   GUOJIGE2.bin         — 板上播放用 (15625 Hz, 每字节一个占空比采样)
#   GUOJIGE2_preview.wav — 16bit PCM 预览, PC 上直接试听
import math
import wave
import struct

RATE = 15625                 # 与板端 RMT 播放器一致 (2MHz/128)
BEAT = 0.6                   # 一拍 s (100 BPM)
TA, TD, TR = 0.008, 0.35, 0.12
# (泛音次数 k, 幅度, 衰减时间常数 tau; tau=0 表示不额外衰减)
HARMONICS = [(1, 1.00, 0.0), (2, 0.30, 0.30), (3, 0.15, 0.18), (4, 0.07, 0.10)]
NORM = sum(a for _, a, _ in HARMONICS)   # 1.52, 归一化防削波
RAMP = int(0.010 * RATE)                 # 首尾 10ms 直流斜坡防爆音

# 音符频率 (1=C, A4=440 十二平均律), 与 GUOJIGE.py 完全一致
E4, F4, G4, A4, B4 = 330, 349, 392, 440, 494
C5, D5 = 523, 587
REST = 0

MELODY = [
    (G4, 1),                                                             # 弱起 5
    (C5, 1.5), (B4, 0.5), (D5, 0.5), (C5, 0.5), (G4, 0.5), (E4, 0.5),   # 第1小节
    (A4, 2), (F4, 1), (REST, 0.5), (A4, 0.5),                           # 第2小节 (6~6延音线合并)
    (D5, 1.5), (C5, 0.5), (B4, 0.5), (A4, 0.5), (G4, 0.5), (F4, 0.5),   # 第3小节
    (E4, 3),                                                             # 第4小节 3拍, 谱面到此为止
]


def note_samples(f, dur):
    n = int(round(dur * RATE))
    out = bytearray(n)
    if f == REST:
        for i in range(n):
            out[i] = 64          # 休止: 保持直流中心, 不掉到 0 (避免爆音)
        return out
    toff = dur - TR
    aoff = math.exp(-(toff - TA) / TD)
    w = 2.0 * math.pi * f
    for i in range(n):
        t = i / RATE
        if t < TA:
            a = t / TA
        elif t < toff:
            a = math.exp(-(t - TA) / TD)
        else:
            a = aoff * (dur - t) / TR
        x = 0.0
        for k, amp, tau in HARMONICS:
            g = amp if tau == 0.0 else amp * math.exp(-t / tau)
            x += g * math.sin(k * w * t)
        s = 64 + int(round(63.0 * a * x / NORM))
        out[i] = 127 if s > 127 else (1 if s < 1 else s)
    return out


# 按音符分段: 板端播放器逐段载入 RAM 再播 (播放期间不能读 flash,
# 否则 flash 读取会阻塞 RMT 喂数中断, 输出变成杂音), 段尺寸索引存 json
segs = []
for f, beats in MELODY:
    segs.append(note_samples(f, BEAT * beats))
segs[0] = bytearray(1 + (63 * i) // RAMP for i in range(RAMP)) + segs[0]    # 首段前加 0->64 斜坡
segs[-1] = segs[-1] + bytearray(64 - (63 * i) // RAMP for i in range(RAMP)) # 末段后加 64->0 斜坡

song = bytearray()
for s in segs:
    song += s

with open("GUOJIGE2.bin", "wb") as fp:
    fp.write(song)
import json
with open("GUOJIGE2.json", "w") as fp:
    json.dump({"rate": RATE, "center": 64, "sizes": [len(s) for s in segs]}, fp)

with wave.open("GUOJIGE2_preview.wav", "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(RATE)
    wf.writeframes(b"".join(
        struct.pack("<h", int((v - 64) / 63.0 * 28000)) for v in song))

print("GUOJIGE2.bin: %d samples, %.2f s" % (len(song), len(song) / RATE))
