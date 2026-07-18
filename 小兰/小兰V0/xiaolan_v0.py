#!/usr/bin/env python3
"""小兰 v0 —— 专注于 ESP32 数字钢琴开发的单片机 agent

基于 mini-claude-code(v4) 架构，使用 Kimi 大模型（Anthropic 兼容端点，
消息角色为 system/user/assistant，工具结果放在 user 消息的 tool_result 块中）。

功能清单：
  - agent 循环：LLM → tool_use → 执行 → tool_result 入 user 消息 → 循环，
    直到 stop_reason != "tool_use" 输出纯文本
  - 基础工具：bash / read_file / write_file / edit_file / TodoWrite
  - Skill 机制：SKILL.md 规范（YAML frontmatter + 按需注入，同 mini-claude-code v4）
  - 子代理：Task 工具（总结冗长串口日志），单次响应限时 5 分钟，不可嵌套
  - MCP：最小标准协议客户端（见下方协议说明），本地 stdio MCP server
  - 最大迭代 100 轮，耗尽后输出进度报告
  - 问候语金丝雀：每轮回复第一句必须是固定问候语，缺失则判定上下文过长，
    自动压缩上下文并重试
  - 安全红线：只做单片机相关的事，禁止可能损坏开发板的操作

MCP 标准协议格式（stdio 传输）：
  - 传输层：子进程 stdin/stdout，换行分隔的 JSON-RPC 2.0 消息
  - 握手：  initialize → notifications/initialized
  - 发现：  tools/list → {tools: [{name, description, inputSchema}]}
  - 调用：  tools/call {name, arguments}
           → {content: [{type: "text", text}], isError}

运行：
  cp .env.example .env   # 然后编辑 .env 填入 Kimi API Key
  ../../piano_workflow/.venv/bin/python xiaolan_v0.py
"""

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path


def _bootstrap_interpreter():
    """系统 python3 直接运行时，自动切换到 piano_workflow 的 venv 解释器
    （anthropic/mcp/numpy 都装在那里）。切换方式是原地 re-exec。

    注意：不能用 resolve() 比较解释器路径——venv 的 bin/python 是指向
    系统 python 的符号链接，resolve 后会误判为"已在 venv 中"。
    正确的判据是 sys.prefix 是否等于 venv 目录。
    """
    try:
        import anthropic  # noqa: F401
        import dotenv     # noqa: F401
        return
    except ModuleNotFoundError:
        script = Path(__file__).resolve()
        venv_dir = script.parents[2] / "piano_workflow" / ".venv"
        venv_py = venv_dir / "bin" / "python"
        already_in_venv = Path(sys.prefix).resolve() == venv_dir.resolve()
        if venv_py.exists() and not already_in_venv:
            os.execv(str(venv_py), [str(venv_py), str(script), *sys.argv[1:]])
        # venv 不存在则继续，让后续 import 报原始错误


_bootstrap_interpreter()

from dotenv import load_dotenv

# =============================================================================
# 配置
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]          # 小兰/小兰V0 → 项目根目录
load_dotenv(SCRIPT_DIR / ".env")

API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("MOONSHOT_API_KEY")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.moonshot.cn/anthropic")
MODEL = os.getenv("MODEL_NAME", "kimi-k3")

WORKDIR = Path.cwd()
SKILLS_DIR = SCRIPT_DIR / "skills"

MAX_ITERATIONS = 100                          # 单任务最大工具调用轮数
SUBAGENT_TIMEOUT = 300                        # 子代理单次响应限时 5 分钟
GREETING = "你好，我是小兰，很高兴可以帮到你。"

# 本地 MCP 服务器（stdio）。esp32_piano_mcp.py 需要其 venv 里的 mcp/numpy。
VENV_PY = PROJECT_ROOT / "piano_workflow" / ".venv" / "bin" / "python"
if not VENV_PY.exists():
    VENV_PY = Path(sys.executable)
