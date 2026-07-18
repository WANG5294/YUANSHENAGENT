---
name: esp32-piano-debug
description: 调试 ESP32-D0WD 数字钢琴（RMT PWM-DAC 音频）。涉及上传/运行
  MicroPython、无声/爆音/哒哒音排查、音色缓存管理、麦克风闭环验证实机声音
  时使用。
---

# ESP32 数字钢琴调试

## 硬件速记（详见 references/）

- 串口 `/dev/ttyACM0`（CP2102N），权限不够先 `sg dialout`
- KEY1 = GPIO35、KEY2 = GPIO34，**输入专用脚**，板载 1k 上拉，按下 = 低
  电平，**勿设 PULL_UP**。注意：现有 py 代码（KEY.py 等）用 `Pin(34)` 且
  注释写"KEY1"，那是修正前的旧命名——实际响应的是丝印 KEY2 按键，py 代码
  保持不动，以引脚号为准。
- LED2 = GPIO32（绿）、LED3 = GPIO33（红），**低电平点亮**
- 音频输出 GPIO25 → J11 跳线 → R13 → Q3(NPN) → 负载
- 引脚全表 → [references/ESP32接口速查.md](references/ESP32接口速查.md)
- 喇叭能接什么、不能接什么 → [references/扬声器硬件限制.md](references/扬声器硬件限制.md)

## 标准调试流程

1. **先主机后上板**：改波形算法先用 scripts/ 或 gen_*.py 生成
   `_preview.wav`，`analyze_wav` 看指标、`aplay` 试听，没问题再上板。
2. **上板无声** → 依次查：J11 跳线是否插着；`CACHE_VERSION` 改了但板上
   陈旧 `.bin/.json` 没删（`device_rm`）；GPIO25 是否被别的外设占用。
3. **爆音（开头/结尾"啪"）** → 检查首尾是否有 ~10ms 直流斜坡
   （占空比 0↔CENTER 线性过渡）。
4. **哒哒音（播放中周期性咔声）** → 本质是 RMT 分块间 35µs 空隙的
   电荷亏空，与音量无关。周期波形必须 `write_pulses(..., loop=True)`
   硬件循环；非周期波形（有包络）分块流水 + 块尾高电平 +233tick 电荷
   补偿。详见项目根目录 `RMT音频哒哒音问题说明.md`。
5. **实机闭环验证** → 用麦克风录下喇叭真实声音与预览对比，见
   [references/麦克风闭环调试.md](references/麦克风闭环调试.md)。

## Agent 操作要点

- 板上主程序通常是 `while True` 等按键，`mpremote run` **必须带超时**，
  超时后软复位。
- KEY1 是物理按键，agent 按不到。要闭环测试，播放逻辑必须封装成
  可 import 的函数（如 `piano.py` 里的 `play()`），用
  `play_and_record("import piano; piano.play()", "rec.wav", 4)` 触发。
- 合成大缓存时 LED2 亮属正常（可能几十秒），别急着判卡死。
- 内存紧张：合成前后 `gc.collect()`，用 `repl_exec` 查 `gc.mem_free()`。
