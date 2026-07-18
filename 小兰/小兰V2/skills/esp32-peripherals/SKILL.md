---
name: esp32-peripherals
description: 扩展外设分块。MPU6050 陀螺仪、电机驱动、I2C/SPI/UART 总线、ADC/DAC、触摸、WS2812 等扩展开发时加载。
---

# 扩展外设分块

## MPU6050 六轴 IMU（板载，I²C GPIO16=SDA / GPIO17=SCL）

```python
from machine import I2C, Pin
i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
i2c.scan()   # 应返回 [104](0x68) 或 [105](0x69)
```

板载 10k 上拉（R7/R8）；≤400kHz；上电等 ~100ms 再初始化；3.3V 供电勿接 5V。

## MX620B 电机驱动（板载，GPIO26=IN1 / GPIO27=IN2）

- J6 端子：GND / A1 / A2 / BAT(5V)。GPIO26/27 打 PWM 控转速与方向
- GPIO26 同时是 DAC2；ADC2_CH7=GPIO27 在 Wi-Fi 下不可用

## 总线映射（本板推荐组合）

| 总线 | 推荐引脚 | 说明 |
|---|---|---|
| VSPI(SPI3) | SCLK=18, MISO=19, MOSI=23, CS=5 | 全在 J4，无 Strapping 冲突，接 TFT/SD 卡首选 |
| HSPI(SPI2) | SCLK=14, MISO=19, MOSI=23, CS=5 | 避开 12/15 Strapping 的组合 |
| I²C0 | SCL=22, SDA=21（或 17/16 板载 MPU6050） | 外部设备与 MPU6050 分总线挂 |
| UART2 | TX=5, RX=18（重映射） | 默认脚被 MPU6050 占用；UART1 不可用（在 Flash 上）|
| SD 卡 | 仅 SPI 模式，用 VSPI + `machine.SDCard` | SDIO 模式不可用（GPIO6~11 被 Flash 占） |

## ADC（12-bit）

- Wi-Fi 下只能用 **ADC1**：GPIO32/33/34/35
- `adc.atten(ADC.ATTN_11DB)` → 0~3.3V 量程；线性区约 0.2~3.1V，需软件校准

```python
from machine import ADC, Pin
adc = ADC(Pin(34)); adc.atten(ADC.ATTN_11DB); adc.width(ADC.WIDTH_12BIT)
voltage = adc.read() * 3.3 / 4095
```

## DAC（8-bit，GPIO25/26）

```python
from machine import DAC, Pin
dac = DAC(Pin(25)); dac.write(128)   # ≈1.65V (0~255)
```

**GPIO25 做 DAC 前必拔 J11 跳线**（否则蜂鸣器跟着响）。

## 电容触摸

最佳通道（无 Strapping、板上负载轻）：GPIO4(T0)、13(T4)、14(T6)、27(T7)。
读数约 0~1024，触摸后从 ~800-1000 降到 ~200-500，需按板校准；本板无板载焊盘，排针外接 ≥10×10mm 铜箔。

## WS2812 / NeoPixel

```python
import machine, neopixel
np = neopixel.NeoPixel(machine.Pin(21), 8); np[0] = (255, 0, 0); np.write()
```

用 J4/J5 排针任意可用 GPIO（如 5/13/14/18/21），避开 Strapping 引脚。

## 通用原则

外接任何设备必须**共地**；PWM(LEDC) 与中断所有输出脚都支持；舵机 50Hz `duty(77)`≈1.5ms 中位。