MCP_SERVERS = [
    {
        "name": "esp32-piano",
        "cmd": [str(VENV_PY), str(PROJECT_ROOT / "piano_workflow" / "esp32_piano_mcp.py")],
    },
]

_client = None

# Kimi K3 是思考模型：思考内容会吃掉 max_tokens 预算（实测 max_tokens=2000
# 时思考耗尽预算、正文一个字都没返回）。agent 场景需要稳定的工具调用输出，
# 故关闭思考。想体验思考模式可改 {"type": "enabled"}（未验证，自行测试）。
THINKING = {"type": "disabled"}


def get_client():
    """惰性创建 API client（缺 key 时给出明确提示而不是报错堆栈）。"""
    global _client
    if _client is None:
        if not API_KEY:
            sys.exit("未找到 API Key：请复制 .env.example 为 .env 并填入 Kimi API Key")
        from anthropic import Anthropic
        _client = Anthropic(api_key=API_KEY, base_url=BASE_URL)
    return _client


def llm_create(**kwargs):
    """统一的 LLM 调用入口：所有请求都注入 thinking 配置。"""
    return get_client().messages.create(thinking=THINKING, **kwargs)


def check_config():
    """启动时检查 .env 配置，问题早发现、提示说人话。"""
    env_file = SCRIPT_DIR / ".env"
    if not env_file.exists():
        sys.exit(f"未找到 {env_file}\n请执行: cp .env.example .env 然后编辑填入 Key")
    if not API_KEY:
        sys.exit(".env 中缺少 ANTHROPIC_API_KEY")
    if "sk-xxx" in API_KEY or len(API_KEY) < 20:
        sys.exit(".env 中的 ANTHROPIC_API_KEY 还是占位符，请填入真实 Key")
    masked = API_KEY[:3] + "*" * 6 + API_KEY[-2:]
    print(f"API Key: {masked} (长度 {len(API_KEY)})")


# =============================================================================
# MCP 最小标准客户端（JSON-RPC 2.0 over stdio，换行分隔 JSON）
# =============================================================================

class MCPClient:
    """连接一个本地 stdio MCP 服务器。

    协议流程（MCP 标准）：
      1. 发送 initialize（协议版本、客户端信息），收到服务器能力响应
      2. 发送 notifications/initialized 通知，握手完成
      3. tools/list 获取工具列表（name/description/inputSchema）
      4. tools/call 调用工具，结果在 content 块的 text 里
    """

    def __init__(self, name: str, cmd: list, timeout: float = 180):
        self.name = name
        self.timeout = timeout
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
        self._next_id = 0
        self._queue = queue.Queue()
        # 后台线程持续读服务器 stdout，把 JSON 消息放进队列
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._initialize()

    def _read_loop(self):
        for line in self.proc.stdout:
            line = line.strip()
            if line:
                try:
                    self._queue.put(json.loads(line))
                except json.JSONDecodeError:
                    pass                # 非 JSON 行（如调试输出）忽略
        self._queue.put(None)           # EOF：服务器退出

    def _request(self, method: str, params: dict = None) -> dict:
        self._next_id += 1
        rid = self._next_id
        req = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            req["params"] = params
        self.proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        deadline = time.time() + self.timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError(f"MCP 调用超时: {method}")
            try:
                msg = self._queue.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError(f"MCP 调用超时: {method}")
            if msg is None:
                raise RuntimeError(f"MCP 服务器 {self.name} 已退出")
            if msg.get("id") != rid:
                continue                # 服务器通知（无 id 或 id 不匹配），跳过
            if "error" in msg:
                raise RuntimeError(f"MCP 错误: {msg['error']}")
            return msg.get("result", {})

    def _notify(self, method: str, params: dict = None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def _initialize(self):
        self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "xiaolan", "version": "0.1"},
        })
        self._notify("notifications/initialized")

    def list_tools(self) -> list:
        return self._request("tools/list").get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> str:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        parts = [c.get("text", "") for c in result.get("content", [])
                 if c.get("type") == "text"]
        text = "\n".join(p for p in parts if p)
        if result.get("isError"):
            return f"Error: {text}"
        return text or "(无输出)"


