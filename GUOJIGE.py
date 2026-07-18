# GUOJIGE.py - 《国际歌》第一句，柔和琴音版（KEY1 播放）
#
# 硬件依据: 修正ESP32_D0WD_硬件开发手册.md
#   GPIO25 -> J11 -> Q3(NPN) -> MLT-5020 压电蜂鸣器
#   KEY1=GPIO34: 仅输入，板上 1kΩ 上拉，按下=0，勿设 PULL_UP
#
# 原版用音频频率方波发声，并用 duty 改“音量”。压电蜂鸣器对 duty 的响度
# 变化并不敏感，而且非 50% duty 会增加偶次谐波，所以声音容易又硬又薄。
# 本版用 RMT 输出 2kHz PWM-DAC（低频试听实验）：
#   1. 每个载波周期的 duty 表示一个波形采样，避免直接播放方波；
#   2. 音头含少量 2/3/4 次谐波，随后快速过渡到以基频为主的柔和音色；
#   3. 双时间常数响度衰减 + 末端 release，长音不会突然被截断；
#   4. 播放期间不读 flash；每个音符首尾做直流斜坡，避免停载波时爆音。
#
# 首次运行会在板上生成约 20KB 的 guojige_timbre.bin 缓存，之后直接播放。
import gc
import math
import time
import ujson
from machine import Pin
import esp32

time.sleep(0.5)

# ---------- 播放与音色参数 ----------
RATE = 2000                  # 80MHz / 200 / 200
RMT_DIV = 200                # RMT tick = 2.5us
TICKS = 200                  # 一个 PWM-DAC 采样周期
CENTER = 100                 # 50% duty 对应零振幅
LEVEL = 0.82                 # 调制深度；过大易削波，过小量化噪声明显
OUTPUT_ON_NUM = 1            # 输出导通时间比例 1/2，避免逐采样浮点分配
OUTPUT_ON_DEN = 2

ATTACK = 0.012               # 12ms，柔化音头但保留清晰度
RELEASE = 0.090              # 音符末端 90ms 线性释音
DECAY_FAST = 0.42            # 主体衰减时间常数
DECAY_SLOW = 1.80            # 基频尾音时间常数
BRIGHT_DECAY = 0.13          # 高频泛音比基频更快消失
BEAT = 0.60                  # 100 BPM
NOTE_RAMP = int(0.004 * RATE)  # 每个音符首尾 4ms 直流斜坡

CACHE_VERSION = "warm-piano-v5-2khz"
BIN_FILE = "guojige_timbre.bin"
INDEX_FILE = "guojige_timbre.json"

# 音符频率 (Hz, A4=440 十二平均律, 1=C)
E4, F4, G4, A4, B4 = 330, 349, 392, 440, 494
C5, D5 = 523, 587
REST = 0

# 第2小节的延音线 6~6 已合并成一个 2 拍音符。
MELODY = [
    (G4, 1),
    (C5, 1.5), (B4, 0.5), (D5, 0.5), (C5, 0.5), (G4, 0.5), (E4, 0.5),
    (A4, 2), (F4, 1), (REST, 0.5), (A4, 0.5),
    (D5, 1.5), (C5, 0.5), (B4, 0.5), (A4, 0.5), (G4, 0.5), (F4, 0.5),
    (E4, 3),
]


def _normalised_table(harmonics):
    """生成 256 点单周期波表，并按实际峰值归一化。"""
    raw = []
    peak = 0.0
    for i in range(256):
        phase = 2.0 * math.pi * i / 256.0
        value = 0.0
        for multiple, amplitude in harmonics:
            value += amplitude * math.sin(multiple * phase)
        raw.append(value)
        if abs(value) > peak:
            peak = abs(value)
    scale = CENTER * LEVEL / peak
    return [int(round(value * scale)) for value in raw]


def make_timbre_tables():
    # warm 是尾音；bright 只在音头占较大比例，随后由 BRIGHT_DECAY 淡出。
    warm = _normalised_table(((1, 1.00), (2, 0.06), (3, 0.02)))
    bright = _normalised_table(
        ((1, 1.00), (2, 0.28), (3, 0.12), (4, 0.04))
    )
    delta = [bright[i] - warm[i] for i in range(256)]
    return warm, delta


def synth_note(frequency, duration, warm, bright_delta, out):
    """把一个音符合成到预分配缓冲，返回有效采样数。"""
    count = int(round(duration * RATE))
    if frequency == REST:
        # 休止期间保持近似低电平，避免无意义地输出 50% 的 2kHz 载波。
        for i in range(count):
            out[i] = 1
        return count

    attack_n = max(1, int(ATTACK * RATE))
    release_n = min(count - attack_n, int(RELEASE * RATE))
    release_at = count - release_n
    phase_step = int(round(frequency * (256 * 65536) / RATE))
    phase = 0

    fast = 1.0
    slow = 1.0
    brightness = 0.78 if frequency < C5 else 0.66
    fast_k = math.exp(-1.0 / (DECAY_FAST * RATE))
    slow_k = math.exp(-1.0 / (DECAY_SLOW * RATE))
    bright_k = math.exp(-1.0 / (BRIGHT_DECAY * RATE))

    for i in range(count):
        if i < attack_n:
            amplitude = i / attack_n
        else:
            fast *= fast_k
            slow *= slow_k
            brightness *= bright_k
            amplitude = 0.72 * fast + 0.28 * slow
        if i >= release_at:
            amplitude *= (count - i) / release_n

        p = (phase >> 16) & 0xFF
        wave = warm[p] + int(brightness * bright_delta[p])
        duty = CENTER + int(amplitude * wave)
        phase = (phase + phase_step) & 0xFFFFFF

        # RMT 中 0 表示序列结束，因此高、低电平时长都必须至少为 1 tick。
        if duty < 1:
            duty = 1
        elif duty > TICKS - 1:
            duty = TICKS - 1
        out[i] = duty
    return count


