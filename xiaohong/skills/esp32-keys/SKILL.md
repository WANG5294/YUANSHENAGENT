---
name: esp32-keys
description: 按键分块。读按键、消抖、中断、BOOT/RESET 键行为时加载。KEY1=GPIO35、KEY2=GPIO34，仅输入、板载上拉、按下为低。
---

# 板载按键（4 个轻触开关）

| 丝印 | 位号 | 连接 | 可编程 |
|---|---|---|---|
| KEY1 | K4 | GPIO35 ─ R12(1k上拉至VCC)，按下→GND | ✅ |
| KEY2 | K3 | GPIO34 ─ R9(1k上拉至VCC)，按下→GND | ✅ |
| BOOT | K1 | GPIO0 ─ 按下→GND | ⚠️ 运行时可当输入；启动时按住进下载模式 |
| RESET | K2 | CHIP_PU(EN) ─ 按下→GND | ❌ 硬件复位，不可编程 |

## 关键约束

- GPIO34/35 **仅输入**：无输出能力、无内部上/下拉。`Pin(35, Pin.IN)` 即可，
  设 `PULL_UP` 无效（靠板载 1k 上拉）。**禁止配置为 Pin.OUT**。
- 读值：`0` = 按下，`1` = 释放。
- ⚠️ 历史坑：项目旧代码（KEY.py 等）注释把 GPIO34 写成"KEY1"，是修正前的
  错误命名。以本表为准：**丝印 KEY1 = GPIO35，丝印 KEY2 = GPIO34**。

## MicroPython 用法

```python
from machine import Pin
import time

key1 = Pin(35, Pin.IN)          # 板载 R12 上拉
key2 = Pin(34, Pin.IN)          # 板载 R9 上拉
boot = Pin(0, Pin.IN, Pin.PULL_UP)

# 轮询 + 20ms 消抖
if key1.value() == 0:
    time.sleep_ms(20)
    if key1.value() == 0:
        print("KEY1 按下")

# 中断（ISR 里只设标志位，不分配内存）
flag = False
def on_key(pin):
    global flag
    flag = True
key1.irq(trigger=Pin.IRQ_FALLING, handler=on_key)
```

## Agent 调试提示

- 实体按键 agent 按不到：闭环测试时把按键触发的逻辑封装成可 import 的
  函数，用 `repl_exec` / `mpremote exec` 软件触发。
- GPIO35 是 RTC GPIO，可做 deepsleep EXT0 唤醒源（见 esp32-mcu 技能）。
- 主程序若是 `while True` 等按键，`run_script` 必须带超时，超时软复位。