MCP_CLIENTS = {}      # 工具名 → MCPClient
MCP_TOOL_DEFS = []    # Anthropic 格式的工具定义


def init_mcp():
    """启动所有本地 MCP 服务器并注册其工具。单个失败不影响其他工具。"""
    for cfg in MCP_SERVERS:
        try:
            client = MCPClient(cfg["name"], cfg["cmd"])
            tools = client.list_tools()
            for t in tools:
                MCP_CLIENTS[t["name"]] = client
                MCP_TOOL_DEFS.append({
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("inputSchema",
                                         {"type": "object", "properties": {}}),
                })
            print(f"MCP 服务器 {cfg['name']}: {len(tools)} 个工具已注册")
        except Exception as e:
            print(f"⚠ MCP 服务器 {cfg['name']} 启动失败: {e}（其工具不可用）")


# =============================================================================
# SkillLoader（SKILL.md 规范，同 mini-claude-code v4：渐进披露）
# =============================================================================

class SkillLoader:
    """skills/ 下每个子目录一个技能：SKILL.md = YAML frontmatter + 正文。

    第一层：name+description 常驻 system prompt（每个约 100 token）
    第二层：Skill 工具调用时才注入正文（作为 tool_result，不污染 system prompt）
    第三层：references/ scripts/ 等资源按需读取
    """

    def __init__(self, skills_dir: Path):
        self.skills = {}
        self.load(skills_dir)

    def parse(self, path: Path):
        content = path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return None
        frontmatter, body = match.groups()
        metadata = {}
        for line in frontmatter.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip().strip("\"'")
        if "name" not in metadata or "description" not in metadata:
            return None
        return {"name": metadata["name"], "description": metadata["description"],
                "body": body.strip(), "dir": path.parent}

    def load(self, skills_dir: Path):
        if not skills_dir.exists():
            return
        for skill_dir in skills_dir.iterdir():
            skill_md = skill_dir / "SKILL.md"
            if skill_dir.is_dir() and skill_md.exists():
                skill = self.parse(skill_md)
                if skill:
                    self.skills[skill["name"]] = skill

    def get_descriptions(self) -> str:
        if not self.skills:
            return "(无可用技能)"
        return "\n".join(f"- {n}: {s['description']}"
                         for n, s in self.skills.items())

    def get_content(self, name: str):
        skill = self.skills.get(name)
        if not skill:
            return None
        content = f"# Skill: {skill['name']}\n\n{skill['body']}"
        resources = []
        for folder, label in [("scripts", "Scripts"), ("references", "References"),
                              ("assets", "Assets")]:
            folder_path = skill["dir"] / folder
            if folder_path.exists():
                files = list(folder_path.glob("*"))
                if files:
                    resources.append(f"{label}: {', '.join(f.name for f in files)}")
        if resources:
            content += f"\n\n**可用资源（位于 {skill['dir']}）:**\n"
            content += "\n".join(f"- {r}" for r in resources)
        return content

    def list_skills(self) -> list:
        return list(self.skills.keys())


SKILLS = SkillLoader(SKILLS_DIR)


# =============================================================================
# TodoManager
# =============================================================================

class TodoManager:
    """任务清单：同时只能有一个 in_progress，最多 20 条。"""

    def __init__(self):
        self.items = []

    def update(self, items: list) -> str:
        validated = []
        in_progress = 0
        for i, item in enumerate(items):
            content = str(item.get("content", "")).strip()
            status = str(item.get("status", "pending")).lower()
            active = str(item.get("activeForm", "")).strip()
            if not content or not active:
                raise ValueError(f"第 {i} 项: content 和 activeForm 必填")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"第 {i} 项: status 非法")
            if status == "in_progress":
                in_progress += 1
            validated.append({"content": content, "status": status,
                              "activeForm": active})
        if in_progress > 1:
            raise ValueError("同时只能有一个任务 in_progress")
        self.items = validated[:20]
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "无任务。"
        marks = {"completed": "[x]", "in_progress": "[>]", "pending": "[ ]"}
        lines = [f"{marks[t['status']]} {t['content']}" for t in self.items]
        done = sum(1 for t in self.items if t["status"] == "completed")
        return "\n".join(lines) + f"\n({done}/{len(self.items)} 完成)"


