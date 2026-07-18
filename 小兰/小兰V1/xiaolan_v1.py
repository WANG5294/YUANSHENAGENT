#!/usr/bin/env python3
"""小兰 v1 —— ESP32 单片机开发 agent（最小可实现版）

相对 v0 的变化：
  - 移除麦克风闭环（mic_check/record_audio/play_and_record/analyze_wav/
    compare_audio 不注册），只保留设备通道：编写 → 上传 → 运行 → 看串口输出
  - 移除子代理、TodoWrite、问候语金丝雀与上下文压缩（最小可实现）
  - 新增循环摘要：模型每轮回复第一段必须报告上一轮循环的工具/成败/耗时
    （轮次与秒数由本程序注入的【循环状态】提供，模型照抄不瞎猜）
  - 新增斜杠命令：
      /model  切换大模型（缺 API Key 时给出保存指引）
      /tool   查看当前可用工具（本地 + MCP，名称+功能）
      /skill  查看当前可用技能（名称+功能）
      /work   探测当前环境能做什么（串口/上传/烧录/麦克风等）
  - 技能改为硬件手册分块：pinmap / buzzer / led / keys / mcu / peripherals

运行：
  python3 xiaolan_v1.py     （自动切换到 piano_workflow/.venv 解释器；
                             .env 优先读本目录，其次沿用 小兰V0/.env）
"""

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path


def _bootstrap_interpreter():
    """缺依赖时原地 re-exec 到 piano_workflow 的 venv（判据是 sys.prefix）。"""
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


_bootstrap_interpreter()

from dotenv import load_dotenv

# =============================================================================
# 配置与模型预设
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]            # 小兰/小兰V1 → 项目根目录
load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(SCRIPT_DIR.parent / "小兰V0" / ".env")   # 沿用 v0 已存的 Key

WORKDIR = Path.cwd()
SKILLS_DIR = SCRIPT_DIR / "skills"
MAX_ITERATIONS = 50

# /model 可切换的预设。key_envs 按顺序取第一个存在的环境变量。
MODEL_PRESETS = {
    "kimi-k3": {
        "base_url": "https://api.moonshot.cn/anthropic",
        "key_envs": ["MOONSHOT_API_KEY", "ANTHROPIC_API_KEY"],
        "key_hint": "MOONSHOT_API_KEY（platform.moonshot.cn → API Keys 页面创建）",
    },
    "deepseek-chat": {
        "base_url": "https://api.deepseek.com/anthropic",
        "key_envs": ["DEEPSEEK_API_KEY"],
        "key_hint": "DEEPSEEK_API_KEY（platform.deepseek.com → API Keys 页面创建）",
    },
    "glm-4.6": {
        "base_url": "https://open.bigmodel.cn/api/anthropic",
        "key_envs": ["ZHIPU_API_KEY"],
        "key_hint": "ZHIPU_API_KEY（open.bigmodel.cn → API 管理页面创建）",
    },
}

MODEL = os.getenv("MODEL_NAME", "kimi-k3")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL",
                     MODEL_PRESETS.get(MODEL, {}).get("base_url",
                                                      "https://api.moonshot.cn/anthropic"))
API_KEY = None
_client = None

# Kimi K3 等思考模型的思考会吃掉 max_tokens 预算，agent 场景关闭思考
THINKING = {"type": "disabled"}


def preset_key(name: str):
    """按预设的 key_envs 顺序找 API Key，找不到返回 None。"""
    for env in MODEL_PRESETS.get(name, {}).get("key_envs", ["ANTHROPIC_API_KEY"]):
        val = os.getenv(env)
        if val and "sk-xxx" not in val and len(val) >= 20:
            return val
    return None


def key_guidance(name: str) -> str:
    hint = MODEL_PRESETS.get(name, {}).get("key_hint", "对应平台的 API Key")
    env_file = SCRIPT_DIR / ".env"
    return (f"模型 {name} 缺少 API Key。保存方法：\n"
            f"  1. 编辑 {env_file}（没有就 cp .env.example .env）\n"
            f"  2. 加一行：{hint.split('（')[0]}=你的Key\n"
            f"     获取途径：{hint}\n"
            f"  3. 保存后重新输入 /model 切换（无需重启）")


