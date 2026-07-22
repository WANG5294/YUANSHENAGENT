# Yuanshen v3 —— ESP32 单片机开发 Agent 设计文档

> Yuanshen v3 基于小兰 v2 演进，核心变化在 **prompt 架构**：
> ① system prompt 内置工具功能精简总览与当前接线事实；
> ② 输入栏分流——硬件说明文档与用户任务分开输入；
> ③ 新硬件说明以 skill 格式接入，换硬件不改主程序。
> 名称由"小兰"改为"Yuanshen"。

---

## 一、整体流程

```
启动
 ├─ 读 .env（本目录 → 小兰V0/.env 兜底），apply_model
 ├─ 加载 skills/（含硬件文档技能）
 ├─ 读 wiring.md → 注入 system prompt【当前接线】
 ├─ 启动 MCP 服务器（esp32-piano，12 工具）
 └─ 进入 REPL，等待输入
        │
        ▼ 输入分流（见 §四）
 ┌──────────────┬───────────────────┬────────────────┐
 │ 斜杠命令       │ 文档导入 /doc      │ 其余 = 任务目标  │
 │ 本地处理，不进  │ 校验 skill 格式 →  │ 开任务文件夹 →   │
 │ 大模型         │ 装入 skills/ 即时  │ 初始化主线任务 →  │
 │               │ 生效              │ 进入 agent 循环  │
 └──────────────┴───────────────────┴────────────────┘
        │
        ▼ agent 循环（每个任务）
 LLM → tool_use → 执行工具 → tool_result + 【循环状态】回灌 → LLM …
 每轮终端输出：循环摘要一行 + `└ 第k轮调用: [MCP]xxx✓，[本地]yyy✓`
 主线四步：编写代码 → 烧录代码(=部署为板上 main.py，覆盖前自动备份)
          → 测试代码(实机验证红线) → 完成
        │
        ▼ 任务结束
 完整汇报 → "⏳ 正在保存记录请勿关闭" → 归档到 files/<时间戳_摘要>/
 → 经验提取 → 用户确认(y 保存 / n→可选保留上下文继续对话修改)
 → "✅ 记录已保存" → 等待下一条输入
```

---

## 二、三层 Prompt 架构（v3 的核心）

| 层 | 位置 | 内容 | 特点 |
|---|---|---|---|
| **System prompt** | 请求的 `system` 字段 | 身份与工作范围、循环摘要格式、主线任务规则、**工具功能精简总览**、**【当前接线】**（wiring.md）、技能列表（仅 name+description）、实机验证红线、安全红线 | 每轮全量重发，只放"每个任务都用得上"的规则与小事实 |
| **Tool prompt** | `tools` 参数每个工具的 description + input_schema | 工具**完整**用法：参数含义、示例、注意事项 | 模型据此决定何时调用、怎么传参；system 里只留其精简版 |
| **Skill 按需注入** | Skill 工具的 tool_result | 大块知识正文：硬件分块文档、经验教训 | 平时不占上下文，任务匹配时才注入 |

**放置原则**：变化慢/体积大/按需用的知识 → Skill；变化快/体积小/全局相关的事实 → system prompt；工具用法 → tool prompt（system 只留一行一个的总览）。

### system prompt 中的工具精简总览（示例节选）

```
【工具总览】详细参数见工具定义，此处只提示能力边界：
- 本地：bash / read_file / write_file / edit_file（文件自动落任务文件夹）
        Skill(按需加载知识) / TodoWrite(主线进度)
- MCP·设备：list_ports / upload(烧录=传为main.py) / run_script(带超时)
        repl_exec / device_ls / device_rm / soft_reset
- MCP·音频闭环：mic_check / record_audio / play_and_record
        analyze_wav / compare_audio
```

---

## 三、Skill 格式规范（硬件文档必须遵守）

每个技能一个目录：`skills/<name>/SKILL.md`，结构：

```markdown
---
name: esp32-led                  # 必填，kebab-case 小写短横线
description: LED 灯分块。点灯、闪烁、呼吸灯时加载。LED2=GPIO32 绿…
                                  # 必填，一句话说清"什么任务该加载我"
---

# 正文（Markdown，按需注入，不常驻上下文）

电路、引脚、代码模板、注意事项……
```

规则：
1. frontmatter 的 `name`、`description` 缺一不可，缺失则拒绝装载；
2. `description` 是模型决定是否加载的唯一依据，必须写"何时加载"；
3. 分块原则：**功能独立分块**（蜂鸣器与 LED 分开），允许**有意重叠**
   （引脚总表与蜂鸣器分块都写 GPIO25，各自视角不同）；