TODO = TodoManager()


# =============================================================================
# 子代理（总结冗长内容，不可嵌套，单次限时 5 分钟）
# =============================================================================

AGENT_TYPES = {
    "log-summary": {
        "description": "总结冗长内容（单片机串口日志、MicroPython 错误堆栈、长文件），只返回关键结论",
        "tools": ["bash", "read_file"],
        "prompt": (
            "你是小兰的子代理，专职压缩信息。从冗长内容（ESP32 串口日志、"
            "MicroPython Traceback、长文件）中提炼：错误类型、出错的文件与行号、"
            "直接原因、可能的修复方向。只读，不修改任何文件。"
            "返回不超过 200 字的结论。"
        ),
    },
}


def get_agent_descriptions() -> str:
    return "\n".join(f"- {n}: {c['description']}"
                     for n, c in AGENT_TYPES.items())


# =============================================================================
# System Prompt
# =============================================================================

SYSTEM = f"""你是小兰 v0 —— 专注于 ESP32 数字钢琴开发的单片机 agent，运行在 Ubuntu 24.04 虚拟机中，工作目录 {WORKDIR}。

【最高优先级】你的每一轮回复，第一句话必须一字不差地是：
{GREETING}

【工作范围】只处理与单片机（ESP32）和数字钢琴相关的任务：编写与调试 MicroPython 程序、上传与运行、串口日志分析、音频闭环验证等。与单片机无关的请求，礼貌拒绝并说明你的工作范围。

【工作循环】理解需求 → 编写/修改代码 → 用 MCP 工具上传 → 运行 → 读取串口输出与音频分析指标 → 有问题则修复 → 重新部署，直到硬件验证通过。只有硬件验证通过才算完成，代码写完不算完成。一次只改一个变量，不瞎猜。

【技能】涉及 ESP32 引脚、音频、调试知识时，先调用 Skill 工具加载对应技能：
{SKILLS.get_descriptions()}

【子代理】遇到明显冗长的内容（如大段串口错误日志），用 Task 工具交给子代理总结，只取回结论，保持自己的上下文干净。

【禁止的操作 —— 安全红线】
1. 禁止任何可能损坏开发板的操作：擦除 Flash（erase_flash）、刷写固件（esptool）
2. 禁止危险 shell 命令：rm -rf /、sudo、shutdown、reboot、mkfs、dd 写设备
3. 文件操作仅限当前工作目录内
4. 串口操作仅限 /dev/ttyACM* 与 /dev/ttyUSB*
5. GPIO34/35 是输入专用引脚，禁止配置为输出
6. 不做与单片机无关的事

【迭代限制】单个任务最多 {MAX_ITERATIONS} 轮工具调用。若达到上限仍未完成，输出进度报告：已完成什么、卡在哪里、下一步建议。

【行事方式】优先用工具行动而非空谈。多步骤任务先用 TodoWrite 列计划。完成后总结改了什么、硬件验证结果是什么。"""


# =============================================================================
# 工具定义
# =============================================================================

BASE_TOOLS = [
    {
        "name": "bash",
        "description": "执行 shell 命令。",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "读取文件内容。",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"},
                           "limit": {"type": "integer"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "写入文件（覆盖）。",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"},
                           "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "精确替换文件中的文本。",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"},
                           "old_text": {"type": "string"},
                           "new_text": {"type": "string"}},
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "TodoWrite",
        "description": "更新任务清单。",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "status": {"type": "string",
                                       "enum": ["pending", "in_progress", "completed"]},
                            "activeForm": {"type": "string"},
                        },
                        "required": ["content", "status", "activeForm"],
                    },
                }
            },
            "required": ["items"],
        },
    },
]

