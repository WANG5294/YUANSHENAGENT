# 自建 Agent 技术方案（对原构想的补充与修正）

> 基于 mini-claude-code(v0–v4) 架构，用标准 MCP + Skill 机制，
> 搭建一个能开发/烧录/验证 ESP32 数字钢琴的 AI 原生 Agent。
> 本文档同时作为第二周"工具链技术方案文档"的底稿。

---

## 1. 总体架构（修正原构想的循环描述）

原构想："tool 的输出加到 user prompt —— 循环"。需要修正为真实的 API 协议流程：

```
messages = [user 消息]
loop:
    response = LLM(system=SYSTEM, messages=messages, tools=TOOLS)
    if response.stop_reason != "tool_use":   # 模型输出纯文本 → 循环结束
        print(text); break
    for each tool_use block in response:      # 一轮可能有多个工具调用
        output = execute_tool(name, input)
    messages += [assistant 消息(含 tool_use 块, 原样保留)]
    messages += [role=user 消息, 内容为 tool_result 块(带 tool_use_id)]
```

要点（mini-claude-code v4 就是这么实现的）：

- 工具结果**不是拼进 user prompt 文本**，而是独立的 `tool_result` 结构块，
  与 assistant 消息里的 `tool_use` 通过 id 配对。
- 循环终止条件是 `stop_reason`：模型想继续调工具就是 `tool_use`，
  说完了就是 `end_turn`。不需要自己定义 "tool-use=1" 标志位。
- 一轮响应可以包含**多个**工具调用，不要限制成每次只能调一个。

## 2. 调用 API：Kimi K3（已核实，满足全部需求）

原构想的 "DeepSeek-V4-pro" 改为 **Kimi K3**（模型 ID `kimi-k3`，
月之暗面旗舰，2.8T 参数，1M token 上下文）。以下事实已于 2026-07
从 Kimi 官方文档（platform.moonshot.cn）逐项核实：

### 需求满足检查

| 需求 | 结论 | 依据 |
|---|---|---|
| 工具调用（agent 的命根子） | ✅ 原生 `tool_calls`，支持并行调用 | 官方文档给出完整 agent loop 示例代码 |
| OpenAI 兼容协议 | ✅ `base_url=https://api.moonshot.cn/v1`，直接用 openai SDK | 官方快速开始 |
| Anthropic 兼容协议 | ✅ `https://api.moonshot.cn/anthropic`（实测无 key 返回 401 而非 404，端点存在） | mini-claude-code 的 `.env.example` 默认就指向这个端点 |
| MCP 集成 | ✅ MCP 是 agent 侧的客户端协议，模型只需会 tool_calls；agent 内嵌 MCP client，把 MCP 工具 schema 翻译成模型工具 schema 即可 | — |
| Skill / 子代理 | ✅ 纯提示词工程 + 同一套 API，与模型无关 | — |
| 长上下文 | ✅ K3 有 1M token（DeepSeek 仅 64–160K），串口长日志无压力 | 官方模型列表 |
| 多模态 | ✅ K3 支持图片/视频输入——原理图/PCB 截图可直接问模型，作业附录 C 对 DeepSeek 的"非多模态"警告不再适用（PDF 仍建议转 MD 放 skill，省 token） | 官方文档 |
| 流式输出 | ✅ stream 模式下 tool_calls 可用 | 官方文档 |

### 两条接入路线

- **路线 A（零代码改动，先跑通）**：mini-claude-code v4 从 `.env` 读
  `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_KEY` / `MODEL_NAME`，其
  `.env.example` 默认就指向 `https://api.moonshot.cn/anthropic`。
  填入 Kimi API Key、`MODEL_NAME=kimi-k3`，v4 原样运行。
  适合第一天先把骨架跑起来验证环境。
- **路线 B（OpenAI 协议，自己 agent 的正式实现）**：用 openai SDK 写
  自己的 agent loop（`finish_reason == "tool_calls"` → 执行工具 →
  追加 role=tool 消息 → 循环）。Kimi 官方工具调用文档给出了逐行的
  循环示例，照抄骨架即可。自己写循环 = 真正理解工具调用机制
  （报告素材），也不依赖第三方兼容层。

建议：A 验证环境 → B 作为正式实现。

### K3 特有的坑（官方文档明示）

- K3 用顶层 `reasoning_effort` 参数（当前仅支持 `"max"`）；各模型
  参数配置有差异，换模型时先查官方"模型参数参考"。
- 带 tool_calls 的 assistant 消息必须**原封不动**追加回 messages，
  且每个 tool_call 都要有 `tool_call_id` 对应的 role=tool 消息，
  否则报 `tool_call_id not found`。
- tools 定义本身也占 token，工具数量多时按需动态注入。

## 3. System Prompt（补充）