def apply_model(name: str) -> bool:
    """切换全局模型配置。成功 True；缺 Key 打印指引并返回 False。"""
    global MODEL, BASE_URL, API_KEY, _client
    load_dotenv(SCRIPT_DIR / ".env", override=True)   # 重读，用户可能刚存了 Key
    key = preset_key(name)
    if not key:
        print(key_guidance(name))
        return False
    MODEL = name
    BASE_URL = MODEL_PRESETS[name]["base_url"]
    API_KEY = key
    _client = None
    masked = key[:3] + "*" * 6 + key[-2:]
    print(f"已切换：{MODEL} @ {BASE_URL}（Key: {masked}）")
    return True


def get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(api_key=API_KEY, base_url=BASE_URL)
    return _client


def llm_create(**kwargs):
    return get_client().messages.create(thinking=THINKING, **kwargs)


# =============================================================================
# MCP 最小客户端（stdio JSON-RPC 2.0，同 v0）——排除麦克风/音频工具
# =============================================================================

VENV_PY = PROJECT_ROOT / "piano_workflow" / ".venv" / "bin" / "python"
if not VENV_PY.exists():
    VENV_PY = Path(sys.executable)
MCP_SERVERS = [
    {"name": "esp32-piano",
     "cmd": [str(VENV_PY), str(PROJECT_ROOT / "piano_workflow" / "esp32_piano_mcp.py")]},
]
# v1 不含麦克风闭环：这些工具即使服务器提供也不注册
MIC_TOOLS = {"mic_check", "record_audio", "play_and_record",
             "analyze_wav", "compare_audio"}