4. `exp-` 前缀保留给任务经验提取（须经用户确认才入库）；
5. 新硬件说明文档（.md）按本格式写好后，用 `/doc <路径>` 导入即可，
   主程序零修改。

当前技能清单（v2 继承）：
`esp32-pinmap` `esp32-buzzer` `esp32-led` `esp32-keys` `esp32-mcu`
`esp32-peripherals` `mic-closed-loop`

---

## 四、用户输入（输入栏分流）

| 输入形式 | 含义 | 处理 |
|---|---|---|
| 普通文本 | **任务目标**。只写要达成什么（如"按key1播放do音"），不写"请编写/烧录/运行"——主线流程在 system prompt 里 | 开任务文件夹 → 主线四步 → 归档 |
| `/doc <md路径>` | **导入硬件说明文档**（与任务输入分离的通道） | 校验 skill 格式 → 复制到 skills/<name>/ → 立即生效并回显 |
| `/wiring` | 查看/编辑**当前接线**（wiring.md） | 修改后下个任务的 system prompt 即更新 |
| `/model` | 切换大模型；缺 Key 给保存指引 | 本地处理 |
| `/tool` | 列出工具（`[本地]`/`[MCP]` 标注 + 功能一行） | 本地处理 |
| `/skill` | 列出技能（名称 + description） | 本地处理 |
| `/work` | 探测环境能力（串口/板子/麦克风/技能/API） | 本地处理 |
| 任务结束后的 `y`/`n` | 经验保存确认；`n` 后可选保留上下文继续多轮对话修改 | 本地交互 |

### wiring.md（接线事实，常驻 system prompt）

```markdown
# 当前接线
- 板子：ESP32-D0WD 开发板，USB → /dev/ttyACM0
- J11 跳线：已插（GPIO25 → 蜂鸣器）
- 外接：无（排针全部空置）
- 备注：GPIO12/15 排针未接任何上下拉（保持可启动）
```

用户换接线后更新此文件；十几行的常驻成本可忽略，但能防住
"GPIO12 外接上拉导致无法启动"这类事故。

---

## 五、MCP 格式

**传输**：本地子进程 stdio，换行分隔的 JSON-RPC 2.0。

**握手与调用**：
```
→ initialize {protocolVersion, capabilities, clientInfo}
→ notifications/initialized
→ tools/list                     ← {tools:[{name, description, inputSchema}]}
→ tools/call {name, arguments}   ← {content:[{type:"text", text}], isError}
```

**服务器侧**（`piano_workflow/esp32_piano_mcp.py`）：FastMCP 注册，
**函数 docstring 即 tool prompt**——写新工具时 docstring 必须说清参数与
何时用。工具分两组：

| 组 | 工具 | 说明 |
|---|---|---|
| 设备通道 | list_ports / upload / run_script / repl_exec / device_ls / device_rm / soft_reset | 全走 mpremote；run_script 超时自动软复位 |
| 音频闭环 | mic_check / record_audio / play_and_record / analyze_wav / compare_audio | mic_check 三档判定（通道未开启/疑似静音/正常）；分析纯 numpy |

**客户端侧**：最小标准客户端（后台线程读 stdout 入队列），MCP 工具与
本地工具对模型完全同构；`upload` 目标为 main.py 时由主程序拦截：
先自动备份板上原 main.py 到 backups/，成功后置 deployed_main 卡点标志。

---

## 六、继承自 v2 的机制（v3 不变）

- **循环摘要**：每轮回复第一段 ≤100 字，格式
  "第k+1轮循环输出结果：完成第k轮循环，成功/失败；第k轮使用了〈技能〉skill、〈工具名（mcp/本地）〉tool，做了〈概括〉。正在进行第k+1轮循环，第N秒。"
  轮次/成败/秒数由程序注入的【循环状态】提供，模型照抄；
  Skill 只报名称，严禁复述正文。
- **终端输出结构**：中间轮只显示摘要行 + `└ 第k轮调用: [MCP]…✓`；
  最终轮完整汇报；随后"⏳ 保存中勿关"→"✅ 已保存"。
- **主线任务 TodoWrite**：四步不可删；"烧录代码"未部署 main.py 不允许
  标记完成（程序级卡点）。
- **实机验证红线**：录音峰值 ≥5×噪声底否则闭环失败；响度/包络类必须
  preview + compare_audio 相关系数 ≥0.8；汇报必须引用数字；
  严禁静态检查替代实机验证。
