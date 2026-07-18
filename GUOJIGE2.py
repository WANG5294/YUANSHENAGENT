# GUOJIGE2.py — 《国际歌》第一句, 单片机逐采样合成复合波形版 (KEY1 播放)
# 基于 GUOJIGE.py 修改: 旋律/包络参数不变, 发声由 PWM 方波改为板上按公式逐采样计算:
#   x[n] = M·A(n/Fs)/1.45 · [ sin(2πf0·n/Fs) + 0.30·sin(2π·2f0·n/Fs) + 0.15·sin(2π·3f0·n/Fs) ]
#   sample[n] = 32767·x[n]                    (16bit 中间量)
#   duty[n]   = 62 + (sample[n]·62 >> 15)     (映射到 7bit PWM-DAC, 中心 62)
# 响度包络 A(t) (同 GUOJIGE.py): Ta 线性起音 / 指数衰减 exp(-(t-Ta)/Td) /
#   末端 Tr 线性收尾, Aoff=exp(-(T-Tr-Ta)/Td); T=音符自身时值
#
# 实现说明:
#   - 纯 Python 无法在 20kHz 下边播边算(每采样仅 50us), 因此首次开机把整句
#     逐音符算好缓存进 flash (GUOJIGE2.bin/.json, 约10~20s, 绿灯亮表示合成中);
#     参数不变则直接用缓存, 秒开
#   - 三个正弦之和是以 1/f0 为周期的固定波形 → 折成一张 256 点单周期查表,
#     逐采样只做 "查表 × 包络" (查表值已含 M、÷1.45 与 32767 量化)
#   - 播放: RMT 硬件定时, tick=0.4us(80MHz/32), 每采样 125tick PWM 周期 = 恰好 20000Hz
#   - 播放期间绝不读 flash (会阻塞 RMT 喂数中断变杂音), 逐音符先载入 RAM;
#     音符首块 500 采样快出声, 后续 1000/2500 大块在播放掩护下准备
#   - 首尾各 10ms 直流斜坡 (0→62→0) 防爆音; RMT 时长 0=序列结束, 占空比钳 1..124
# 硬件: GPIO25 — J11跳线(需插上) — Q3(NPN) — 外接扬声器
#       KEY1=GPIO34 仅输入, 板上 1kΩ 上拉, 按下=0; LED2 绿=GPIO32 低电平点亮
import gc
import math
import time
import ujson
from machine import Pin
import esp32

time.sleep(0.5)              # 等待外设上电稳定 (手册 §7.1)

# ---------- 合成参数 ----------
FS = 20000                   # 采样率 Hz = 2.5MHz / 125
TICKS = 125                  # 每采样载波 tick 数
CENTER = 62                  # 占空比中心 (PWM-DAC 的"零点")
M = 0.2                      # 总音量系数 (建议 0.1~0.2; 7bit 输出下调大到 0.5~1.0 更响更细腻)
TA = 0.008                   # attack 起音 s
TD = 0.35                    # decay 衰减时间常数 s
TR = 0.12                    # release 收尾 s
BEAT = 0.6                   # 一拍 s (约100BPM)
RAMP = int(0.010 * FS)       # 首尾直流斜坡 10ms

# 音符频率 (Hz, A4=440 十二平均律, 1=C)
E4, F4, G4, A4, B4 = 330, 349, 392, 440, 494   # 中音 3 4 5 6 7
C5, D5 = 523, 587                              # 高音 1̇ 2̇
REST = 0

# (频率Hz, 拍数); 第2小节 6~6 延音线已合并为 2 拍不重新起音
MELODY = [
    (G4, 1),                                                             # 弱起 5
    (C5, 1.5), (B4, 0.5), (D5, 0.5), (C5, 0.5), (G4, 0.5), (E4, 0.5),   # 第1小节
    (A4, 2), (F4, 1), (REST, 0.5), (A4, 0.5),                           # 第2小节
    (D5, 1.5), (C5, 0.5), (B4, 0.5), (A4, 0.5), (G4, 0.5), (F4, 0.5),   # 第3小节
    (E4, 3),                                                             # 第4小节 3拍
]

BIN = "GUOJIGE2.bin"
IDX = "GUOJIGE2.json"
# 参数签名: 任一参数变动 → 缓存失效自动重新合成
SIG = "v2 %d %s %s %s %s %s %s %d" % (FS, M, TA, TD, TR, BEAT, CENTER, len(MELODY))


def make_tbl():
    """复合波形单周期查表: TBL[i] = 32767·M·[sinθ+0.30sin2θ+0.15sin3θ]/1.45"""
    tbl = []
    for i in range(256):
        th = 2.0 * math.pi * i / 256.0
        w = (math.sin(th) + 0.30 * math.sin(2.0 * th)
             + 0.15 * math.sin(3.0 * th)) / 1.45
        tbl.append(int(32767.0 * M * w))
    return tbl


