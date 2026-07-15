# ESP32-D0WD 三按键音乐盒 + 红绿灯闪烁
# 硬件依据: 修正ESP32_D0WD_硬件开发手册.md
#   GPIO25 经 Q3(NPN) 驱动外接扬声器 (原蜂鸣器位), 占空比 0~512 控制音量, 跳线 J11 需插上
#   LED2 绿 GPIO32 / LED3 红 GPIO33 (低电平点亮: value(0)=亮, value(1)=灭)
#   板载按键 (按下=0):
#     BOOT K1 = GPIO0  (需启用内部上拉, 手册 §4.3)
#     KEY1 K3 = GPIO34 (仅输入, 板上 R9 1kΩ 上拉, 勿设 PULL_UP)
#     KEY2 K4 = GPIO35 (仅输入, 板上 R12 1kΩ 上拉, 勿设 PULL_UP)
from machine import Pin, PWM
import time

time.sleep(0.5)  # 等待外设上电稳定 (手册 §7.1)

# ---------- 音符频率表 (Hz, A4=440 十二平均律) ----------
# 简谱转换: 1=do 2=re 3=mi 4=fa 5=sol 6=la 7=si; 注意简谱标注的调号(1=C 或 1=G 等),
# 不是 C 调的谱要整体移调, 不要机械地把 1 都当 C4
G3, A3, B3 = 196, 220, 247
C4, D4, E4, F4, G4, A4, B4 = 262, 294, 330, 349, 392, 440, 494
C5, D5, E5, F5, G5, A5, B5 = 523, 587, 659, 698, 784, 880, 988
FS4, GS4, AS4 = 370, 415, 466        # 升号音 (F#4 / G#4 / A#4)
CS5, DS5, FS5 = 554, 622, 740        # C#5 / D#5 / F#5
REST = 0

Q = 400   # 四分音符时长 ms
H = 800   # 二分音符
E8 = 200  # 八分音符

# ==================== 旋律数据区 (与播放逻辑分离, 可独立替换) ====================
# 格式: 每首歌是 (频率Hz, 时长ms) 元组的列表, 频率 0 = 休止符
# 时值参考: 八分音符 E8=200ms, 四分音符 Q=400ms, 附点四分 Q+E8=600ms, 二分 H=800ms
# 注意: 以下三首是凭记忆整理的近似版, 与原曲会有出入;
# 建议从授权乐谱/老师提供的简谱逐音核对后替换本区数据, 播放逻辑无需改动
# ================================================================================
# KEY1 (GPIO34) -> 周杰伦《你听得到》
# "有谁能比我知道 你的温柔像羽毛 秘密躺在我怀抱 只有你能听得到"
TINGDEDAO = [
    (G4,E8),(E4,E8),(G4,E8),(E4,E8),(G4,E8),(A4,E8),(G4,Q+E8),  # 有谁能比我知道
    (G4,E8),(E4,E8),(G4,E8),(E4,E8),(G4,E8),(D4,E8),(E4,Q+E8),  # 你的温柔像羽毛
    (G4,E8),(E4,E8),(G4,E8),(E4,E8),(G4,E8),(A4,E8),(G4,Q+E8),  # 秘密躺在我怀抱
    (E4,E8),(D4,E8),(C4,E8),(D4,E8),(E4,E8),(D4,Q),(C4,H),      # 只有你能听得到
]
# KEY2 (GPIO35) -> 《追光者》
# "我可以跟在你身后 像影子追着光梦游 ... 你是我的梦 像北方的风"
ZHUIGUANG = [
    (E4,E8),(E4,E8),(E4,E8),(E4,E8),(D4,E8),(E4,E8),(A4,Q),(G4,H),  # 我可以跟在你身后
    (E4,E8),(E4,E8),(E4,E8),(E4,E8),(D4,E8),(E4,E8),(D4,Q),(C4,H),  # 像影子追着光梦游
    (E4,E8),(E4,E8),(E4,E8),(E4,E8),(D4,E8),(E4,E8),(A4,Q),(G4,H),  # 我可以等在这路口
    (E4,E8),(E4,E8),(E4,E8),(E4,E8),(D4,E8),(E4,E8),(E4,Q),(D4,H),  # 不管你会不会经过
    (E4,Q),(G4,Q),(A4,Q),(C5,Q),(A4,H),                             # 你是我的梦
    (A4,Q),(C5,Q),(D5,Q),(C5,Q),(A4,Q),(G4,H),                      # 像北方的风
]
# BOOT (GPIO0) -> 《起风了》
# "我曾难自拔于世界之大 也沉溺于其中梦话 不得真假 不做挣扎 不惧笑话"
QIFENGLE = [
    (E4,E8),(A4,E8),(A4,E8),(A4,E8),(G4,E8),(A4,E8),
    (B4,E8),(A4,E8),(G4,E8),(A4,Q+E8),                              # 我曾难自拔于世界之大
    (E4,E8),(A4,E8),(A4,E8),(G4,E8),(A4,E8),(G4,E8),(E4,Q),(D4,H), # 也沉溺于其中梦话
    (A4,E8),(B4,E8),(C5,E8),(B4,Q),(REST,E8),                       # 不得真假
    (A4,E8),(B4,E8),(C5,E8),(B4,Q),(REST,E8),                       # 不做挣扎
    (A4,E8),(B4,E8),(C5,E8),(D5,Q),(B4,H),                          # 不惧笑话
]

# ---------- 外设初始化 ----------
buzzer = PWM(Pin(25), freq=440, duty=0)      # 初始静音
led_green = Pin(32, Pin.OUT, value=1)        # 1 = 灭 (低电平点亮)
led_red   = Pin(33, Pin.OUT, value=1)

