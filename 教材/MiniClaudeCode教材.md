# Mini Claude Code 教程：从零构建你自己的 AI 编码智能体

**副标题：五个版本、约 1100 行代码，拆解 Claude Code / Cursor / Kode 的全部秘密**

> 本教材基于 mini-claude-code 开源工程（v0–v4 五个渐进版本 + 配套文档）编写。
> 每一章对应一个版本，只引入一个新概念；每章末尾附习题与参考答案。
> 建议边读边跑代码：`pip install anthropic python-dotenv`，配好 `.env` 即可运行任意版本。

---

## 目录

- 第 1 章 导论：智能体没有秘密
- 第 2 章 v0：Bash 就是一切（~50 行）
- 第 3 章 v1：模型即代理（~200 行）
- 第 4 章 v2：结构化规划——TodoWrite（~300 行）
- 第 5 章 v3：子代理机制——分而治之（~450 行）
- 第 6 章 v4：Skills 机制——知识外化（~550 行）
- 第 7 章 上下文缓存经济学：别让你的 Agent 烧钱
- 第 8 章 总结与进阶：从玩具到产品的距离

---

# 第 1 章 导论：智能体没有秘密

## 1.1 学习目标

1. 写出所有编码智能体共享的核心循环（≤6 行伪代码）；
2. 说出五个版本各自新增的概念与核心洞察；
3. 搭好运行环境并跑通第一个版本。

## 1.2 核心模式：一个循环

Claude Code、Cursor Agent、Codex CLI 的"秘密"是：**没有秘密**。剥去终端美化、进度条、权限系统，剩下的是一个出奇简单的循环：

```python
while True:
    response = model(messages, tools)          # 1. 问模型
    if response.stop_reason != "tool_use":     # 2. 不再调工具 → 完成
        return response.text
    results = execute(response.tool_calls)     # 3. 执行工具
    messages.append(results)                   # 4. 结果进历史，继续
```

**就这样。模型持续调用工具直到完成。其他一切都是精化（refinement）。**

传统助手与智能体的区别一图看清：

```
传统助手：  用户 → 模型 → 文本回答
智能体：    用户 → 模型 → [工具 → 结果]* → 回答
                        ↑___________|
```

星号（*）是全部要害：模型**反复**调用工具，直到它自己判断任务完成。决策者是模型——代码只提供工具、跑这个循环。

## 1.3 五个版本的路线图

| 版本 | 行数 | 新增内容 | 核心洞察 |
|------|------|----------|----------|
| v0 | ~50 | 1 个 bash 工具 | Bash 就是一切 |
| v1 | ~200 | 4 个核心工具 | 模型即代理 |
| v2 | ~300 | Todo 追踪 | 显式规划 |
| v3 | ~450 | 子代理 | 分而治之 |
| v4 | ~550 | Skills | 按需领域专业知识 |

教学法：**每个版本只添加一个概念**。学完 v4，你对任何商业编码智能体的架构都不再有神秘感。

## 1.4 环境准备

```bash
pip install anthropic python-dotenv
cp .env.example .env      # 填入 ANTHROPIC_API_KEY（可选 BASE_URL、MODEL_NAME）
python v0_bash_agent.py   # 跑通第一个版本
```

三个环境变量：`ANTHROPIC_API_KEY`（必填）、`ANTHROPIC_BASE_URL`（用兼容网关时填）、`MODEL_NAME`（默认 claude-sonnet-4）。

## 1.5 习题

**一、选择题**

1. 智能体核心循环的终止条件是？
   A. 循环 100 次  B. stop_reason 不再是 "tool_use"  C. 用户按 Ctrl+C  D. 内存耗尽

2. 在这个架构中，"决定调用哪个工具、什么顺序、何时停止"的是？
   A. 循环代码  B. 用户  C. 模型  D. 操作系统

**二、简答题**

3. 默写核心循环伪代码（4–6 行），并标注哪一行体现"模型即决策者"。

4. "其他一切都是精化"——结合五版本路线图，说说 v2、v3、v4 各"精化"了什么问题。

**三、参考答案**

1. **B**。模型回复中不含工具调用时循环结束。
2. **C**。代码只提供工具和循环，一切决策由模型做出。
3. 见 1.2 节代码。第 1 行 `response = model(messages, tools)` 与第 2 行的判断体现决策权在模型：调不调工具、调什么，都由模型输出决定。
4. v2 精化"计划不可见导致跑偏"（加 TodoWrite 让计划显式化）；v3 精化"探索细节污染主上下文"（子代理隔离上下文）；v4 精化"模型缺少领域操作知识"（SKILL.md 按需注入专业知识）。

---

# 第 2 章 v0：Bash 就是一切（~50 行）

## 2.1 学习目标

1. 论证"一个工具（bash）+ 一个循环 = 完整智能体能力"；
2. 解释 bash 递归自调用如何实现子代理；
3. 读懂 v0 全部代码，包括 16 行极限压缩版的每一处技巧。

## 2.2 为什么 Bash 就够了

Unix 哲学：一切皆文件，一切可管道。Bash 是通往这个世界的大门：

| 需求 | Bash 命令 |
|------|-----------|
| 读文件 | cat、head、tail、grep |
| 写文件 | `echo '...' > file`、`cat << 'EOF' > file` |
| 搜索 | find、grep、rg、ls |
| 执行 | python、npm、make、任何命令 |
| **子代理** | `python v0_bash_agent.py "任务"` |

最后一行是**关键洞察**：通过 bash 调用自身即实现子代理！不需要 Task 工具、不需要 Agent 注册表——**进程派生即递归**。

## 2.3 进程隔离 = 上下文隔离

```
主智能体
  └── bash: python v0_bash_agent.py "分析架构"
        └── 子智能体（独立进程，全新 history=[]）
              ├── bash: find . -name "*.py"
              ├── bash: cat src/main.py
              └── 经 stdout 返回摘要
```

- 子进程有自己的 `history=[]`——父进程的对话它看不见；
- 父进程把子进程的 stdout 当作工具结果——子进程读的 20 个文件不进入父上下文，只有摘要进入；
- 递归调用支持无限嵌套。

这五个字值得背下来：**进程隔离 = 上下文隔离**。它是第 5 章 v3 子代理机制的原始形态。

## 2.4 代码剖析

v0 的三个组成部分：

**（1）唯一的工具定义。** 注意 description 不只是说明，还在**教模型使用模式**（包括如何派生子代理）：

