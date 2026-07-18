# 按下 KEY1 播放 do(C4 262Hz)，3 秒，响度从 100% 沿直线降到 0%。
# 频率不变，PDM 脉冲密度调制实现线性衰减，平滑无锯齿无爆音。
from machine import Pin, PWM
import time

DO_FREQ = 262          # C4
DURATION_MS = 3000     # 总时长 3 秒
SEG_MS = 25            # 每段 25ms，共 120 段
N_SEG = DURATION_MS // SEG_MS

buzzer = PWM(Pin(25), freq=DO_FREQ, duty=0)
key1 = Pin(35, Pin.IN)   # KEY1 = GPIO35，板载上拉，按下为 0


def _ratio(i):
    """第 i 段发声比例：线性 1.0 -> 0.0，等步长，严格单调（无锯齿）。"""
    return 1.0 - i / (N_SEG - 1)


def play():
    """播放一次 3 秒线性衰减 do。可被 import 后软件触发。"""
    buzzer.freq(DO_FREQ)
    buzzer.duty(0)
    seg_us = SEG_MS * 1000
    t0 = time.ticks_us()
    for i in range(N_SEG):
        r = _ratio(i)
        on_us = int(seg_us * r)
        seg_start = time.ticks_add(t0, i * seg_us)
        # 段内发声部分
        if on_us > 0:
            buzzer.duty(512)
            target = time.ticks_add(seg_start, on_us)
            while time.ticks_diff(target, time.ticks_us()) > 0:
                pass
        # 段内静音部分（含末段 r=0 时整段静音）
        buzzer.duty(0)
        target = time.ticks_add(seg_start, seg_us)
        while time.ticks_diff(target, time.ticks_us()) > 0:
            pass
    buzzer.duty(0)


def main():
    print("ready: press KEY1 -> do 262Hz, 3s, linear 100%->0%")
    while True:
        if key1.value() == 0:
            time.sleep_ms(20)          # 消抖
            if key1.value() == 0:
                play()
                while key1.value() == 0:   # 等松开，防连发
                    time.sleep_ms(10)
        time.sleep_ms(10)


main()