TASK_TOOL = {
    "name": "Task",
    "description": f"把冗长内容交给子代理总结，只取回结论（单次限时 5 分钟）。\n\n子代理类型：\n{get_agent_descriptions()}",
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "简短任务描述"},
            "prompt": {"type": "string", "description": "给子代理的完整指令（含要总结的内容或文件路径）"},
            "agent_type": {"type": "string", "enum": list(AGENT_TYPES.keys())},
        },
        "required": ["description", "prompt", "agent_type"],
    },
}

SKILL_TOOL = {
    "name": "Skill",
    "description": f"加载技能以获得领域知识。任务匹配时立即使用。\n\n可用技能：\n{SKILLS.get_descriptions()}",
    "input_schema": {
        "type": "object",
        "properties": {"skill": {"type": "string", "description": "技能名称"}},
        "required": ["skill"],
    },
}

LOCAL_TOOLS = BASE_TOOLS + [TASK_TOOL, SKILL_TOOL]


def get_all_tools() -> list:
    """本地工具 + MCP 工具，对模型完全同构。"""
    return LOCAL_TOOLS + MCP_TOOL_DEFS


# =============================================================================
# 工具实现
# =============================================================================

def safe_path(p: str) -> Path:
    """文件操作限制在工作目录内。"""
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"路径越出工作目录: {p}")
    return path


BANNED_CMDS = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs",
               "dd of=/dev", "esptool", "erase_flash"]