class MCPClient:
    def __init__(self, name: str, cmd: list, timeout: float = 180):
        self.name = name
        self.timeout = timeout
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self._next_id = 0
        self._queue = queue.Queue()
        threading.Thread(target=self._read_loop, daemon=True).start()
        self._request("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "xiaolan", "version": "1.0"}})
        self._notify("notifications/initialized")

    def _read_loop(self):
        for line in self.proc.stdout:
            line = line.strip()
            if line:
                try:
                    self._queue.put(json.loads(line))
                except json.JSONDecodeError:
                    pass
        self._queue.put(None)

    def _send(self, msg: dict):
        self.proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def _request(self, method: str, params: dict = None) -> dict:
        self._next_id += 1
        rid = self._next_id
        req = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            req["params"] = params
        self._send(req)
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
                continue
            if "error" in msg:
                raise RuntimeError(f"MCP 错误: {msg['error']}")
            return msg.get("result", {})

    def _notify(self, method: str, params: dict = None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)

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


MCP_CLIENTS = {}
MCP_TOOL_DEFS = []


def init_mcp():
    for cfg in MCP_SERVERS:
        try:
            client = MCPClient(cfg["name"], cfg["cmd"])
            tools = [t for t in client.list_tools() if t["name"] not in MIC_TOOLS]
            for t in tools:
                MCP_CLIENTS[t["name"]] = client
                MCP_TOOL_DEFS.append({
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("inputSchema",
                                          {"type": "object", "properties": {}})})
            print(f"MCP 服务器 {cfg['name']}: 注册 {len(tools)} 个工具"
                  f"（麦克风/音频闭环工具在 v1 中不启用）")
        except Exception as e:
            print(f"⚠ MCP 服务器 {cfg['name']} 启动失败: {e}（其工具不可用）")


# =============================================================================
# SkillLoader（SKILL.md：YAML frontmatter + 正文，按需注入）
# =============================================================================

class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills = {}
        if not skills_dir.exists():
            return
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if skill_dir.is_dir() and skill_md.exists():
                parsed = self.parse(skill_md)
                if parsed:
                    self.skills[parsed["name"]] = parsed

    def parse(self, path: Path):
        content = path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return None
        frontmatter, body = match.groups()
        meta = {}
        key = None
        for line in frontmatter.strip().split("\n"):
            if ":" in line and not line.startswith((" ", "\t")):
                key, value = line.split(":", 1)
                key = key.strip()
                meta[key] = value.strip().strip("\"'")
            elif key:                       # 折行的 description 续行
                meta[key] += " " + line.strip()
        if "name" not in meta or "description" not in meta:
            return None
        return {"name": meta["name"], "description": meta["description"],
                "body": body.strip()}

    def get_descriptions(self) -> str:
        if not self.skills:
            return "(无可用技能)"
        return "\n".join(f"- {n}: {s['description']}"
                         for n, s in self.skills.items())

    def get_content(self, name: str):
        skill = self.skills.get(name)
        if not skill:
            return None
        return f"# Skill: {skill['name']}\n\n{skill['body']}"


SKILLS = SkillLoader(SKILLS_DIR)

# =============================================================================
# System Prompt
# =============================================================================

SYSTEM = f"""你是小兰 v1 —— ESP32 单片机开发 agent，运行在 Ubuntu 24.04 虚拟机中，工作目录 {WORKDIR}。

【循环摘要 —— 最高优先级】你的每一轮回复，第一段必须是约 50 字的循环摘要，之后才是其他内容。
- 若上一条消息里有【循环状态】（记录了第 k 轮工具的成败与当前秒数），格式必须为：
  "第k+1轮循环输出结果：完成第k轮循环，成功/失败；第k轮使用了〈技能名，若有〉skill、〈工具名〉tool，做了〈一句话概括〉。正在进行第k+1轮循环，第N秒。"
  其中 k、成败、N 一律照抄【循环状态】给出的数字与结论，不得自行估计。
- 若没有【循环状态】（本任务首轮），则第一段为："第1轮循环：任务开始，第0秒。"

【工作范围】只处理与 ESP32 单片机相关的任务：编写/调试 MicroPython 程序、上传运行、串口日志分析等。无关请求礼貌拒绝。

【工作循环】理解需求 → 编写/修改代码 → 上传 → 运行 → 读串口输出 → 有问题修复重来，直到硬件验证通过。代码写完不算完成，硬件验证通过才算。一次只改一个变量。

【技能】涉及具体硬件模块（引脚、蜂鸣器、LED、按键、芯片约束、扩展外设）时，先用 Skill 工具加载对应技能，只加载和当前任务相关的分块：
{SKILLS.get_descriptions()}

【禁止的操作 —— 安全红线】
1. 禁止擦除 Flash（erase_flash）、刷写固件（esptool）
2. 禁止危险 shell 命令：rm -rf /、sudo、shutdown、reboot、mkfs、dd 写设备
3. 文件操作仅限当前工作目录内；串口仅限 /dev/ttyACM* 与 /dev/ttyUSB*
4. GPIO34/35 是输入专用引脚，禁止配置为输出
5. 本版本无麦克风/录音能力，不要尝试录音验证

【迭代限制】单个任务最多 {MAX_ITERATIONS} 轮工具调用，耗尽后输出进度报告（已完成什么、卡在哪里、下一步建议）。"""

# =============================================================================
# 工具定义与实现
# =============================================================================

BASE_TOOLS = [
    {"name": "bash", "description": "执行 shell 命令。",
     "input_schema": {"type": "object",
                      "properties": {"command": {"type": "string"}},
                      "required": ["command"]}},
    {"name": "read_file", "description": "读取文件内容。",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"},
                                     "limit": {"type": "integer"}},
                      "required": ["path"]}},
    {"name": "write_file", "description": "写入文件（覆盖）。",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"},
                                     "content": {"type": "string"}},
                      "required": ["path", "content"]}},
    {"name": "edit_file", "description": "精确替换文件中的文本。",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"},
                                     "old_text": {"type": "string"},
                                     "new_text": {"type": "string"}},
                      "required": ["path", "old_text", "new_text"]}},
    {"name": "Skill",
     "description": f"加载技能获得硬件分块知识。任务涉及对应模块时立即使用。\n\n可用技能：\n{SKILLS.get_descriptions()}",
     "input_schema": {"type": "object",
                      "properties": {"skill": {"type": "string"}},
                      "required": ["skill"]}},
]


