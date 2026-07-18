---
name: esp32-mcu
description: 单片机分区。芯片/电源/Flash/串口 REPL/启动顺序/Strapping 约束/深度睡眠/驱动能力等芯片级问题时加载。与 esp32-pinmap 有部分重叠。
---

# 单片机分区（ESP32-D0WD 芯片级）

## 核心配置

- ESP32-D0WD-V3，双核 Xtensa LX6 @240MHz，40MHz 晶振
- Flash：ZB25VQ32 4MB（固件 ~1.5MB + 用户文件系统 ~2.5MB）；
  占用 GPIO6~11，**用户绝对不可用**
- USB 串口：CP2102N，`/dev/ttyACM0`，115200-8-N-1；DTR/RTS 自动下载电路
  （esptool 烧录属安全红线，agent 禁用）
- 电源：USB 5V → F1保险丝 → D1 → BAT → 两片 AMS1085（+5V 和 VCC 3.3V）

## 启动（Strapping）约束 —— 与引脚分区重叠，此处是权威解释

| 引脚 | 启动要求 | 违反后果 |
|---|---|---|
| GPIO12 (MTDI) | 必须**低** | Flash 电压误判 3.3V→1.8V，无法启动 |
| GPIO15 (MTDO) | 必须**高**（片内上拉） | 启动日志静默（运行不受影响） |
| GPIO0 | 高=正常运行，低=下载模式 | 复位时若被拉低进下载模式 |
| GPIO2 | 需浮空或低 | 配合 GPIO0 影响下载模式 |

## MicroPython 启动顺序与 REPL

1. 上电 → `boot.py` → `main.py` → REPL
2. REPL 占用 UART0(GPIO1/3)；`uos.dupterm(None, 1)` 可释放（慎用，会失去 REPL）
3. `main.py` 开头建议 `time.sleep(0.5)` 等外设稳定
4. 死循环主程序会占住 REPL：调试时用超时 + 软复位打断

## 深度睡眠与唤醒

功耗 ~5-10µA。RAM 全丢，唤醒=从头执行，用 `machine.reset_cause()` 区分冷启动。

```python
import machine, esp32
esp32.wake_on_ext0(pin=machine.Pin(35), level=esp32.WAKEUP_ALL_LOW)  # KEY1 唤醒
machine.deepsleep(10000)          # 或定时 10s 唤醒
if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    print("从深度睡眠唤醒")
```

本板可用 RTC GPIO：0,2,4,12,13,14,15,25,26,27,32,33,34,35。

## 内存与 GC

- 合成/处理大缓存前后 `gc.collect()`，`gc.mem_free()` 查余量
- 中断 ISR 内禁止分配内存（只设全局标志位）

## GPIO 电气能力

- 单脚：吸入 28mA / 输出 40mA / **长期建议 12mA**
- VDD3P3_RTC 域（GPIO0,2,4,12~15,25~27,32~39）与 CPU 域（1,3,5,16~23）各 40mA 总限
- Wi-Fi 开启 → ADC2 全废、DAC2 有噪声；蓝牙同理
