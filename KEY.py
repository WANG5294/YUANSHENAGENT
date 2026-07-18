# KEY.py - KEY1 依次试听 5 种钢琴中音 Do (C4)
#
# 板级连接依据: 修正ESP32_D0WD_硬件开发手册.md
#   KEY1 = GPIO34，板上已有 1k 上拉，按下为低电平。
#   GPIO25 经 J11/R13 控制 Q3；板载原负载由 VCC(3.3V)供电。
#
# 重要硬件警告:
#   8ohm 喇叭若直接接在 GPIO25 和 GND 之间，理论峰值电流约 3.3/8=0.41A，
#   远超 ESP32 GPIO 能力。下面的 POWER_NUM/POWER_DEN 只能降低平均导通时间，
#   不能降低高电平瞬间的峰值电流。直连时必须加串联限流电阻/功放，并建议
#   加隔直电容；更合理的接法是用 Q3 或专用音频功放驱动喇叭。
#
# 按一次 KEY1 后依次播放:
#   1. 纯正弦基准
#   2. 动态整数泛音
#   3. 三弦轻微失谐
#   4. 音槌 + 非谐模态
#   5. 混合三弦三角钢琴
# 每种声音之间静音 1 秒。首次启动生成约 126KB 缓存，LED2 亮表示合成中。
import gc
import math
import time
import ujson
from machine import Pin
import esp32

time.sleep(0.5)

# ---------- 硬件输出 ----------
RATE = 20000                 # 80MHz / 32 / 125 = 20kHz
RMT_DIV = 32
TICKS = 125
CENTER = 62                  # 未限流波形的零振幅中心
MOD_TICKS = 32               # 降低低频冲程，让8ohm喇叭振动更平顺

# 实际高电平时间 = 合成 duty * 1/5。
# 零振幅附近 Q3 平均导通约 (62/125)/5 = 9.9%。
POWER_NUM = 1
POWER_DEN = 5

NOTE_HZ = 261.626            # C4，中音 Do
DURATION = 1.25              # 每种音色时长 s
PAUSE_MS = 1000              # 音色之间静音 1s
ATTACK_MS = (24, 22, 22, 20, 20)
RELEASE = 0.24
RAMP = int(0.004 * RATE)     # 低电平 <-> PWM 静音中心，抑制爆音

CACHE_VERSION = "key-piano-c4-v2-smooth"
BIN_FILE = "key_piano.bin"
INDEX_FILE = "key_piano.json"

STYLE_NAMES = (
    "1/5 纯正弦基准",
    "2/5 动态整数泛音",
    "3/5 三弦轻微失谐",
    "4/5 音槌与非谐模态",
    "5/5 混合三弦三角钢琴",
)

# (相对基频, 初始幅度, 独立衰减时间常数s)
# 每组幅度总和约为 1；高次模态衰减更快，使音头亮、尾音柔和。
MODELS = (
    (
        ((1.0000, 1.00, 0.82),),
        0.00, 0.020,
    ),
    (
        ((1.0000, 0.72, 1.10), (2.0000, 0.17, 0.34),
         (3.0000, 0.08, 0.21), (4.0000, 0.03, 0.13)),
        0.00, 0.020,
    ),
    (
        ((0.9992, 0.28, 1.15), (1.0000, 0.35, 1.25),
         (1.0009, 0.27, 1.08), (2.0040, 0.07, 0.36),
         (3.0150, 0.03, 0.22)),
        0.00, 0.020,
    ),
    (
        ((1.0000, 0.60, 1.30), (2.0100, 0.18, 0.46),
         (3.0300, 0.10, 0.29), (4.0700, 0.06, 0.20),
         (5.1200, 0.035, 0.14), (6.1800, 0.025, 0.10)),
        0.06, 0.022,
    ),
    (
        ((0.9993, 0.22, 1.38), (1.0000, 0.30, 1.45),
         (1.0008, 0.22, 1.32), (2.0080, 0.12, 0.50),
         (3.0250, 0.07, 0.31), (4.0550, 0.04, 0.21),
         (5.1000, 0.02, 0.14), (6.1600, 0.01, 0.10)),
        0.035, 0.020,
    ),
)

Q14 = 1 << 14
PHASE_SCALE = 256 * 65536


def make_sine_table():
    return [
        int(round(32767 * math.sin(2 * math.pi * i / 256)))
        for i in range(256)
    ]