```python
TOOL = [{
    "name": "bash",
    "description": """Execute shell command. Common patterns:
- Read: cat/head/tail, grep/find/rg/ls, wc -l
- Write: echo 'content' > file, sed -i 's/old/new/g' file
- Subagent: python v0_bash_agent.py 'task description' (spawns isolated agent, returns summary)""",
    "input_schema": {"type": "object",
                     "properties": {"command": {"type": "string"}},
                     "required": ["command"]}
}]
```

**（2）系统提示。** 告诉模型它在哪、行为准则、以及**何时该用子代理**：任务要读很多文件（隔离探索）、任务独立自洽、想避免中间细节污染当前对话。

**（3）chat() 函数——完整的循环。** 逐步看：

```python
def chat(prompt, history=None):
    if history is None: history = []
    history.append({"role": "user", "content": prompt})
    while True:
        response = client.messages.create(model=MODEL, system=SYSTEM,
                                          messages=history, tools=TOOL, max_tokens=8000)
        # 把 assistant 回复(文本块+tool_use块)原样存回历史
        content = []
        for block in response.content:
            if hasattr(block, "text"):
                content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content.append({"type": "tool_use", "id": block.id,
                                "name": block.name, "input": block.input})
        history.append({"role": "assistant", "content": content})
        if response.stop_reason != "tool_use":      # 终止条件
            return "".join(b.text for b in response.content if hasattr(b, "text"))
        # 执行每个工具调用，结果以 tool_result 形式作为 user 消息追加
        results = []
        for block in response.content:
            if block.type == "tool_use":
                out = subprocess.run(block.input["command"], shell=True,
                                     capture_output=True, text=True,
                                     timeout=300, cwd=os.getcwd())
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": (out.stdout + out.stderr)[:50000]})
        history.append({"role": "user", "content": results})
```

四个必须注意的细节：

1. **消息协议**：assistant 消息里的 tool_use 块必须原样保存；工具结果以 `tool_result` 块放在**user 角色**消息中，并用 `tool_use_id` 与调用配对——这是 Anthropic API 的硬性格式；
2. **timeout=300**：命令可能挂死，必须设超时；
3. **[:50000] 截断**：命令输出可能是兆级的，直灌上下文会撑爆窗口（呼应"上下文是预算"）；
4. **入口双模式**：有命令行参数 → 子代理模式（执行任务、打印结果、退出）；无参数 → 交互 REPL。**同一份代码既是主代理又是子代理**。

## 2.5 16 行极限压缩版

v0_bash_agent_mini.py 把同样的逻辑压到 16 行，用了海象运算符把"调用+判断"合一：

```python
while (r := C.messages.create(model=M, system=S, messages=h,
                              tools=T, max_tokens=8000)).stop_reason == "tool_use":
    ...
```

教学价值不在炫技，而在证明：**智能体的最小本质真的只有这么多**——一个 API 调用、一个循环条件、一次工具执行、两次 append。

## 2.6 v0 的局限

- 一切靠 bash：写复杂文件内容要与 shell 引号搏斗，容易出错；
- 无安全网：模型让跑什么就跑什么；
- 编辑文件靠 sed，精确修改困难。
这些正是 v1 要解决的问题。

## 2.7 习题

**一、选择题**

1. v0 实现子代理的机制是？
   A. Task 工具  B. 线程池  C. 通过 bash 递归调用自身脚本（进程派生）  D. 不支持子代理

2. 工具结果在消息历史中的角色（role）是？
   A. assistant  B. user（内容为 tool_result 块）  C. system  D. tool

3. 对命令输出做 [:50000] 截断的目的是？
   A. 美观  B. 防止超长输出撑爆上下文窗口  C. 加密  D. 提高命令速度

4. v0 中"父进程只看到子代理的摘要"是因为？
   A. 模型自觉  B. 父进程仅捕获子进程 stdout 作为工具结果，子进程的完整历史在其独立进程内  C. API 过滤  D. 网络限制

**二、简答题**

5. 解释"进程隔离 = 上下文隔离"，并说明系统提示中列出的三种"该用子代理"的场景。

6. v0 的工具 description 里为什么要写常用命令模式和子代理用法？这揭示了工具描述的什么本质？

7. 同一份 v0 代码如何"既是主代理又是子代理"？

**三、实践题**

8. 运行 v0，让它"统计当前目录下所有 .py 文件的总行数"。记录它实际执行的命令序列，并解释每条命令在感知-行动循环中的角色。

**四、参考答案**

1. **C**。2. **B**。3. **B**。4. **B**。
5. 子进程从 history=[] 全新开始，看不到父对话；父进程只把子进程 stdout（最终摘要）计入自己的上下文——操作系统的进程边界天然成为上下文边界。三种场景：①任务要读大量文件（把探索隔离出去）；②任务独立自洽；③想避免中间细节污染当前对话。
6. description 是模型看得到的"使用说明书"：写入常用模式等于给模型现成的行动模板，写入子代理用法等于教会它任务分解。本质：**工具描述是提示工程的一部分**，工具"能做什么"与"模型知道怎么用"是两件事，后者靠 description。
7. 入口处判断 `len(sys.argv) > 1`：带参数运行时执行单个任务并打印结果（被父代理经 bash 调用，即子代理模式）；不带参数进入交互 REPL（主代理模式）。
8. 开放题。典型序列：`find . -name "*.py" | xargs wc -l` 或先 `ls` 再 `wc -l *.py`。感知：ls/find 了解有哪些文件；行动：wc 计算；模型读取结果后汇总作答（推理）。

---

# 第 3 章 v1：模型即代理（~200 行）

## 3.1 学习目标

1. 说明从 1 个工具到 4 个工具的动机；
2. 熟记四工具的分工与各自 input_schema；
3. 逐行理解 agent_loop 与消息协议；
4. 掌握三项基础安全措施：safe_path、危险命令黑名单、超时与截断。

## 3.2 四个基本工具

v0 用 bash 做一切；v1 把最高频的文件操作升级为**专用工具**：

| 工具 | 用途 | 为什么不继续用 bash |
|------|------|---------------------|
| bash | 运行任意命令 | （保留，兜底通道） |
| read_file | 读文件内容 | 免去引号地狱；可加 limit 参数控制行数 |
| write_file | 创建/整体覆盖文件 | 多行内容经 JSON 参数传递，不再与 shell 转义搏斗 |
| edit_file | 精确字符串替换 | 比 sed 可靠：old_text 必须精确匹配，只替换第一处 |

**这 4 个工具覆盖 90% 的编码任务**：探索（bash: find/grep）、理解（read_file）、修改（write_file/edit_file）、执行（bash: python/npm）。