btn_songs = [
    (Pin(34, Pin.IN),              TINGDEDAO, "你听得到 (KEY1)"),
    (Pin(35, Pin.IN),              ZHUIGUANG, "追光者 (KEY2)"),
    (Pin(0,  Pin.IN, Pin.PULL_UP), QIFENGLE,  "起风了 (BOOT)"),
]

def all_off():
    buzzer.duty(0)
    led_green.value(1)
    led_red.value(1)

# ---------- 扬声器版发声引擎 ----------
# GPIO25 外接动圈扬声器(经 Q3 驱动): 音量随占空比变化 (0=静音, 512=50% 最响),
# 因此可做真正的音量包络(ADSR)和颤音, 取代压电时代的频率滑音方案:
#   起音 attack: 音量 0 -> 峰值渐强, 消除爆音, 音头柔和
#   延音 sustain: 音量从峰值缓慢衰减(模拟钢琴触键), 长音叠加颤音(模拟人声)
#   释音 release: 音量渐弱到 0, 音符间过渡自然无咔哒声
import math

# 功率限制: 扬声器为 8Ω/0.5W, Q3 导通时喇叭上约 3V/375mA (瞬时 ~1.1W),
# 平均功率 = duty/1024 × 1.1W, 需 duty ≤ ~370 才不超 0.4W 安全线 — 勿调回 512!
PEAK   = 350    # 起音峰值占空比 (受 0.5W 功率限制, 见上)
SUS    = 230    # 延音起始占空比
ATT_MS = 20     # 起音时长
REL_MS = 70     # 释音时长
VIB_HZ    = 5.5    # 颤音频率 Hz
VIB_DEPTH = 0.012  # 颤音深度 ±1.2%
VIB_DELAY = 200    # 长音颤音起始延迟 ms (>=350ms 的音才加颤音)

def _poll_other_key(cur_idx):
    """检查是否有非当前歌曲的按键被按下, 返回其索引或 None"""
    for i in range(len(btn_songs)):
        if i != cur_idx and btn_songs[i][0].value() == 0:
            return i
    return None

def _wait_ms(ms, cur_idx):
    """分段延时, 期间轮询其它按键; 被按下则提前返回其索引"""
    t = 0
    while t < ms:
        step = min(10, ms - t)
        time.sleep_ms(step)
        t += step
        nxt = _poll_other_key(cur_idx)
        if nxt is not None:
            return nxt
    return None

def play_note(freq, dur_ms, idx, cur_idx):
    """带 ADSR 包络与颤音地播放一个音符; 红绿灯随音符节奏交替闪烁
    返回 None=正常结束, 或被按下的其它按键索引(立即切歌)"""
    # 偶数音符绿灯亮, 奇数音符红灯亮 (低电平点亮)
    led_green.value(idx % 2)
    led_red.value(1 - idx % 2)
    if freq == 0:                        # 休止符
        buzzer.duty(0)
        return _wait_ms(dur_ms, cur_idx)
    buzzer.freq(freq)
    # 起音: 渐强
    for i in range(1, 5):
        buzzer.duty(PEAK * i // 4)
        nxt = _wait_ms(ATT_MS // 4, cur_idx)
        if nxt is not None:
            return nxt
    # 延音: 峰值 -> SUS 线性衰减, 长音加颤音
    sus_ms = max(20, dur_ms - ATT_MS - REL_MS)
    duty = PEAK
    t = 0
    while t < sus_ms:
        k = t / sus_ms
        duty = int(PEAK - (PEAK - SUS) * k)
        f = freq
        if dur_ms >= 350 and t > VIB_DELAY:
            f = int(freq * (1 + VIB_DEPTH * math.sin(2 * math.pi * VIB_HZ * t / 1000)))
        buzzer.freq(f)
        buzzer.duty(duty)
        time.sleep_ms(10)
        t += 10
        nxt = _poll_other_key(cur_idx)
        if nxt is not None:
            return nxt
    # 释音: 渐弱至静音 (时间短, 不中断)
    for i in range(6, -1, -1):
        buzzer.duty(duty * i // 6)
        time.sleep_ms(REL_MS // 7)
    return None

def play_song(idx):
    """播放第 idx 首; 返回 None=正常播完, 或播放中被按下的新歌索引"""
    _pin, song, name = btn_songs[idx]
    print("播放:", name)
    for i, (freq, dur) in enumerate(song):
        nxt = play_note(freq, dur, i, idx)
        if nxt is not None:
            all_off()
            print("切歌 ->", btn_songs[nxt][2])
            return nxt
    all_off()
    print("播放完毕:", name)
    return None

# ---------- 主循环: 轮询按键 ----------
if __name__ == "__main__":              # 开机自动运行; import main 时不进循环, 便于 REPL 调试
    print("READY - KEY1=你听得到  KEY2=追光者  BOOT=起风了 (播放中按其它键可切歌)")
    all_off()
    pending = None                          # 待播放的歌曲索引
    while True:
        if pending is None:
            for i in range(len(btn_songs)):
                if btn_songs[i][0].value() == 0:    # 按下 = 低电平
                    time.sleep_ms(20)               # 消抖
                    if btn_songs[i][0].value() == 0:
                        pending = i
                        break
            time.sleep_ms(10)
        else:
            nxt = play_song(pending)
            if nxt is None:                 # 正常播完: 等本键松开, 防止重复触发
                pin = btn_songs[pending][0]
                while pin.value() == 0:
                    time.sleep_ms(10)
                pending = None
            else:                           # 播放中切歌
                time.sleep_ms(20)           # 消抖后直接播新歌
                pending = nxt