原构想："身份+环境+任务+skill+tool"，方向对。补充四条：

- **"完成"的定义要写死**：不是"代码写完"，而是"串口输出无异常 **且**
  音频指标达标（f0 偏差 <10 音分、无哒哒音）"。否则模型会宣布
  "代码已生成，应该能工作"就停手——这正是作业要打破的传声筒模式。
- **硬件事实不放 system prompt，放 skill**。system prompt 保持稳定
  （利于 prompt 缓存，mini-claude-code v4 的 cache-preserving 设计），
  GPIO 表、蜂鸣器限制这些领域知识走 Skill 工具按需注入。
- **循环规则**：优先用工具行动而非空谈；一次只改一个变量；
  每改必上板验证；验证不过就根据日志/音频指标修，不瞎猜。
- **安全红线**（见第 6 节）直接写进 system prompt。

草稿改写示例：

```
你是 ESP32 嵌入式开发 agent，运行在 Ubuntu 24.04 虚拟机中，
通过 MCP 工具与 /dev/ttyACM0 上的 ESP32-D0WD 开发板直接交互。
工作循环：理解需求 → 编写/修改 MicroPython 代码 → 上传 → 运行
→ 读串口输出与音频分析指标 → 有问题则修复 → 重新部署，直到
硬件验证通过。只有硬件验证通过才算完成，代码生成不算完成。
涉及 ESP32 引脚/音频/调试知识时，先调用 Skill 工具加载对应技能。
```

## 4. 工具体系：MCP（修正概念）+ 基础工具

原构想："本地MCP文件+云端MCP文件"。修正：

- **MCP server 不是"文件"，是一个进程**（stdio）或 HTTP 服务，
  通过 JSON-RPC 暴露工具列表。你的 `esp32_piano_mcp.py` 已经是一个
  标准 FastMCP server，12 个工具，这就是作业附录 B 推荐的 ★★★★★ 方案。
- 自建 agent 要**内嵌 MCP client**（mcp SDK 的 `ClientSession` +
  `stdio_client`）：启动时连接 server → `list_tools()` 拿到工具定义
  → 动态注册进 agent 工具表 → 模型调用时转发给 server，结果包成
  tool_result 返回。这样 MCP 工具和 bash/read/write 对模型完全同构。
- **"云端 MCP" 砍掉**。本作业用不上，徒增复杂度。KISS。
- 加分点：同一个 `esp32_piano_mcp.py` 既能接你的自建 agent，也能
  `claude mcp add` 挂到 Claude Code / Kimi CLI——一次实现两个宿主，
  最终演示和报告里可以做对比，证明你用的是"标准 MCP"而非私有协议。

Agent 工具表最终形态：

| 类别 | 工具 | 来源 |
|---|---|---|
| 基础 | bash / read_file / write_file / edit_file | mini-claude-code 自带 |
| 任务管理 | TodoWrite | v2 |
| 知识 | Skill | v4 |
| 子代理 | Task | v3 |
| 硬件 | upload / run_script / repl_exec / soft_reset / device_ls / device_rm / list_ports | MCP server |
| 音频闭环 | mic_check / record_audio / play_and_record / analyze_wav / compare_audio | MCP server |

（"python3" 不必单列工具，bash 已覆盖；"micropython" 就是 MCP 的
upload/run/repl 三个工具。）

## 5. 检测运行效果（原构想最大的修正点）

原构想："子代理用某种神奇的 API 把音频转成 ASCII，同时执行两个子代理"。
两个修正：

### 5.1 不需要"神奇 API"——你已经有更好的

`esp32_piano_mcp.py` 里的 `analyze_wav` 用纯 numpy 在**本地**把录音变成
结构化文本指标：基频 f0、与期望频率的音分偏差、谐波分布、包络形态、
哒哒音检测（还能推算分块周期）。对 LLM 来说，**数字指标远比 ASCII
波形图有用**——模型能直接推理"f0=277Hz vs 期望 261.6Hz，偏差 +100
音分 = 高了半音，频率表错了"，但看不懂一屏 ASCII 字符画。

本地分析 vs 云 API：免费、确定性、可复现、不依赖外部服务可用性；
语音 ASR 类 API 是为人声设计的，对单音方波测频反而不如 FFT 准。

**建议增强（差异化亮点）**：音符序列识别——按包络把录音切成单个音符，
逐音符报 f0 和音分偏差，输出"第 3 音应为 sol(392Hz) 实测 415Hz，
偏差 +100 音分"。这样 agent 能自动验证整首曲子，闭环演示效果拉满。

### 5.2 不需要两个子代理并行