def run_bash(cmd: str) -> str:
    if any(b in cmd for b in BANNED_CMDS):
        return "Error: 禁止的命令（安全红线，见 system prompt）"
    try:
        r = subprocess.run(cmd, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=60)
        return ((r.stdout + r.stderr).strip() or "(无输出)")[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit:
            lines = lines[:limit]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"已写入 {len(content)} 字节到 {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        text = fp.read_text()
        if old_text not in text:
            return f"Error: 在 {path} 中找不到要替换的文本"
        fp.write_text(text.replace(old_text, new_text, 1))
        return f"已编辑 {path}"
    except Exception as e:
        return f"Error: {e}"


def run_todo(items: list) -> str:
    try:
        return TODO.update(items)
    except Exception as e:
        return f"Error: {e}"


def run_skill(skill_name: str) -> str:
    """加载技能正文，作为 tool_result 注入（不进 system prompt，保缓存）。"""
    content = SKILLS.get_content(skill_name)
    if content is None:
        available = ", ".join(SKILLS.list_skills()) or "无"
        return f"Error: 未知技能 '{skill_name}'。可用: {available}"
    return f"""<skill-loaded name="{skill_name}">
{content}
</skill-loaded>

请遵循以上技能说明完成任务。"""


def _text_of(response) -> str:
    return "".join(b.text for b in response.content
                   if getattr(b, "type", None) == "text")


def _starts_with_greeting(text) -> bool:
    return bool(text) and text.strip().startswith(GREETING)


def _subagent_loop(prompt: str, config: dict) -> str:
    """子代理独立循环：独立上下文、工具受限、不可再嵌套子代理。"""
    sub_system = f"""你是小兰的子代理，工作目录 {WORKDIR}。

{config["prompt"]}

完成任务后返回简洁结论。"""
    allowed = config.get("tools", [])
    sub_tools = [t for t in BASE_TOOLS if t["name"] in allowed]
    sub_messages = [{"role": "user", "content": prompt}]

    for _ in range(15):                       # 子代理迭代上限 15 轮
        response = llm_create(
            model=MODEL, system=sub_system, messages=sub_messages,
            tools=sub_tools, max_tokens=4000,
        )
        if response.stop_reason != "tool_use":
            return _text_of(response) or "(子代理无文本返回)"
        results = []
        for tc in [b for b in response.content if b.type == "tool_use"]:
            output = execute_tool(tc.name, tc.input)
            results.append({"type": "tool_result", "tool_use_id": tc.id,
                            "content": output})
        sub_messages.append({"role": "assistant", "content": response.content})
        sub_messages.append({"role": "user", "content": results})
    return "(子代理达到迭代上限，未得出结论)"


def run_task(description: str, prompt: str, agent_type: str) -> str:
    """子代理入口：5 分钟硬限时，超时放弃。"""
    config = AGENT_TYPES.get(agent_type)
    if not config:
        return f"Error: 未知子代理类型 '{agent_type}'"

    holder = {}

    def worker():
        try:
            holder["result"] = _subagent_loop(prompt, config)
        except Exception as e:
            holder["result"] = f"Error: 子代理异常: {e}"

    t = threading.Thread(target=worker, daemon=True)
    start = time.time()
    t.start()
    t.join(SUBAGENT_TIMEOUT)
    if t.is_alive():
        return (f"Error: 子代理超时（{SUBAGENT_TIMEOUT // 60} 分钟），已放弃。"
                "请缩小任务范围，或直接在主上下文处理。")
    elapsed = time.time() - start
    print(f"  [子代理完成，耗时 {elapsed:.1f}s]")
    return holder.get("result", "Error: 子代理无返回")


def execute_tool(name: str, args: dict) -> str:
    """工具分发：先本地工具，再 MCP 工具。"""
    if name == "bash":
        return run_bash(args["command"])
    if name == "read_file":
        return run_read(args["path"], args.get("limit"))
    if name == "write_file":
        return run_write(args["path"], args["content"])
    if name == "edit_file":
        return run_edit(args["path"], args["old_text"], args["new_text"])
    if name == "TodoWrite":
        return run_todo(args["items"])
    if name == "Task":
        return run_task(args["description"], args["prompt"], args["agent_type"])
    if name == "Skill":
        return run_skill(args["skill"])
    if name in MCP_CLIENTS:
        try:
            return MCP_CLIENTS[name].call_tool(name, args)
        except Exception as e:
            return f"Error: MCP 工具 {name} 调用失败: {e}"
    return f"Unknown tool: {name}"


# =============================================================================
# 上下文压缩（问候语金丝雀触发）
# =============================================================================

def _block_desc(b) -> str:
    btype = b.get("type") if isinstance(b, dict) else getattr(b, "type", None)
    if btype == "text":
        txt = b.get("text", "") if isinstance(b, dict) else getattr(b, "text", "")
        return f"文本: {txt[:400]}"
    if btype == "tool_use":
        name = b.get("name") if isinstance(b, dict) else b.name
        inp = b.get("input") if isinstance(b, dict) else b.input
        return f"调用工具 {name}: {json.dumps(inp, ensure_ascii=False)[:200]}"
    if btype == "tool_result":
        c = b.get("content") if isinstance(b, dict) else getattr(b, "content", "")
        return f"工具结果: {str(c)[:300]}"
    return str(b)[:200]


def compress_context(messages: list):
    """用 LLM 把全部历史压缩成摘要并替换。

    只在 end_turn 之后调用（无悬挂的 tool_use/tool_result 配对），
    所以整体替换是安全的。
    """
    lines = []
    for m in messages:
        role = m.get("role", "?")
        content = m.get("content")
        if isinstance(content, str):
            lines.append(f"[{role}] {content[:600]}")
        elif isinstance(content, list):
            for b in content:
                lines.append(f"[{role}] {_block_desc(b)}")
    transcript = "\n".join(lines)[-30000:]

    resp = llm_create(
        model=MODEL, max_tokens=2000,
        system=("你是上下文压缩器。把 agent 对话历史压缩成结构化摘要，保留："
                "用户目标、已完成的步骤、当前文件/代码状态、未解决的问题、"
                "下一步计划。丢弃冗余的工具输出细节。"),
        messages=[{"role": "user", "content": f"请压缩以下对话历史：\n\n{transcript}"}],
    )
    summary = _text_of(resp)
    messages[:] = [{
        "role": "user",
        "content": (f"【上下文已压缩】以下是之前对话的摘要：\n{summary}\n\n"
                    "请基于摘要继续任务。"),
    }]
    print(f"  [上下文已压缩：{len(lines)} 条记录 → 摘要 {len(summary)} 字]")


# =============================================================================
# Agent 主循环
# =============================================================================

def agent_loop(messages: list):
    """循环：LLM → tool_use → 执行 → tool_result 入 user 消息 → 循环。

    返回 (最后一轮纯文本, 本轮是否问候过)。
    "问候过"的判据：本轮第一个文本块以固定问候语开头——只要模型在本轮
    开头问了好，说明 system prompt 仍在生效，无需触发上下文压缩。
    达到 MAX_ITERATIONS 轮后强制输出进度报告。
    """
    iterations = 0
    first_text = None
    while True:
        response = llm_create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=get_all_tools(), max_tokens=8000,
        )
        for block in response.content:
            if getattr(block, "type", None) == "text":
                print(block.text)
                if first_text is None and block.text.strip():
                    first_text = block.text

        if response.stop_reason != "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            return _text_of(response), _starts_with_greeting(first_text)

        iterations += 1
        tool_calls = [b for b in response.content if b.type == "tool_use"]

        if iterations >= MAX_ITERATIONS:
            # 迭代耗尽：不再执行工具，要求输出进度报告
            results = [{"type": "tool_result", "tool_use_id": tc.id,
                        "content": "(已达最大迭代次数，工具未执行)"}
                       for tc in tool_calls]
            results.append({"type": "text",
                            "text": f"已达最大迭代次数 {MAX_ITERATIONS}。请停止调用工具，"
                                    "直接输出进度报告：1) 已完成什么 2) 卡在哪里 "
                                    "3) 下一步建议。"})
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": results})
            report = llm_create(
                model=MODEL, system=SYSTEM, messages=messages, max_tokens=4000,
            )
            for block in report.content:
                if getattr(block, "type", None) == "text":
                    print(block.text)
                    if first_text is None and block.text.strip():
                        first_text = block.text
            messages.append({"role": "assistant", "content": report.content})
            return _text_of(report), _starts_with_greeting(first_text)

        results = []
        for tc in tool_calls:
            if tc.name == "Task":
                print(f"\n> Task: {tc.input.get('description', '子任务')}")
            elif tc.name == "Skill":
                print(f"\n> 加载技能: {tc.input.get('skill', '?')}")
            else:
                print(f"\n> {tc.name}")
            output = execute_tool(tc.name, tc.input)
            if tc.name == "Skill":
                print(f"  技能已加载（{len(output)} 字符）")
            elif tc.name != "Task":
                preview = output[:200] + "..." if len(output) > 200 else output
                print(f"  {preview}")
            results.append({"type": "tool_result", "tool_use_id": tc.id,
                            "content": output})

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": results})