def cache_signature():
    return "%s|%d|%.3f|%.3f|%.3f|%.2f|%.2f|%.2f|%.2f" % (
        CACHE_VERSION, RATE, LEVEL, ATTACK, RELEASE,
        DECAY_FAST, DECAY_SLOW, BRIGHT_DECAY, BEAT
    )


def cache_ok():
    try:
        with open(INDEX_FILE) as fp:
            meta = ujson.load(fp)
        if meta.get("signature") != cache_signature():
            return False
        sizes = meta.get("sizes")
        if not sizes or len(sizes) != len(MELODY):
            return False
        with open(BIN_FILE, "rb") as fp:
            fp.seek(0, 2)
            return fp.tell() == sum(sizes)
    except (OSError, ValueError):
        return False


def generate_cache():
    """首次开机逐音符合成到 flash；LED2 亮表示正在处理。"""
    led = Pin(32, Pin.OUT, value=0)
    warm, bright_delta = make_timbre_tables()
    gc.collect()
    max_note = int(round(max(item[1] for item in MELODY) * BEAT * RATE))
    sample_buf = bytearray(max_note)
    sample_view = memoryview(sample_buf)
    ramp_up = bytearray(
        1 + ((CENTER - 1) * i) // (NOTE_RAMP - 1)
        for i in range(NOTE_RAMP)
    )
    ramp_down = bytearray(reversed(ramp_up))
    sizes = []
    total = 0
    started = time.ticks_ms()
    try:
        with open(BIN_FILE, "wb") as fp:
            for index, (frequency, beats) in enumerate(MELODY):
                count = synth_note(
                    frequency, BEAT * beats, warm, bright_delta, sample_buf
                )
                samples = sample_view[:count]
                if frequency == REST:
                    fp.write(samples)
                    size = len(samples)
                else:
                    fp.write(ramp_up)
                    fp.write(samples)
                    fp.write(ramp_down)
                    size = len(samples) + 2 * NOTE_RAMP
                sizes.append(size)
                total += size
                print("合成 %d/%d: %dHz, %.1f拍" % (
                    index + 1, len(MELODY), frequency, beats
                ))
                del samples
                gc.collect()

        with open(INDEX_FILE, "w") as fp:
            ujson.dump({
                "signature": cache_signature(),
                "rate": RATE,
                "center": CENTER,
                "samples": total,
                "sizes": sizes,
            }, fp)
    finally:
        led.value(1)
    print("音色缓存完成: %d samples, %dms" % (
        total, time.ticks_diff(time.ticks_ms(), started)
    ))


if not cache_ok():
    print("首次运行或参数已变化，正在生成音色缓存（LED2 亮）...")
    generate_cache()
else:
    print("使用已有音色缓存")

with open(INDEX_FILE) as _index:
    SIZES = ujson.load(_index)["sizes"]
gc.collect()

# ---------- 逐音符 RAM 播放 ----------
# flash 读取只发生在 RMT 空闲时；播放期间只访问 RAM，避免喂数中断受干扰。
CHUNK = 500                  # 2kHz 下每块 250ms
note_buf = bytearray(max(SIZES))
note_view = memoryview(note_buf)
pulses = [1] * (CHUNK * 2)
rmt = esp32.RMT(0, pin=Pin(25), clock_div=RMT_DIV)


def sync_idle():
    # write_pulses 会先等待上一段完成；单个低电平脉冲把输出可靠地留在空闲态。
    rmt.write_pulses((1,), False)


def play():
    with open(BIN_FILE, "rb") as fp:
        for size in SIZES:
            sync_idle()
            if fp.readinto(note_view[:size]) != size:
                raise OSError("音色缓存读取不完整")
            gc.collect()

            pos = 0
            while pos < size:
                count = min(CHUNK, size - pos)
                j = 0
                for i in range(pos, pos + count):
                    duty = note_buf[i]
                    # 缩短高电平导通时间但保持总周期 TICKS 不变，因此频率不变。
                    on_ticks = max(1, (duty * OUTPUT_ON_NUM) // OUTPUT_ON_DEN)
                    pulses[j] = on_ticks
                    pulses[j + 1] = TICKS - on_ticks
                    j += 2
                durations = pulses if count == CHUNK else pulses[:2 * count]
                rmt.write_pulses(durations, True)
                durations = None
                pos += count
    sync_idle()
    gc.collect()


key1 = Pin(34, Pin.IN)
print("就绪: 按 KEY1(GPIO34) 播放《国际歌》第一句（柔和琴音）")
while True:
    if key1.value() == 0:
        time.sleep_ms(20)
        if key1.value() == 0:
            play()
            while key1.value() == 0:
                time.sleep_ms(10)
    time.sleep_ms(10)