设计准则（与 Claude Code 一致）：**结构化参数替代字符串拼接**——write_file 的 content 是 JSON 字段，模型不需要考虑转义；edit_file 的"精确匹配 + 只改第一处"把误伤面压到最小。

## 3.3 系统提示

```
You are a coding agent at {WORKDIR}.
Loop: think briefly -> use tools -> report results.
Rules:
- Prefer tools over prose. Act, don't just explain.
- Never invent file paths. Use bash ls/find first if unsure.
- Make minimal changes. Don't over-engineer.
- After finishing, summarize what changed.
```

四条规则各针对一种典型失败：只说不做；幻觉路径；过度工程；改完不汇报。**系统提示是对失败模式的预防性编码。**

## 3.4 安全三件套

**（1）safe_path——路径逃逸防护：**

```python
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path
```

resolve() 展开 `../` 等技巧后检查仍在工作区内——模型（或注入攻击）无法读写项目之外的文件。

**（2）危险命令黑名单：**

```python
dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
if any(d in command for d in dangerous):
    return "Error: Dangerous command blocked"
```

朴素但有效的第一道防线（真正的产品还需要权限系统，见第 8 章讨论）。

**（3）超时与截断**：bash 60 秒超时；一切输出截断至 50KB。

## 3.5 agent_loop 剖析

```python
def agent_loop(messages):
    while True:
        response = client.messages.create(model=MODEL, system=SYSTEM,
                                          messages=messages, tools=TOOLS, max_tokens=8000)
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        # （同时打印文本块，给用户看思考过程）
        if response.stop_reason != "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            return messages
        results = [{"type": "tool_result", "tool_use_id": tc.id,
                    "content": execute_tool(tc.name, tc.input)} for tc in tool_calls]
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": results})
```

要点：

1. **先存 assistant 消息再存结果**，维持 user/assistant 交替的合法序列；
2. execute_tool 是**分发器**：按工具名路由到具体实现，返回字符串——每个工具结果都是字符串，无论成功还是错误（`Error: ...` 也是有效反馈，模型读到后会自我修正）；
3. **记忆是自动的**：messages 列表只增不减地累积——这既是记忆机制，也埋下第 7 章缓存经济学的伏笔；
4. REPL 中 history 跨轮传递，实现多轮对话记忆。

## 3.6 为什么说"模型即代理"

回看整份 v1：代码没有任何"智能"——没有规划算法、没有状态机、没有 if 判断任务类型。**所有智能来自模型，代码只是模型的手脚。**这是与传统"用代码编排 AI"框架（把 LLM 当作流水线上一个节点）的根本分野：这里 LLM 是大脑，代码是外设。

## 3.7 习题

**一、选择题**

1. edit_file 相比 sed 的可靠性来自？
   A. 更快  B. old_text 精确匹配且只替换第一处，失配即报错  C. 支持正则  D. 免费

2. safe_path 防御的攻击是？
   A. SQL 注入  B. 通过 ../ 等相对路径读写工作区之外的文件  C. DDoS  D. 缓冲区溢出

3. 工具执行出错时正确的处理是？
   A. 抛异常终止程序  B. 把错误信息作为字符串返回给模型  C. 静默忽略  D. 重启循环

4. "模型即代理"的含义是？
   A. 模型运行在代理服务器上  B. 决策智能全部来自模型，代码只提供工具与循环  C. 模型需要代理上网  D. 代理比模型重要

**二、简答题**

5. 为什么消息序列必须"先 append assistant（含 tool_use），再 append user（含 tool_result）"？

6. 系统提示的四条规则分别预防哪四种失败模式？

7. write_file 用 JSON 参数传 content，相比 v0 的 `echo '...' > file` 解决了什么问题？

**三、实践题**

8. 给 v1 增加第五个工具 `list_dir(path)`：写出它的 input_schema 定义、实现函数、以及在 execute_tool 中的分发分支。

**四、参考答案**

1. **B**。2. **B**。3. **B**——错误也是环境反馈，模型读到 "Error: Text not found" 会先 read_file 再重试。4. **B**。
5. API 要求对话交替且每个 tool_use 必须有配对的 tool_result（靠 tool_use_id 对应）。tool_use 属于模型的输出（assistant），执行结果属于环境的输入（user）；顺序或配对错误 API 会直接拒绝请求。
6. "Prefer tools over prose"防只解释不行动；"Never invent file paths"防路径幻觉；"Make minimal changes"防过度工程/范围蔓延；"summarize what changed"防改完不汇报导致用户不知道发生了什么。
7. shell 引号/转义问题：多行内容、引号嵌套、特殊字符在 echo/heredoc 里极易出错。JSON 字段直接携带任意文本，模型无需生成转义正确的 shell 代码，可靠性大幅提升。
8. 参考：

```python
# schema
{"name": "list_dir", "description": "List files in a directory.",
 "input_schema": {"type": "object",
                  "properties": {"path": {"type": "string"}},
                  "required": ["path"]}}
# 实现
def run_list(path: str) -> str:
    try:
        entries = sorted(p.name + ("/" if p.is_dir() else "")
                         for p in safe_path(path).iterdir())
        return "\n".join(entries) or "(empty)"
    except Exception as e:
        return f"Error: {e}"
# 分发
if name == "list_dir":
    return run_list(args["path"])
```

（注意复用 safe_path——新工具也必须过安全层。）

---

# 第 4 章 v2：结构化规划——TodoWrite（~300 行）

## 4.1 学习目标

1. 描述"上下文淡出（context fade）"问题；
2. 解释 TodoWrite 工具与 TodoManager 的三条约束及其理由；
3. 理解 activeForm 字段与"渲染即反馈"的设计；
4. 掌握 system reminder（系统提醒）的软引导技术；
5. 内化"结构既约束又赋能"的设计哲学。

## 4.2 问题：看不见的计划会淡出

v1 处理"重构 auth、加测试、更新文档"这类多步任务时的典型溃败：

```
v1: "我先做 A，再做 B，再做 C"   （计划只存在于模型"脑中"，不可见）
    …… 10 次工具调用之后 ……
    "等等，我刚才在做什么来着？"
```

计划淡出的原因回到注意力机制：计划说完就沉入越来越长的历史中，最近的工具输出在注意力上永远更"响"。**看不见的计划必然淡出——解法是把计划变成看得见、可更新的对象。**

## 4.3 解法：TodoWrite 工具

v2 只加一个工具。模型每次调用 TodoWrite 提交**完整的新任务列表**（全量替换，非增量修改），TodoManager 校验、存储、渲染：