录音和播放的并行**已经在 `play_and_record` 工具内部做了**：先起
arecord 进程，0.5s 后通过 REPL 触发播放，进程内并行，时序精确可控。
如果改成"子代理 A 管 MCP 触发、子代理 B 管录音"，两个 LLM 子代理的
调度延迟不可控，很可能录音还没起来播放就结束了，漏掉起振瞬间。

子代理（v3 的 Task）的正确用途是**上下文隔离**：让子代理去读大段
串口日志 / 长文件 / 搜索代码，只把结论带回主上下文，主 agent 的
上下文窗口不被污染。

## 6. 安全限制 + TodoList（具体化）

mini-claude-code 已有的：`safe_path`（文件操作限制在工作目录内）、
bash 简单黑名单。在此基础上补全：

- **命令黑名单**：`rm -rf /`、`sudo`、`shutdown`、`mkfs`、`dd of=/dev/*`、
  `esptool erase_flash`（误擦固件要重烧，演示时灾难）
- **设备白名单**：串口操作只允许 `/dev/ttyACM*` / `/dev/ttyUSB*`
- **循环护栏**：单任务最大工具调用轮数（如 30 轮，防死循环烧 API 额度）；
  所有 mpremote 调用**强制超时**（板上主程序是 `while True`，不超时必挂死，
  超时后自动软复位——你的 run_script 已经这么做了）
- **危险操作人工确认**（可选）：`device_rm` 删板上文件前打印确认
- **TodoList**：用 v2 的 TodoManager，约束"同时只能一个 in_progress"，
  多步骤任务（写代码→上传→验证→修复）强制模型先列计划，
  演示视频里 todo 列表的变化也是很好的可视化素材。

## 7. 对照作业基本要求的覆盖检查

作业 5.2 的 6 项基本能力 → 工具映射（报告里直接用这个表）：

| 作业要求 | 实现 | 状态 |
|---|---|---|
| 1 文件传输 | `upload`（mpremote cp） | ✅ 已有 |
| 2 程序执行 | `run_script` / `repl_exec` | ✅ 已有 |
| 3 微控制器复位 | `soft_reset` | ✅ 已有 |
| 4 串口监控 | run/repl 输出捕获；建议补一个持续监听读缓冲工具 | ⚠️ 基本有 |
| 5 运行日志检索 | 串口输出落盘成日志文件 + read_file 检索 | ⚠️ 要补落盘 |
| 6 错误报告 | **MicroPython Traceback 结构化解析**（提取文件名/行号/异常类型，regex 几行的事） | ❌ 要新写 |

进阶功能（至少一项）：你已有远程文件管理（device_ls/device_rm）+
GPIO 状态在线查询（repl_exec 读 Pin）+ 音频闭环验证（超出作业清单的
独有项），绰绰有余。

## 8. 闭环验证演示剧本（核心交付，占工具链分数大头）

作业规定：没有闭环演示，工具链单项得分 ≤40%。建议剧本：

1. 在钢琴代码里埋一个**真实但串口发现不了的 bug**：音符频率表整体
   错半音（或蜂鸣器 GPIO 写成 26）。
2. Agent：upload → run → 串口输出"正常"（bug 不触发异常）。
3. Agent 按 skill 里的闭环流程调 `play_and_record` 录音 →
   `analyze_wav` 报"f0 偏差 +100 音分"（或录音全零=无声）。
4. Agent 定位到频率表/引脚定义 → edit_file 修复 → 重新 upload/run。
5. 再次录音验证：f0 偏差 <10 音分 → 宣布修复完成。

卖点：**纯串口日志永远发现不了"音不准"，只有"耳朵"能**——
这是你的方案超出作业基本要求（只要求串口错误闭环）的差异化亮点，
报告和演示里重点讲。

## 9. 落地路线（对齐作业里程碑）

- **第 2 周（本周）**：定稿本方案；agent 骨架 = fork v4_skills_agent.py，
  先用路线 A（.env 指向 Kimi anthropic 端点 + `kimi-k3`）零改动跑通，
  再用路线 B（openai SDK + `https://api.moonshot.cn/v1`）写自己的
  agent loop；内嵌 MCP client 接通 esp32_piano_mcp.py。
- **第 3 周**：补齐 6 项能力（Traceback 解析器、日志落盘）；每个工具
  独立测试；agent 端到端跑通"写 blink.py → 上板 → 验证"。
- **第 4 周**：音符序列识别增强；按第 8 节剧本录闭环演示。
- **第 5 周**：仓库按作业 8.3 结构整理（firmware/ + toolchain/ +
  hardware/ + docs/ + tests/），agent 代码和 MCP server 都放 toolchain/。

杂项：API key 放 `.env` 并加进 .gitignore；串口输出截断（mini-claude-code
截 50000 字符）防上下文爆炸；长会话的历史压缩作业不要求，但报告里
可以作为"已知局限与改进方向"讨论。
