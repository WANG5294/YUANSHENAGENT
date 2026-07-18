---
name: esp32-led
description: LED 灯分块。点灯、闪烁、呼吸灯、状态指示时加载。LED2=GPIO32 绿、LED3=GPIO33 红，均低电平点亮。
---

# 板载 LED（GPIO32 / GPIO33）

## 电路（共阳接法）

```
VCC ── LED2(绿) ── R10 ── GPIO32
VCC ── LED3(红) ── R11 ── GPIO33
VCC ── R3 ── LED1(红,电源指示) ── GND   ← 不可编程，常亮
```

- **低电平点亮**：`value(0)`=亮，`value(1)`=灭；高阻态也是灭
- 板上限流电阻已选好，GPIO 吸入电流在安全范围，无需外加限流

## MicroPython 用法

```python
from machine import Pin, PWM
led_green = Pin(32, Pin.OUT, value=1)   # 初始灭（注意 value=1）
led_red   = Pin(33, Pin.OUT, value=1)
led_green.value(0)                      # 点亮

# 呼吸灯：低电平有效 → 占空比逻辑反转
led = PWM(Pin(32), freq=1000, duty=1023)  # duty=1023 全高 = 常灭
led.duty(0)                                # duty=0 全低 = 最亮
# 亮度 = 1023 - 期望亮度值
```

## 注意

- 初始化务必 `value=1`，否则上电瞬间 LED 会闪一下
- GPIO32/33 同时是 ADC1_CH4/CH5 和触摸通道 T9/T8，复用需先释放 LED 功能
- 更多 LED 走 J4/J5 排针外接：LED+限流电阻（(3.3-Vf)/12mA 估算），共地