def get_all_tools() -> list:
    return BASE_TOOLS + MCP_TOOL_DEFS


def safe_path(p: str) -> Path:
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


def run_skill(skill_name: str) -> str:
    content = SKILLS.get_content(skill_name)
    if content is None:
        available = ", ".join(SKILLS.skills) or "无"
        return f"Error: 未知技能 '{skill_name}'。可用: {available}"
    return f'<skill-loaded name="{skill_name}">\n{content}\n</skill-loaded>\n\n请遵循以上技能说明完成任务。'


def execute_tool(name: str, args: dict) -> str:
    if name == "bash":
        return run_bash(args["command"])
    if name == "read_file":
        return run_read(args["path"], args.get("limit"))
    if name == "write_file":
        return run_write(args["path"], args["content"])
    if name == "edit_file":
        return run_edit(args["path"], args["old_text"], args["new_text"])
    if name == "Skill":
        return run_skill(args["skill"])
    if name in MCP_CLIENTS:
        try:
            return MCP_CLIENTS[name].call_tool(name, args)
        except Exception as e:
            return f"Error: MCP 工具 {name} 调用失败: {e}"
    return f"Unknown tool: {name}"


# =============================================================================
# Agent 主循环（每轮注入【循环状态】，供模型输出循环摘要）
# =============================================================================

def agent_loop(messages: list):
    round_no = 0
    task_start = time.time()
    while True:
        response = llm_create(model=MODEL, system=SYSTEM, messages=messages,
                              tools=get_all_tools(), max_tokens=8000)
        for block in response.content:
            if getattr(block, "type", None) == "text" and block.text.strip():
                print(block.text)

        if response.stop_reason != "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            return

        round_no += 1
        tool_calls = [b for b in response.content if b.type == "tool_use"]

        if round_no >= MAX_ITERATIONS:
            results = [{"type": "tool_result", "tool_use_id": tc.id,
                        "content": "(已达最大迭代次数，工具未执行)"}
                       for tc in tool_calls]
            results.append({"type": "text",
                            "text": f"已达最大迭代次数 {MAX_ITERATIONS}。请停止调用工具，"
                                    "直接输出进度报告：1) 已完成什么 2) 卡在哪里 3) 下一步建议。"})
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": results})
            report = llm_create(model=MODEL, system=SYSTEM,
                                messages=messages, max_tokens=4000)
            for block in report.content:
                if getattr(block, "type", None) == "text":
                    print(block.text)
            messages.append({"role": "assistant", "content": report.content})
            return

        results = []
        used = []                             # [(工具名, 成功/失败, 概要)]
        for tc in tool_calls:
            label = f"Skill({tc.input.get('skill', '?')})" if tc.name == "Skill" else tc.name
            print(f"\n> {label}")
            output = execute_tool(tc.name, tc.input)
            ok = not output.startswith(("Error", "Unknown tool"))
            used.append((label, ok, output[:60].replace("\n", " ")))
            preview = output[:200] + "..." if len(output) > 200 else output
            print(f"  {preview}")
            results.append({"type": "tool_result", "tool_use_id": tc.id,
                            "content": output})

        elapsed = int(time.time() - task_start)
        detail = "；".join(f"{n}→{'成功' if ok else '失败'}（{brief}）"
                          for n, ok, brief in used)
        results.append({"type": "text",
                        "text": f"【循环状态】第 {round_no} 轮循环已完成：{detail}。"
                                f"当前任务计时第 {elapsed} 秒。"
                                f"现在开始第 {round_no + 1} 轮循环，"
                                f"请先按规定格式输出约 50 字的循环摘要。"})
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": results})


# =============================================================================
# 斜杠命令：/model /tool /skill /work
# =============================================================================