def synth_style(style_index, sine, out):
    """用整数相位与 Q14 衰减器合成一种琴音，返回有效采样数。"""
    modes, noise_level, noise_tau = MODELS[style_index]
    count = int(round(DURATION * RATE))
    phases = [0] * len(modes)
    steps = [
        int(round(NOTE_HZ * ratio * PHASE_SCALE / RATE))
        for ratio, _amplitude, _tau in modes
    ]
    amplitudes = [int(round(amplitude * Q14)) for _r, amplitude, _t in modes]
    decays = [
        int(round(math.exp(-16.0 / (tau * RATE)) * Q14))
        for _ratio, _amplitude, tau in modes
    ]
    noise_amp = int(round(noise_level * Q14))
    noise_decay = int(round(math.exp(-1.0 / (noise_tau * RATE)) * Q14))
    attack = max(1, int(ATTACK_MS[style_index] * RATE / 1000))
    release = max(1, int(RELEASE * RATE))
    release_at = count - release
    random_state = 0xACE1 ^ (style_index * 97)
    filtered = 0

    for i in range(count):
        sample = 0
        for mode_index in range(len(modes)):
            p = (phases[mode_index] >> 16) & 0xFF
            sample += (sine[p] * amplitudes[mode_index]) >> 14
            phases[mode_index] = (phases[mode_index] + steps[mode_index]) & 0xFFFFFF
            if (i & 15) == 15:
                amplitudes[mode_index] = (
                    amplitudes[mode_index] * decays[mode_index]
                ) >> 14

        if noise_amp:
            lsb = random_state & 1
            random_state >>= 1
            if lsb:
                random_state ^= 0xB400
            noise = random_state - 32768
            sample += (noise * noise_amp) >> 14
            noise_amp = (noise_amp * noise_decay) >> 14

        if sample > 32767:
            sample = 32767
        elif sample < -32767:
            sample = -32767

        # 一阶低通抑制锤击毛刺和高次模态的机械冲击感。
        filtered += (sample - filtered) >> 2
        sample = filtered

        if i < attack:
            x = (i * Q14) // attack
            gain = (((x * x) >> 14) * (3 * Q14 - 2 * x)) >> 14
            sample = (sample * gain) >> 14
        if i >= release_at:
            x = ((count - i) * Q14) // release
            gain = (((x * x) >> 14) * (3 * Q14 - 2 * x)) >> 14
            sample = (sample * gain) >> 14

        raw_duty = CENTER + ((sample * MOD_TICKS) >> 15)
        duty = max(1, (raw_duty * POWER_NUM) // POWER_DEN)
        if duty > TICKS - 1:
            duty = TICKS - 1
        out[i] = duty
    return count


def signature():
    return "%s|%d|%.3f|%.2f|%d|%d" % (
        CACHE_VERSION, RATE, NOTE_HZ, DURATION, POWER_NUM, POWER_DEN
    )


def cache_ok():
    try:
        with open(INDEX_FILE) as fp:
            meta = ujson.load(fp)
        sizes = meta.get("sizes")
        if meta.get("signature") != signature() or len(sizes) != len(MODELS):
            return False
        with open(BIN_FILE, "rb") as fp:
            fp.seek(0, 2)
            return fp.tell() == sum(sizes)
    except (OSError, TypeError, ValueError):
        return False


def generate_cache():
    led = Pin(32, Pin.OUT, value=0)
    sine = make_sine_table()
    gc.collect()
    sample_count = int(round(DURATION * RATE))
    sample_buf = bytearray(sample_count)
    sample_view = memoryview(sample_buf)
    idle_duty = max(1, (CENTER * POWER_NUM) // POWER_DEN)
    ramp_up = bytearray(
        1 + ((idle_duty - 1) * i) // (RAMP - 1) for i in range(RAMP)
    )
    ramp_down = bytearray(reversed(ramp_up))
    sizes = []
    started = time.ticks_ms()
    try:
        with open(BIN_FILE, "wb") as fp:
            for style_index in range(len(MODELS)):
                count = synth_style(style_index, sine, sample_buf)
                fp.write(ramp_up)
                fp.write(sample_view[:count])
                fp.write(ramp_down)
                sizes.append(count + 2 * RAMP)
                print("已合成", STYLE_NAMES[style_index])
                gc.collect()
        with open(INDEX_FILE, "w") as fp:
            ujson.dump({
                "signature": signature(),
                "rate": RATE,
                "sizes": sizes,
            }, fp)
    finally:
        led.value(1)
    print("5种琴音缓存完成: %dms" % time.ticks_diff(time.ticks_ms(), started))


if not cache_ok():
    print("首次运行，正在合成5种钢琴音色（LED2亮）...")
    generate_cache()
else:
    print("使用已有钢琴音色缓存")

with open(INDEX_FILE) as _index:
    SIZES = ujson.load(_index)["sizes"]
gc.collect()

# ---------- RMT 播放器 ----------
CHUNK = 2500                # 125ms/块；flash 只在音色播放前读取
note_buf = bytearray(max(SIZES))
note_view = memoryview(note_buf)
pulses = [1] * (CHUNK * 2)
rmt = esp32.RMT(0, pin=Pin(25), clock_div=RMT_DIV)


def sync_idle():
    rmt.write_pulses((1,), False)


def play_segment(fp, size):
    sync_idle()
    if fp.readinto(note_view[:size]) != size:
        raise OSError("钢琴音色缓存读取不完整")
    gc.collect()
    pos = 0
    while pos < size:
        count = min(CHUNK, size - pos)
        j = 0
        for i in range(pos, pos + count):
            duty = note_buf[i]
            pulses[j] = duty
            pulses[j + 1] = TICKS - duty
            j += 2
        durations = pulses if count == CHUNK else pulses[:2 * count]
        rmt.write_pulses(durations, True)
        durations = None
        pos += count
    sync_idle()


def play_all_styles():
    with open(BIN_FILE, "rb") as fp:
        for style_index, size in enumerate(SIZES):
            print("播放:", STYLE_NAMES[style_index])
            play_segment(fp, size)
            if style_index != len(SIZES) - 1:
                time.sleep_ms(PAUSE_MS)
    gc.collect()
    print("5种音色试听完成")


key1 = Pin(34, Pin.IN)
print("就绪: 按 KEY1 依次试听5种钢琴中音Do，每种间隔1秒")
while True:
    if key1.value() == 0:
        time.sleep_ms(20)
        if key1.value() == 0:
            play_all_styles()
            while key1.value() == 0:
                time.sleep_ms(10)
    time.sleep_ms(10)