```
[x] 重构 auth 模块
[>] 添加单元测试 <- Adding unit tests...
[ ] 更新文档

(1/3 completed)
```

渲染文本作为**工具结果**返回——于是计划以最新鲜的形式重新出现在上下文末尾，人与模型看到同一份计划。

## 4.4 三条约束

| 规则 | 理由 |
|------|------|
| 最多 20 项 | 防止无限膨胀的任务列表 |
| 只允许 1 项 in_progress | 强制单点专注，防止"同时做所有事" |
| 三字段必填（content/status/activeForm） | 保证结构化输出可校验、可渲染 |

status 只能是 pending / in_progress / completed；违规时 TodoManager 直接 `raise ValueError`——错误信息返回给模型，模型修正后重发。**校验器在这里扮演"环境反馈"的角色：不是劝模型守规矩，而是让不守规矩的调用失败。**

activeForm 是进行时描述（content="Add tests"，activeForm="Adding unit tests..."），在 in_progress 项旁展示，提供实时可见性。

## 4.5 System Reminder：软引导

约束之外还有**软提示**技术：

```python
INITIAL_REMINDER = "<reminder>Use TodoWrite for multi-step tasks.</reminder>"
NAG_REMINDER = "<reminder>10+ turns without todo update. Please update todos.</reminder>"
```

对话开始时注入前者；连续多轮未更新 todo 时注入后者。这是真实 Claude Code 也在用的技术（你在它的会话里能看到 `<system-reminder>` 标签）：**用环境注入的轻量提示，把模型行为拉回轨道，而不动系统提示**（不动系统提示的深层原因见第 7 章缓存）。

## 4.6 设计哲学：结构既约束又赋能

> "Structure constrains AND enables. 好的约束不是限制，而是脚手架。"

这个模式在智能体设计中无处不在：

- max_tokens 约束 → 换来可管理的响应；
- 工具 schema 约束 → 换来可解析的结构化调用；
- Todo 三约束 → 换来可见的计划与可追踪的进度。

设计智能体时问的不是"怎么给模型最大自由"，而是"**哪种约束能把模型的行为兑换成系统的能力**"。

## 4.7 习题

**一、选择题**

1. "上下文淡出"指？
   A. 屏幕变暗  B. 早期陈述的计划沉入长历史，注意力被最近内容占据而跑偏  C. 网络断线  D. token 用尽

2. TodoWrite 的更新语义是？
   A. 增量 patch  B. 全量替换（每次提交完整列表）  C. 只能追加  D. 只能删除

3. "只允许一项 in_progress"的目的是？
   A. 节省内存  B. 强制单点专注  C. API 限制  D. 美观

4. 违反约束的 TodoWrite 调用会？
   A. 被静默修正  B. 校验器抛错，错误作为工具结果返回，模型修正重发  C. 程序崩溃  D. 被忽略

**二、简答题**

5. 为什么把渲染后的 todo 列表作为工具结果返回是关键设计？（提示：从注意力位置角度答）

6. 比较硬约束（校验器抛错）与软引导（system reminder）：各适合什么场合？

7. 用"结构既约束又赋能"分析工具 schema：它约束了什么、赋能了什么？

**三、实践题**

8. 为 TodoManager 增加第四条约束："completed 的任务不允许变回 pending"。写出校验逻辑伪代码，并说明这条约束防止什么智能体行为。

**四、参考答案**

1. **B**。2. **B**——全量替换使校验可以整体进行，也免去增量语义的复杂性。3. **B**。4. **B**。
5. 注意力对上下文末尾最敏感。计划若只在历史深处，会被新内容淹没；作为最新的工具结果返回，计划每次更新都重新出现在"最响"的位置——模型每一轮都被迫面对自己的计划。
6. 硬约束适合**必须成立的结构性质**（字段完整、状态合法、唯一 in_progress）——违反即失败，不容商量；软引导适合**期望但非必需的行为**（记得用 todo、别忘更新）——轻推不强制，保留模型的自主判断。区分标准：违反的后果是"数据坏了"用硬，是"效果差了"用软。
7. 约束：模型必须输出符合 JSON Schema 的参数（字段名、类型、必填项）。赋能：宿主代码可以机械地解析与执行调用，无需理解自然语言——正是这种可解析性让"模型调用工具"成为可能。没有 schema 约束，就没有工具调用这个能力。
8. 伪代码：

```python
def update(self, items):
    old_completed = {t["content"] for t in self.items if t["status"] == "completed"}
    for item in items:
        if item["content"] in old_completed and item["status"] != "completed":
            raise ValueError(f"'{item['content']}' 已完成，不可回退")
    ...  # 原有校验
```

防止的行为：模型"忘记"某任务已做过而重做（重复劳动），或通过回退状态掩盖进度混乱——保证进度单调向前，todo 列表始终可信。

---

# 第 5 章 v3：子代理机制——分而治之（~450 行）

## 5.1 学习目标

1. 描述"上下文污染"问题及子代理如何解决；
2. 掌握 Agent 类型注册表（explore/code/plan）的设计：工具过滤 + 专用提示；
3. 逐行理解 Task 工具与 run_task 的实现；
4. 说出子代理的四大收益与典型编排流程。

## 5.2 问题：上下文污染

单代理做"探索代码库然后重构 auth"：

```
单代理历史：
  [探索] cat file1.py → 500 行
  [探索] cat file2.py → 300 行
  …… 再读 15 个文件 ……
  [开始重构] "等等，file1 里有什么来着？"
```

探索细节填满上下文，真正干活时预算已尽、注意力已散。这就是**上下文污染**。

## 5.3 解法：带隔离上下文的子代理

```
主代理历史：
  [Task: 探索代码库]
     → 子代理在自己的上下文里读 20 个文件
     → 只返回："auth 在 src/auth/，DB 在 src/models/"
  [以干净的上下文开始重构]
```

每个子代理有四要素：**①全新的消息历史；②按类型过滤的工具；③专用系统提示；④只把最终摘要返回给父代理。**

v0 用进程派生实现了同样的隔离；v3 把它**产品化**：进程换成函数内的独立 messages 列表，加上类型系统与进度显示。

## 5.4 Agent 类型注册表

```python
AGENT_TYPES = {
    "explore": {"description": "Read-only agent for exploring code...",
                "tools": ["bash", "read_file"],        # 无写权限
                "prompt": "You are an exploration agent. ... never modify files. Return a concise summary."},
    "code":    {"description": "Full agent for implementing features...",
                "tools": "*",                           # 全部工具
                "prompt": "You are a coding agent. Implement the requested changes efficiently."},
    "plan":    {"description": "Planning agent for designing strategies",
                "tools": ["bash", "read_file"],        # 只读
                "prompt": "... output a numbered implementation plan. Do NOT make changes."},
}
```