def cmd_model():
    print(f"当前模型: {MODEL} @ {BASE_URL}\n")
    names = list(MODEL_PRESETS)
    for i, n in enumerate(names, 1):
        mark = "✓ 已配置Key" if preset_key(n) else "✗ 缺Key"
        cur = "  ← 当前" if n == MODEL else ""
        print(f"  {i}. {n:<16} [{mark}]{cur}")
    print("\n输入编号或模型名切换（直接回车取消）：", end="", flush=True)
    try:
        choice = input().strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not choice:
        return
    if choice.isdigit() and 1 <= int(choice) <= len(names):
        choice = names[int(choice) - 1]
    if choice not in MODEL_PRESETS:
        print(f"未知模型 '{choice}'。可选: {', '.join(names)}")
        return
    apply_model(choice)


def cmd_tool():
    print("== 本地工具 ==")
    for t in BASE_TOOLS:
        print(f"  - {t['name']}: {t['description'].splitlines()[0]}")
    print("== MCP 工具 (esp32-piano) ==")
    if not MCP_TOOL_DEFS:
        print("  (无 —— MCP 服务器未启动)")
    for t in MCP_TOOL_DEFS:
        desc = t["description"].strip().splitlines()
        print(f"  - {t['name']}: {desc[0] if desc else '(无描述)'}")
    print("（麦克风/音频闭环工具在 v1 中不启用）")


def cmd_skill():
    print("== 可用技能（Skill 工具按需加载）==")
    if not SKILLS.skills:
        print("  (无)")
    for n, s in SKILLS.skills.items():
        print(f"  - {n}: {s['description']}")


def cmd_work():
    print("== 当前环境能力探测 ==")
    import glob
    ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    print(f"  串口设备: {'✓ ' + ', '.join(ports) if ports else '✗ 未发现（检查USB线/dialout权限）'}")
    mp = shutil.which("mpremote")
    print(f"  mpremote: {'✓ ' + mp if mp else '✗ 未安装（pip install mpremote）'}")
    board = False
    if ports and mp:
        try:
            r = subprocess.run(["mpremote", "connect", ports[0], "exec", "print('pong')"],
                               capture_output=True, text=True, timeout=8)
            board = "pong" in r.stdout
        except Exception:
            pass
    print(f"  板子 REPL 响应: {'✓ 可交互' if board else '✗ 无响应（板子未接/被程序占用）'}")
    ok = "✓ 可用" if board else "✗ 依赖上面三项"
    print(f"  上传/运行/删除板上文件: {ok}")
    print(f"  技能知识库: {'✓ ' + str(len(SKILLS.skills)) + ' 个分块' if SKILLS.skills else '✗ 无'}")
    print(f"  大模型 API: {'✓ ' + MODEL if preset_key(MODEL) else '✗ 缺 Key（输入 /model 看指引）'}")
    print("  固件烧录 (esptool/erase_flash): ✗ 安全红线，永久禁止")
    print("  麦克风闭环验证: ✗ v1 不包含此功能（需要请用 小兰V0）")


COMMANDS = {"/model": cmd_model, "/tool": cmd_tool,
            "/skill": cmd_skill, "/work": cmd_work}


# =============================================================================
# 主 REPL
# =============================================================================

def main():
    print(f"小兰 v1 —— ESP32 单片机 agent（最小版） - {WORKDIR}")
    if not apply_model(MODEL):
        print("（暂无可用 Key，仅 /tool /skill /work 可用；存好 Key 后 /model 激活）")
    print(f"技能: {', '.join(SKILLS.skills) or '无'}")
    init_mcp()
    print("命令: /model 切换模型 | /tool 看工具 | /skill 看技能 | /work 看能力 | exit 退出\n")

    history = []
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            break
        if user_input in COMMANDS:
            COMMANDS[user_input]()
            print()
            continue
        if user_input.startswith("/"):
            print(f"未知命令 {user_input}。可用: {', '.join(COMMANDS)}\n")
            continue
        if not API_KEY:
            print(key_guidance(MODEL) + "\n")
            continue

        history.append({"role": "user", "content": user_input})
        try:
            agent_loop(history)
        except Exception as e:
            print(f"Error: {e}")
        print()


if __name__ == "__main__":
    main()