# =============================================================================
# 主 REPL（含问候语金丝雀检查）
# =============================================================================

def main():
    check_config()
    print(f"小兰 v0 —— ESP32 数字钢琴 agent - {WORKDIR}")
    print(f"模型: {MODEL} @ {BASE_URL}")
    print(f"技能: {', '.join(SKILLS.list_skills()) or '无'}")
    init_mcp()
    print(f"MCP 工具: {', '.join(sorted(MCP_CLIENTS)) or '无'}")
    print("输入 'exit' 退出。\n")

    history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() in ("exit", "quit", "q"):
            break

        history.append({"role": "user", "content": user_input})

        try:
            _, greeted = agent_loop(history)

            # 问候语金丝雀：本轮第一个文本块必须以固定问候语开头。
            # 缺失 → 判定上下文过长 → 压缩上下文 → 重试（最多 2 次）。
            retries = 0
            while not greeted and retries < 2:
                print("\n⚠ 回复缺少问候语 → 判定上下文过长，压缩后重试...")
                compress_context(history)
                _, greeted = agent_loop(history)
                retries += 1
            if not greeted:
                print("\n⚠ 压缩重试后仍无问候语，请人工检查。")
        except Exception as e:
            print(f"Error: {e}")

        print()


if __name__ == "__main__":
    main()
