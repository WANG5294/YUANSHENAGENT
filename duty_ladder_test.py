# duty_ladder_test.py - 440Hz 固定, duty 10%~100% 阶梯试听
#
# 目的: 验证"占空比 = 音量"是否成立。
# 预期 (通过 Q3 开关管驱动):
#   - 交流有效值 ∝ sqrt(d*(1-d)): 50% 最响, 10% 与 90% 一样轻, 100% 无声
#   - 音色随 duty 变: 50% 无偶次谐波(空), 偏离 50% 谐波变齐(尖/薄)
#   - d 与 1-d 波形只差极性, 人耳应无法区分
#
# 注意: duty 越大直流发热越大 (100% 时约 1W 全落在喇叭+Q3 上),
#       故每级只播 2s、级间静音 0.8s 散热, 整个测试只跑一遍。
import time
from machine import Pin, PWM

FREQ = 440
STEP_MS = 2000       # 每级 2s
GAP_MS = 800         # 级间静音

pwm = PWM(Pin(25), freq=FREQ, duty=0)
led = Pin(32, Pin.OUT, value=1)   # 绿 LED, 低电平亮, 播放时点亮

try:
    for pct in range(10, 101, 10):
        duty = 1023 * pct // 100
        print("duty %3d%%  (%4d/1023)  播 2s..." % (pct, duty))
        led.value(0)
        pwm.duty(duty)
        time.sleep_ms(STEP_MS)
        pwm.duty(0)
        led.value(1)
        time.sleep_ms(GAP_MS)
finally:
    pwm.duty(0)
    pwm.deinit()
    Pin(25, Pin.OUT, value=0)     # 确保 Q3 截止, 停止发热
    led.value(1)

print("结束。预期: 50%最响、100%无声、10%和90%听不出区别")