- **文件组织**：`files/<时间戳_任务摘要>/` 每任务一个项目文件夹，
  产出（py/wav，纯文件名自动落位）+ 流程.md + transcript.json +
  经验提取.md 同放。
- **经验提取确认**：候选经验展示全文 → 用户 y/n → 不确认可保留上下文
  继续多轮对话修改；无人值守默认不保存。
- **安全红线**：禁 esptool/erase_flash、sudo 等危险命令；文件操作限
  工作目录；串口限 /dev/ttyACM*、/dev/ttyUSB*；GPIO34/35 禁配输出。

---

## 七、目录结构

```
YuanshenV3/
├── Yuanshen_v3.py      # 主程序
├── readme_v3.md        # 本文档
├── .env.example        # 多平台 API Key 模板
├── wiring.md           # 当前接线（常驻 system prompt）
├── skills/             # 技能分块（硬件文档 + exp- 经验，经用户审查后装入）
├── files/              # 每任务一个项目文件夹（产出+日志+报告）
└── backups/            # 板上原 main.py 自动备份（运行时在工作目录生成）
```

依赖的外部组件（不在本目录内）：
- `../piano_workflow/esp32_piano_mcp.py` —— MCP 服务器（12 个工具）
- `../piano_workflow/.venv` —— Python 虚拟环境（anthropic/mcp/numpy）
- `../小兰/小兰V0/.env` —— 已存的 API Key（自动兜底读取）

---

## 八、安装与运行

### 8.1 环境依赖

| 依赖 | 说明 | 安装 |
|---|---|---|
| Python 3.10+ | 主程序与 MCP 服务器 | 系统自带 |
| anthropic / python-dotenv / mcp / numpy | 已装在 `piano_workflow/.venv`，主程序缺依赖时自动 re-exec 切换过去 | `piano_workflow/.venv/bin/pip install anthropic python-dotenv mcp numpy` |
| mpremote | 与 ESP32 通信 | `pip install mpremote`（用户须在 dialout 组） |
| arecord (alsa-utils) | 麦克风闭环录音 | `sudo apt install alsa-utils`；VirtualBox 须勾选 设备→音频→音频输入 |

### 8.2 配置 API Key

```bash
cd Yuanshen
cp .env.example .env
nano .env        # 填入 MOONSHOT_API_KEY（或 DEEPSEEK/ZHIPU 的 Key）
```

已在 `小兰/小兰V0/.env` 存过 Key 的会自动沿用，可跳过本步。

### 8.3 启动与日常使用

```bash
cd /home/vboxuser/YUANSHENAGENT     # 在项目根目录启动（工作目录）
python3 Yuanshen/Yuanshen_v3.py
```

启动后直接输入任务目标即可（如"按key1播放do音"）。斜杠命令速查：

| 命令 | 作用 |
|---|---|
| `/model` | 切换大模型（缺 Key 时给保存指引） |
| `/tool` | 列出工具（[本地]/[MCP] 标注） |
| `/skill` | 列出技能 |
| `/work` | 探测环境能力（串口/板子/麦克风/API） |
| `/wiring` | 查看当前接线（编辑 wiring.md 生效） |
| `/doc <md路径>` | 导入新硬件说明文档（须符合 §三 skill 格式） |
| `exit` | 退出 |

### 8.4 接入新硬件的标准动作

1. 把新硬件说明写成符合 §三 格式的 md（可拆多个分块，一块一个文件）；
2. 逐个 `/doc 路径.md` 导入；
3. 更新 `wiring.md` 写明实际接线；
4. 直接下达任务目标——不需要改主程序任何代码。

---

## 九、与大作业要求的对应（任务书 5.2）

| 任务书要求的基本能力 | Yuanshen v3 的实现 |
|---|---|
| 1 文件传输 | MCP `upload`（目标 main.py 时自动备份原程序） |
| 2 程序执行 | MCP `run_script` / `repl_exec`（软件触发，带超时） |
| 3 微控制器复位 | MCP `soft_reset` |
| 4 串口监控 | `run_script` / `repl_exec` 捕获全部串口输出 |
| 5 运行日志检索 | files/<任务>/流程.md + transcript.json 全量归档 |
| 6 错误报告 | 工具结果 Error 前缀 + 循环摘要成败上报 + Traceback 回灌模型 |
| 进阶：远程文件管理 | MCP `device_ls` / `device_rm` |
| 进阶：自动化验证（超纲） | 麦克风闭环 `play_and_record`/`analyze_wav`/`compare_audio`，实机验证红线 |
| 闭环迭代（核心交付） | 主线四步强制"硬件验证通过才算完成"；files/ 归档即闭环证据 |