两层专化：

- **工具过滤**（get_tools_for_agent）：explore/plan 拿不到 write_file、edit_file——"不许改文件"不是请求而是**能力剥夺**（对比第 4 章：这属于硬约束）；
- **专用提示**：每类代理有聚焦的角色定义，比通用提示更少分心。

注意 explore/plan 仍有 bash（现实的权衡：探索需要 find/grep），所以隔离并非绝对——真正的产品还要限制 bash 本身（呼应 OpenTalon 教材第 8 章权限系统）。

## 5.5 Task 工具与 run_task

主代理获得一个新工具：

```python
{"name": "Task",
 "input_schema": {"properties": {
     "description": {...},                     # 短描述（进度显示用）
     "prompt": {...},                          # 子代理的完整任务指令
     "agent_type": {"enum": ["explore","code","plan"]}}}}
```

run_task 的核心（注意它与主循环是**同一个循环**，只是上下文不同）：

```python
def run_task(description, prompt, agent_type):
    config = AGENT_TYPES[agent_type]
    sub_system = f"You are a {agent_type} subagent at {WORKDIR}.\n{config['prompt']}..."
    sub_tools = get_tools_for_agent(agent_type)
    sub_messages = [{"role": "user", "content": prompt}]   # ← 隔离的关键：全新历史！
    while True:
        response = client.messages.create(model=MODEL, system=sub_system,
                                          messages=sub_messages, tools=sub_tools, ...)
        if response.stop_reason != "tool_use": break
        ...  # 执行工具、追加消息（同主循环）
    for block in response.content:            # 只提取最终文本返回
        if hasattr(block, "text"): return block.text
```

运行时打印 `[explore] find auth files ... 5 tools, 3.2s` 的进度行——**可见性不等于入上下文**：人类看得到过程，父代理只收到结论。

## 5.6 典型编排流程

```
用户: "把 auth 重构为 JWT"
主代理:
  1. Task(explore): "找出所有 auth 相关文件"     → "auth 在 src/auth/login.py..."
  2. Task(plan):    "设计 JWT 迁移方案"          → "1. 加 jwt 库 2. 建 utils..."
  3. Task(code):    "实现 JWT token"             → "创建了 jwt_utils.py，更新了 login.py"
  4. 向用户总结全部变更
```

主代理退化为**编排者**：不亲自读文件、不亲自写代码，只分解、派发、综合。四大收益：主上下文干净、可并行探索、任务自然分解、同一循环复用于不同上下文。

## 5.7 习题

**一、选择题**

1. 上下文污染的定义是？
   A. 病毒感染  B. 探索/中间细节填满上下文，挤占真正任务的预算与注意力  C. 内存泄漏  D. 网络劫持

2. 子代理隔离的技术关键是哪一行？
   A. print 进度  B. `sub_messages = [{"role":"user","content":prompt}]`（全新历史）  C. time.time()  D. enum 校验

3. explore 代理不能改文件是因为？
   A. 系统提示请求它别改  B. 工具列表里根本没有 write_file/edit_file（能力剥夺）  C. 文件只读  D. 运气

4. 父代理从子代理得到的是？
   A. 完整消息历史  B. 所有工具调用记录  C. 仅最终文本摘要  D. 屏幕截图

**二、简答题**

5. v0 的"bash 递归自调用"与 v3 的 Task 工具都实现了子代理。比较两者的实现机制与优劣。

6. 为什么说"run_task 与主循环是同一个循环"很重要？这揭示了智能体架构的什么性质？

7. "可见性不等于入上下文"——解释 v3 的进度显示设计如何同时满足人类可见与上下文干净。

**三、实践题**

8. 给 AGENT_TYPES 注册一个 "test" 代理：只能跑命令和读文件、专注运行测试并总结失败原因。写出注册表条目。

**四、参考答案**

1. **B**。2. **B**——子代理的历史从零开始，与父对话完全隔离。3. **B**——硬约束优于软请求：拿不到工具就物理上不可能修改。4. **C**。
5. v0：经 bash 派生新进程，隔离由操作系统进程边界保证；优点是极简（无需任何新代码）、天然支持无限嵌套；缺点是无类型系统、无工具过滤（子代理同样全能）、通信只有 stdout 字符串、开销是整个进程。v3：函数内新建 messages 列表实现隔离；优点是可按类型过滤工具与定制提示、可显示进度、开销小；缺点是需要 Task 工具与注册表代码。机制不同，原理相同：**新的干净历史 + 只回传摘要**。
6. 它证明"主代理/子代理"不是两种东西——同一个"模型+工具+循环"结构，仅仅换了 messages、system、tools 三个参数。智能体架构因此是**可递归组合的**：任何代理都能派生代理，复杂系统由同一原语嵌套而成。
7. 进度打印走 stdout 直接给人看（`[explore] ... 5 tools, 3.2s`），不进入任何 messages 列表；父代理的上下文只追加 Task 工具的返回值（摘要）。人的信息通道与模型的上下文通道被分开设计。
8. 参考：

```python
"test": {
    "description": "Run tests and summarize failures without modifying code",
    "tools": ["bash", "read_file"],
    "prompt": "You are a testing agent. Run the test suite, read failing tests, "
              "and return a concise summary of failures and probable causes. Do NOT modify files.",
}
```

---

# 第 6 章 v4：Skills 机制——知识外化（~550 行）

## 6.1 学习目标

1. 区分工具（Tool）与技能（Skill）：能力 vs 知识；
2. 阐述"知识外化"的范式转变；
3. 掌握三层渐进式披露与 SKILL.md 标准格式；
4. 逐行理解 SkillLoader 与 run_skill；
5. 解释"缓存保护注入"：为什么技能内容进 tool_result 而不进系统提示。

## 6.2 问题：模型缺的不是能力，是知识

v3 的代理什么都"能"做（有 bash），但它"知道"怎么处理 PDF 吗？知道 MCP 协议规范吗？知道系统化的代码评审清单吗？

| 概念 | 是什么 | 例子 |
|------|--------|------|
| **Tool** | 模型**能**做什么 | bash、read_file、write_file |
| **Skill** | 模型**知道怎么**做 | PDF 处理方法、MCP 开发规范、评审清单 |

**工具是能力，技能是知识。**

## 6.3 范式转变：知识外化