def synth_note(tbl, f, dur, buf):
    """逐采样计算一个音符, 量化为占空比 1..124 存入 buf, 返回样本数"""
    n = int(round(dur * FS))
    if f == REST:
        for i in range(n):
            buf[i] = CENTER          # 休止: 保持直流中心 (静音, 不掉 0 防爆音)
        return n
    atk = int(TA * FS)
    rel = int((dur - TR) * FS)       # 收尾起点采样号
    k = math.exp(-1.0 / (TD * FS))   # 衰减递推系数 (等价 exp(-(t-Ta)/Td))
    step = int(round(f * (256 * 65536) / FS))   # 相位步进, 高 8 位查表
    acc = 0
    a = 0.0
    arel = 0.0
    for i in range(n):
        if i < atk:
            a = i / atk              # 线性起音
        elif i < rel:
            a *= k                   # 指数衰减
        else:
            if i == rel:
                arel = a             # = Aoff
            a = arel * (n - i) / (n - rel)   # 线性收尾到 0
        s16 = int(a * tbl[(acc >> 16) & 0xFF])      # = 32767·x[n]
        acc = (acc + step) & 0xFFFFFF
        v = CENTER + ((s16 * CENTER) >> 15)         # 16bit → 7bit 占空比
        if v < 1:
            v = 1
        elif v > 124:
            v = 124
        buf[i] = v
    return n


def cache_ok():
    try:
        with open(IDX) as fp:
            return ujson.load(fp).get("sig") == SIG
    except (OSError, ValueError):
        return False


def generate():
    led = Pin(32, Pin.OUT, value=0)              # 绿灯亮 = 正在合成
    tbl = make_tbl()
    buf = bytearray(int(round(3 * BEAT * FS)) + RAMP)   # 最长音符(3拍)+斜坡余量
    sizes = []
    t0 = time.ticks_ms()
    last = len(MELODY) - 1
    with open(BIN, "wb") as out:
        for j, (f, beats) in enumerate(MELODY):
            n = synth_note(tbl, f, BEAT * beats, buf)
            sz = n
            if j == 0:                           # 首段前加 0→62 斜坡
                out.write(bytearray(1 + ((CENTER - 1) * i) // RAMP
                                    for i in range(RAMP)))
                sz += RAMP
            out.write(memoryview(buf)[:n])
            if j == last:                        # 末段后加 62→0 斜坡
                out.write(bytearray(CENTER - ((CENTER - 1) * i) // RAMP
                                    for i in range(RAMP)))
                sz += RAMP
            sizes.append(sz)
            print("合成 %d/%d (%dHz, %.1f拍)" % (j + 1, last + 1, f, beats))
    with open(IDX, "w") as fp:
        ujson.dump({"sig": SIG, "rate": FS, "center": CENTER, "sizes": sizes}, fp)
    led.value(1)                                 # 灭灯 = 合成完毕
    print("板上合成完成: %d ms" % time.ticks_diff(time.ticks_ms(), t0))
    return sizes


if cache_ok():
    with open(IDX) as _fp:
        SIZES = ujson.load(_fp)["sizes"]
    print("使用 flash 缓存 (参数未变)")
else:
    print("首次运行/参数已变: 单片机逐采样合成整句 (绿灯亮, 约10~20s) ...")
    SIZES = generate()
gc.collect()

# ---------- 播放 (逐音符载入, 播放期间零 flash 访问) ----------
rmt = esp32.RMT(0, pin=Pin(25), clock_div=32)   # tick=0.4us, 空闲低电平静音
dl = [0] * (2 * 2500)        # 复用时长表: 整块 2500 采样 = 125ms
d500 = [0] * 1000            # 音符首块/次块, 预分配免 GC 停顿
d1000 = [0] * 2000
CHUNK = 2500
nbuf = bytearray(max(SIZES))                    # 单音符 RAM 缓冲 (最长约 36KB)
nmv = memoryview(nbuf)


def wait_idle():
    while not rmt.wait_done():
        time.sleep_ms(2)


def play():
    with open(BIN, "rb") as fp:
        for sz in SIZES:
            wait_idle()                  # RMT 空闲后才碰 flash
            fp.readinto(nmv[:sz])        # 音符间静音点载入下一个音符
            pos = 0
            step = 500                   # 首块小尽快出声, 大块在播放掩护下备好
            collected = False
            while pos < sz:
                m = min(step, sz - pos)
                step = 1000 if step == 500 else CHUNK
                if m == CHUNK:
                    d = dl
                elif m == 500:
                    d = d500
                elif m == 1000:
                    d = d1000
                else:
                    d = [0] * (2 * m)    # 仅音符尾部零头
                j = 0
                for i in range(pos, pos + m):
                    v = nbuf[i]
                    d[j] = v
                    d[j + 1] = TICKS - v
                    j += 2
                rmt.write_pulses(d, True)
                pos += m
                if m == CHUNK and not collected:
                    gc.collect()         # 125ms 整块播放掩护下回收 (纯 RAM 不扰 RMT)
                    collected = True
    wait_idle()


key1 = Pin(34, Pin.IN)
print("就绪: 按 KEY1(GPIO34) 播放《国际歌》第一句 (复合波形)")
while True:
    if key1.value() == 0:
        time.sleep_ms(20)                # 消抖
        if key1.value() == 0:
            play()
            while key1.value() == 0:
                time.sleep_ms(10)
    time.sleep_ms(10)
