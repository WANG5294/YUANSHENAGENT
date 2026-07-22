# yuanshen-esp32-agent（Yuanshen v3）

ESP32 单片机开发 Agent：你输入一句话目标（如"按key1播放do音"），它自动完成
**编写 MicroPython 代码 → 烧录为板上 main.py（原程序自动备份）→ 实机测试
（串口回读 + 麦克风闭环）→ 汇报**，并归档全过程日志。

## 安装（Linux / macOS）

```bash
npm install -g yuanshen-esp32-agent
```

前置：`python3`（含 venv）、ESP32 开发板 USB 连接（用户在 dialout 组：
`sudo usermod -aG dialout $USER` 后重新登录）。首次运行自动创建 Python
虚拟环境并装依赖。

## 配置 API Key（必须）

```bash
cd $(npm root -g)/yuanshen-esp32-agent
cp .env.example .env && nano .env    # 填入 Kimi 或 DeepSeek 的 API Key
```

## 使用

```bash
Yuanshen
```

启动后直接输入任务目标。常用命令：`/model` 切换模型、`/work` 探测环境、
`/wiring` 查看接线（编辑包目录下 wiring.md 记录你的实际接线，支持简写
如 `G05连LED接GND`）、`/doc <md路径>` 导入新硬件说明文档（SKILL.md 格式）、
`/skill` `/tool` 查看能力、`exit` 退出。

详细说明见包内 `请用户先阅读.md` 与 `readme_v3.md`（架构/技能格式/MCP 协议）。

## 说明

- 包内自带 ESP32 MCP 服务器（12 个工具）与 7 个硬件知识技能分块
- 不含任何 API Key；任务产出 files/ 与你的接线 wiring.md 均为本地生成，不在包内