传统 AI 教模型新本事：收集数据 → 训练 → 部署（成本 $10K–$1M+，周期数周，需要 ML 团队与 GPU）。

Skills 的方式：**写一个 SKILL.md 文件**（成本为零，周期几分钟，任何人都会）。

> 就像不经训练就给模型热插拔一个 LoRA 适配器。

知识从模型参数里解放出来，存在**可编辑、可版本控制、可分享的文件**里——这就是知识外化（Knowledge Externalization）。

## 6.4 三层渐进式披露

```
第 1 层：元数据（永远加载）        ~100 token/技能
        仅 name + description
第 2 层：SKILL.md 正文（触发才加载） ~2000 token
        详细操作指令
第 3 层：资源（需要才读）           无上限
        scripts/、references/、assets/
```

启动时 SkillLoader 只把每个技能的一行描述放进系统提示；模型判断"这个任务需要 pdf 技能"时调用 Skill 工具，正文才注入；正文里提到的脚本/参考文档，模型再按需用 read_file/bash 去取。**上下文保持精瘦，知识深度不设上限。**

## 6.5 SKILL.md 标准与 SkillLoader

一个技能是一个**文件夹**：

```
skills/
├── pdf/
│   └── SKILL.md          # 必需：YAML frontmatter + Markdown 正文
├── mcp-builder/
│   ├── SKILL.md
│   └── references/       # 可选：文档、规范
└── code-review/
    ├── SKILL.md
    └── scripts/          # 可选：辅助脚本
```

SKILL.md 格式：

```markdown
---
name: pdf
description: Process PDF files. Use when reading, creating, or merging PDFs.
---

# PDF Processing Skill
## Reading PDFs
用 pdftotext 快速提取: `pdftotext input.pdf -`
...
```

SkillLoader 的四个方法：

- `parse_skill_md`：正则拆出 frontmatter 与正文，要求 name/description 必在；
- `load_skills`：扫描 skills/ 目录，**只加载元数据**；
- `get_descriptions`：生成第 1 层的一行式清单（进系统提示）；
- `get_skill_content`：取出第 2 层正文，并附上第 3 层资源清单提示（"本技能目录下有 scripts: extract.py ..."）。

description 的写法有讲究：**必须包含触发条件**（"Use when reading, creating, or merging PDFs"）——它是模型决定"要不要装载这个技能"的唯一依据。

## 6.6 缓存保护注入：进 tool_result，不进系统提示

run_skill 把技能正文包在标签里作为**工具结果**返回：

```python
return f"""<skill-loaded name="{skill_name}">
{content}
</skill-loaded>

Follow the instructions in the skill above to complete the user's task."""
```

为什么不把技能写进系统提示？——**缓存**：

```
错误做法：每次把技能拼进 system prompt → 前缀变化 → 缓存全失效 → 成本增加 20–50 倍
正确做法：技能作为 tool_result 追加在末尾 → 前缀不变 → 缓存命中
```

这是生产级 Claude Code 的真实做法，也是它成本可控的原因之一。完整原理见第 7 章。

## 6.7 五版本全景

至此完整拼图：

```
v4 智能体 = 核心循环(v1)
          + 结构化规划 TodoWrite(v2)
          + 上下文隔离 Task/子代理(v3)
          + 按需知识 Skill(v4)
          （而 v0 证明：这一切的最小本质只是 bash + 循环）
```

四个机制各解决一类资源问题：循环解决"行动"，todo 解决"注意力"，子代理解决"上下文预算"，skills 解决"知识供给"。

## 6.8 习题

**一、选择题**

1. Tool 与 Skill 的区别是？
   A. 没有区别  B. Tool 是能做什么（能力），Skill 是知道怎么做（知识）  C. Skill 更贵  D. Tool 是文件

2. 三层披露中，永远加载的是？
   A. SKILL.md 全文  B. name + description 元数据（约百 token）  C. scripts/ 全部脚本  D. 什么都不加载

3. 技能内容注入为 tool_result 而非改系统提示，是为了？
   A. 美观  B. 保护前缀缓存（改系统提示会让缓存全失效，成本暴涨）  C. 安全  D. 兼容旧版 API

4. "知识外化"相对于微调（fine-tuning）的优势不包括？
   A. 零成本、分钟级  B. 可版本控制与分享  C. 无需 ML 专业知识  D. 提升模型的基础推理能力

**二、简答题**

5. description 字段为什么必须写明"何时使用"？写差的 description 会导致什么两类失败？

6. 解释第 3 层资源如何被使用：get_skill_content 返回的"资源清单提示"起什么作用？

7. 用"渐进式披露"的语言总结 v4 的上下文策略，并类比 CLAUDE.md 的分层加载（如果你学过 OpenTalon 教材）。

**三、实践题**

8. 为"编写 Dockerfile"写一个完整 SKILL.md（frontmatter + 至少三节正文：基础镜像选择、层缓存优化、安全实践）。

**四、参考答案**

1. **B**。2. **B**。3. **B**。4. **D**——Skills 注入操作知识，但不改变模型参数，不提升基础推理能力。
5. 第 1 层只有 description 可供模型判断是否装载。写差的两类失败：①触发不足——任务明明相关模型却没装载（描述太窄/太模糊）；②误触发——不相关任务装载了技能，白白消耗第 2 层的约 2000 token（描述太宽）。
6. 正文注入时附带"本技能目录下有 scripts: xxx / references: yyy"的清单。它是第 3 层的**指针**：模型看到清单才知道这些资源存在，需要时用 read_file 或 bash 主动去取——资源本身不自动入上下文，保持按需原则。
7. v4 策略：元数据常驻（第 1 层）→ 触发时注入正文（第 2 层）→ 需要时读取资源（第 3 层），且注入走追加式的 tool_result 保护缓存。类比：CLAUDE.md 分层加载同构——根 CLAUDE.md 常驻（元层），子目录 CLAUDE.md 进目录才加载（触发层），@import 的专题文档按需（资源层）。同一原则：**上下文预算下的分层知识供给**。
8. 参考示例：

```markdown
---
name: dockerfile
description: Write production-grade Dockerfiles. Use when creating or optimizing Docker images.
---

# Dockerfile Skill

## 基础镜像选择
- 优先官方 slim/alpine 变体：python:3.12-slim
- 固定次版本标签，禁用 latest

## 层缓存优化
- 先 COPY 依赖清单并安装，再 COPY 源码（源码常变，依赖少变）
- 合并 RUN 减少层数；清理包管理器缓存于同一层

## 安全实践
- 创建非 root 用户并 USER 切换
- 不在镜像中留密钥；用构建参数/运行时环境变量
- 多阶段构建：构建工具不进最终镜像
```

---

# 第 7 章 上下文缓存经济学：别让你的 Agent 烧钱

## 7.1 学习目标

1. 建立"上下文是只追加日志"的心智模型；
2. 说出五种摧毁缓存的危险操作；
3. 计算缓存命中与失效的成本差异；
4. 掌握与缓存共存的正确工程实践。

> 核心警告：你在传统编程里习以为常的"编辑消息、修改历史、DIY 上下文"，在 LLM Agent 中会让成本暴增 **7–50 倍**。

## 7.2 前缀缓存的原理

LLM API 的**前缀缓存（prompt caching）**：如果本次请求的前缀（系统提示 + 历史消息）与上次完全相同，供应商可以复用已计算的注意力状态，只对新增部分做全量计算。缓存命中部分的计价通常仅为正常输入的约 1/10。

推论：**前缀必须逐字节不变**。任何对前缀的改动——哪怕改一个字符——都会使从改动点开始的全部内容缓存失效、按全价重算。

## 7.3 思维转变：上下文不是变量，是只追加日志

传统后端思维（危险）：

```python
user_state["step"] = 2          # 随意修改状态
del user_state["history"]       # 删除不需要的
```

LLM Agent 思维（必须遵守）：

```python
messages = [system_msg]         # 前缀永不改变
messages.append(user_msg)       # ✅ 只能追加
messages.append(assistant_msg)  # ✅ 只能追加
# messages[0] = xxx             # ❌ 改前缀 = 成本爆炸
# messages = messages[-10:]     # ❌ 删除 = 成本爆炸
```

## 7.4 五种危险操作

```python
# ❌ 1. 每次修改 system prompt（塞入动态状态）
system = f"Current step: {step}, files: {files}"
# ❌ 2. 编辑历史消息
messages[2]["content"] = "updated"
# ❌ 3. 滑动窗口删旧消息
messages = messages[-10:]
# ❌ 4. 用摘要替换历史（不当的 compaction）
messages = [summary] + messages[15:]
# ❌ 5. 中间插入消息
messages.insert(5, new_message)
```

共同点：**都改变了前缀**。许多用 LangChain/LangGraph/AutoGen 按传统思维"编排上下文"的开发者，正是这样在不知不觉中支付 7–50 倍的账单。

注意第 3、4 条的微妙之处：删旧消息/摘要替换**看似省 token**（发送量变小了），实际**费钱**（全部按未缓存价格重算）——省下的名义 token 远抵不上失去的 90% 缓存折扣。

## 7.5 成本算术

设某轮对话历史 100K token，新增 2K：

- **缓存命中**：100K × 0.1 + 2K × 1 = 约 12K 等效 token；
- **缓存失效**（改了前缀）：102K × 1 = 102K 等效 token；
- 一次失误 ≈ 8.5 倍成本。智能体动辄几十轮，轮轮失效就是数十倍账单。

## 7.6 正确实践清单

1. **系统提示保持静态**：动态信息（当前状态、时间）放到消息流末尾（system reminder 模式，见第 4 章）；
2. **历史只追加**：todo 更新、技能注入、状态提醒全部走 tool_result / 新消息追加（见第 4、6 章的设计正是为此）；
3. **确需压缩时，接受一次性代价**：/compact 类操作会失效缓存——它是**偶发的战略动作**（并且换来后续更短的历史），不是每轮的常规操作；
4. **把大内容外置**：与其把大文件常驻历史，不如存文件系统，让模型按需重读（重读虽花 token，但避免了常驻负担）；
5. **测量**：监控 API 返回的 cache_read / cache_creation 字段，缓存命中率是智能体系统的核心健康指标之一。

## 7.7 习题

**一、选择题**

1. 前缀缓存命中部分的典型计价约为正常输入的？
   A. 1/2  B. 1/10  C. 1/100  D. 免费

2. 以下哪个操作**不会**破坏缓存？
   A. 修改 system prompt  B. 在历史末尾追加新消息  C. 删除最旧的 10 条消息  D. 在第 5 条后插入消息

3. "滑动窗口删旧消息看似省钱实则费钱"的原因是？
   A. API 罚款  B. 发送量虽小但前缀改变导致全量按未缓存价重算，损失 90% 折扣  C. 网络变慢  D. 模型变笨

4. 把动态状态（如当前步骤）放进系统提示的正确替代方案是？
   A. 不提供状态  B. 以 system reminder / tool_result 形式追加在消息流末尾  C. 写进模型参数  D. 用更大的模型

**二、简答题**

5. 解释为什么 v2 的 TodoWrite（全量渲染作为 tool_result 返回）和 v4 的技能注入（tool_result 而非系统提示）都是"缓存友好"的设计。

6. /compact 类的历史压缩明明破坏缓存，为什么仍然是合理操作？它与"每轮滑动窗口"的本质区别是什么？

**三、计算题**

7. 一个智能体任务运行 30 轮，每轮历史平均 60K token、新增 2K。(a) 全程缓存命中的等效计费 token？(b) 因每轮都在改系统提示导致全程缓存失效的等效计费 token？(c) 相差多少倍？

**四、参考答案**

1. **B**。2. **B**——追加不改变前缀，是唯一安全的常规操作。3. **B**。4. **B**。
5. 二者的新信息都以**追加**方式进入上下文末尾：todo 的最新状态是新一条 tool_result，技能正文也是新一条 tool_result。系统提示与既有历史逐字节未动，前缀缓存全程有效。若改为"把 todo/技能拼进系统提示"，则每次更新都重算全部历史。
6. 压缩是**低频的战略动作**：一次性支付缓存重建成本，换来此后每轮历史大幅变短（新前缀更便宜且重新可缓存），长期净收益为正。滑动窗口是**每轮的常规操作**：轮轮改前缀、轮轮全价重算，且没有换来任何后续收益。区别在频率与收益结构：偶发投资 vs 持续放血。
7. (a) 每轮 ≈ 60K×0.1 + 2K×1 = 8K，30 轮 ≈ **240K**；(b) 每轮 ≈ 62K×1 = 62K，30 轮 ≈ **1860K**；(c) 约 **7.75 倍**——这正是"7–50 倍"警告的下端。

---

# 第 8 章 总结与进阶：从玩具到产品的距离

## 8.1 学习目标

1. 完整复述五版本的概念栈与各自解决的资源问题；
2. 列出 mini 版与生产级 Claude Code 之间的主要差距；
3. 规划自己的扩展路线。

## 8.2 五版本概念栈（总复习）

| 版本 | 新概念 | 解决的问题 | 关键机制 |
|------|--------|-----------|----------|
| v0 | bash + 循环 | 智能体的最小本质 | 一个工具；进程派生即子代理 |
| v1 | 四工具 | 可靠的文件操作 | 结构化参数；safe_path；错误即反馈 |
| v2 | TodoWrite | 计划淡出 | 三约束校验；渲染进上下文末尾；system reminder |
| v3 | Task/子代理 | 上下文污染 | 全新历史；工具过滤；只回传摘要 |
| v4 | Skill | 领域知识供给 | 三层渐进披露；SKILL.md；缓存保护注入 |

再加上第 7 章的横切原则：**上下文是只追加日志**。

一句话总纲：**智能体 = 模型（决策）+ 工具（手脚）+ 循环（生命）+ 上下文纪律（经济性）**。

## 8.3 与生产级 Claude Code 的差距

诚实清单——mini 版为教学而省略的东西：

1. **权限系统**：mini 版只有黑名单；产品需要 allow/deny 规则、权限模式、人工确认流（参见 OpenTalon 教材第 8 章）；
2. **流式输出**：mini 版等完整回复；产品逐 token 流式展示；
3. **上下文压缩**：mini 版历史无限增长；产品有 /compact 与自动摘要；
4. **Hooks 与可扩展性**：生命周期钩子、MCP 外部工具协议；
5. **健壮性**：API 重试、速率限制处理、并发工具调用、会话持久化；
6. **终端体验**：Rich 渲染、快捷键、diff 预览。

关键认知：这些都是**精化**，不改变核心架构——你已经掌握的循环仍然是那台发动机。

## 8.4 扩展路线建议

按性价比排序的动手方向：

1. 给 v4 加一个 **权限询问**：执行 bash 前打印命令并等待 y/n；
2. 加 **流式输出**（`client.messages.stream`）；
3. 实现 **简易 /compact**：把前 N 条消息交给模型摘要，开启新会话（注意第 7 章：这是战略动作）；
4. 写 3 个自己领域的 **SKILL.md**（最高杠杆：零代码提升能力）；
5. 给 v3 的子代理加 **并行派发**（asyncio 同时跑多个 explore）；
6. 接入一个 **MCP 服务器**，体验标准化工具协议。

## 8.5 期末综合题

**一、综合简答**

1. 面试官问："Claude Code 的核心架构是什么？"请用不超过 200 字回答，必须涵盖：循环、工具、终止条件、上下文。

2. 你的智能体在长任务中出现三个症状：①忘记计划跑偏；②读了太多文件后开始胡言乱语；③账单是预期的 20 倍。分别诊断病因并给出对应机制（各对应本教材某一章）。

3. "结构既约束又赋能"——从五个版本中各举一例（共 5 例）。

**二、设计题**

4. 设计一个"文档翻译智能体"：需要批量读取 docs/ 下的 Markdown、按术语表翻译、写入 translated/。要求写出：工具清单（并说明各自必要性）、Agent 类型注册（至少两类）、一个 SKILL.md 的 frontmatter、以及防止成本失控的三条措施。

**三、参考答案**

1. 参考要点：核心是一个循环——把对话历史与工具定义发给模型；模型返回文本或工具调用；有工具调用则执行之，结果以 tool_result 追加进历史再次调用模型；直到模型给出不含工具调用的回复（stop_reason ≠ tool_use），循环终止。模型是唯一决策者（调什么工具、何时停），代码只提供工具与循环。上下文是只追加的日志，既是记忆机制也是缓存与成本的关键。

2. ①计划淡出 → v2：引入 TodoWrite，把计划以工具结果形式反复出现在上下文末尾，配合 system reminder；②上下文污染 → v3：把大宗探索派给子代理，主上下文只收摘要；③缓存失效 → 第 7 章：检查是否存在改系统提示/删改历史等破坏前缀的操作，改为只追加模式，监控 cache_read 指标。

3. 示例：v0——bash 单工具的约束换来极简可递归的架构；v1——工具 schema 约束换来可机械解析执行的调用；v2——"唯一 in_progress"约束换来单点专注与可见进度；v3——explore 代理被剥夺写工具，换来可放心的大范围探索；v4——SKILL.md 必须有 name/description 的约束，换来可自动发现、按需装载的知识库。

4. 参考要点：工具——read_file（读源文档）、write_file（写译文）、bash（列目录/统计）、TodoWrite（追踪每个文件的翻译状态）、Skill（装载翻译规范）；Agent 类型——explore（只读，盘点待译文件与结构）、translate/code（可写，执行翻译写入）；SKILL.md frontmatter 示例：

```markdown
---
name: doc-translation
description: Translate Markdown docs using the project glossary. Use when translating files in docs/.
---
```

成本措施：①逐文件处理而非全量读入（按需读取）；②术语表与规范放 SKILL.md 按需注入而非系统提示（缓存友好）；③每个文件的翻译派给独立子代理，主上下文只记录完成状态（隔离+可并行）；④输出截断与 todo 全量替换维持历史精瘦。任答三条。

---

## 附录 A：五版本核心 API 速查

```python
# 调用模型
response = client.messages.create(model=MODEL, system=SYSTEM,
                                  messages=messages, tools=TOOLS, max_tokens=8000)
# 判断是否继续
response.stop_reason == "tool_use"
# 遍历内容块
for block in response.content:
    block.type          # "text" | "tool_use"
    block.text          # 文本块
    block.id, block.name, block.input   # 工具调用块
# 回传工具结果（user 角色）
{"type": "tool_result", "tool_use_id": block.id, "content": output}
```

## 附录 B：核心概念中英对照

| 中文 | 英文 | 出处 |
|------|------|------|
| 核心循环 | agent loop | 第 1 章 |
| 进程隔离即上下文隔离 | process isolation = context isolation | 第 2 章 |
| 模型即代理 | the model IS the agent | 第 3 章 |
| 上下文淡出 | context fade | 第 4 章 |
| 结构既约束又赋能 | structure constrains AND enables | 第 4 章 |
| 上下文污染 | context pollution | 第 5 章 |
| 知识外化 | knowledge externalization | 第 6 章 |
| 渐进式披露 | progressive disclosure | 第 6 章 |
| 缓存保护注入 | cache-preserving injection | 第 6 章 |
| 前缀缓存 | prompt/prefix caching | 第 7 章 |
| 只追加日志 | append-only log | 第 7 章 |

（全教材完）
