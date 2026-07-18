#!/usr/bin/env python3
"""小红 v3 —— ESP32 单片机开发 agent

在小兰 v2 核心之上的 v3 增量（详见 readme_v3.md）：
  - system prompt 新增【工具总览】：主要功能精简版常驻（详细参数仍在
    tool prompt），模型不用翻工具列表就知道能力边界
  - system prompt 新增【当前接线】：wiring.md 的内容常驻注入，接线事实
    （外接了什么、哪些脚被占）每轮都在模型眼前
  - 输入栏分流：硬件说明文档与用户任务分开输入——
      /doc <md路径>  导入新硬件说明文档（须符合 SKILL.md 格式：
                     frontmatter 含 name/description），校验后装入
                     skills/ 立即生效，换硬件零改代码
      /wiring        查看当前接线（编辑 wiring.md 后下个任务生效）
  - 名称由"小兰"改为"小红"

继承 v2 的核心：agent 循环与循环摘要、主线任务 TodoWrite（烧录卡点+
自动备份）、实机验证红线、files/ 每任务一个项目文件夹、经验提取需用户
确认、/model /tool /skill /work。

运行：
  python3 xiaohong_v3.py    （自动切换 piano_workflow/.venv 解释器；
                             .env 优先本目录，其次沿用 小兰/小兰V0/.env）
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
from datetime import datetime
from pathlib import Path


def _bootstrap_interpreter():
    """缺依赖时原地 re-exec 到可用的 venv（判据是 sys.prefix）。
    优先本目录 .venv（npm 安装场景，由 bin/xiaohong.js 创建），
    其次开发环境的 piano_workflow/.venv。"""
    try:
        import anthropic  # noqa: F401
        import dotenv     # noqa: F401
        return
    except ModuleNotFoundError:
        script = Path(__file__).resolve()
        for venv_dir in (script.parent / ".venv",
                         script.parents[1] / "piano_workflow" / ".venv"):
            venv_py = venv_dir / "bin" / "python"
            if venv_py.exists() and Path(sys.prefix).resolve() != venv_dir.resolve():
                os.execv(str(venv_py), [str(venv_py), str(script), *sys.argv[1:]])
        sys.exit("缺少 Python 依赖。请通过 npm 启动器运行（xiaohong 命令），"
                 "或手动: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")


_bootstrap_interpreter()

from dotenv import load_dotenv

# =============================================================================
# 配置与模型预设
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent                # xiaohong/ → 项目根目录
load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(PROJECT_ROOT / "小兰" / "小兰V0" / ".env")   # 沿用 v0 已存的 Key

WORKDIR = Path.cwd()
SKILLS_DIR = SCRIPT_DIR / "skills"
FILES_DIR = SCRIPT_DIR / "files"        # 与 skills 平行；每个任务一个项目文件夹
WIRING_FILE = SCRIPT_DIR / "wiring.md"  # 当前接线事实，常驻 system prompt
CURRENT_TASK_DIR = None                 # 当前任务的项目文件夹（main 里逐任务设置）
MAX_ITERATIONS = 50
SUMMARY_LIMIT = 100                             # 循环摘要字数上限


def read_wiring() -> str:
    try:
        return WIRING_FILE.read_text().strip()
    except OSError:
        return "（wiring.md 不存在——接线情况未知，涉及外接硬件时先向用户确认）"

MODEL_PRESETS = {
    "kimi-k3": {
        "base_url": "https://api.moonshot.cn/anthropic",
        "key_envs": ["MOONSHOT_API_KEY", "ANTHROPIC_API_KEY"],
        "key_hint": "MOONSHOT_API_KEY（platform.moonshot.cn → API Keys 页面创建）",
    },
    "deepseek-v4-pro": {
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
THINKING = {"type": "disabled"}     # 思考会吃掉 max_tokens 预算，agent 场景关闭


def preset_key(name: str):
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
    global MODEL, BASE_URL, API_KEY, _client
    load_dotenv(SCRIPT_DIR / ".env", override=True)
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
# MCP 最小客户端（stdio JSON-RPC 2.0）—— v2 注册全部工具，含麦克风闭环
# =============================================================================

# MCP 服务器脚本与解释器：优先包内自带（npm 安装场景），其次开发环境路径
_MCP_PY = SCRIPT_DIR / "esp32_piano_mcp.py"
if not _MCP_PY.exists():
    _MCP_PY = PROJECT_ROOT / "piano_workflow" / "esp32_piano_mcp.py"
VENV_PY = SCRIPT_DIR / ".venv" / "bin" / "python"
if not VENV_PY.exists():
    VENV_PY = PROJECT_ROOT / "piano_workflow" / ".venv" / "bin" / "python"
if not VENV_PY.exists():
    VENV_PY = Path(sys.executable)
MCP_SERVERS = [
    {"name": "esp32-piano", "cmd": [str(VENV_PY), str(_MCP_PY)]},
]


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
            "clientInfo": {"name": "xiaohong", "version": "3.0"}})
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
            tools = client.list_tools()
            for t in tools:
                MCP_CLIENTS[t["name"]] = client
                MCP_TOOL_DEFS.append({
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("inputSchema",
                                          {"type": "object", "properties": {}})})
            print(f"MCP 服务器 {cfg['name']}: 注册 {len(tools)} 个工具（含麦克风闭环）")
        except Exception as e:
            print(f"⚠ MCP 服务器 {cfg['name']} 启动失败: {e}（其工具不可用）")


# =============================================================================
# SkillLoader（可重载：任务结束提取的新经验立即可用）
# =============================================================================

class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills = {}
        self.reload()

    def reload(self):
        self.skills = {}
        if not self.skills_dir.exists():
            return
        for skill_dir in sorted(self.skills_dir.iterdir()):
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
            elif key:
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
# TodoManager（主线任务：编写代码 → 烧录代码 → 测试代码 → 完成）
# =============================================================================

MAINLINE = ["编写代码", "烧录代码", "测试代码", "完成"]


class TodoManager:
    """记住用户原始需求（goal），维护主线任务清单。
    每个新任务自动初始化四个主线步骤；模型用 TodoWrite 更新进度、
    也可插入子步骤（总数 ≤20，同时只能一个 in_progress）。"""

    def __init__(self):
        self.goal = ""
        self.items = []
        self.deployed_main = False

    def start(self, goal: str):
        self.goal = goal
        self.deployed_main = False        # 本任务是否已把程序部署为板上 main.py
        self.items = [{"content": s, "status": "pending", "activeForm": s}
                      for s in MAINLINE]

    def update(self, items: list) -> str:
        validated = []
        in_progress = 0
        for i, item in enumerate(items):
            content = str(item.get("content", "")).strip()
            status = str(item.get("status", "pending")).lower()
            active = str(item.get("activeForm", content)).strip()
            if not content:
                raise ValueError(f"第 {i} 项: content 必填")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"第 {i} 项: status 非法")
            if status == "in_progress":
                in_progress += 1
            validated.append({"content": content, "status": status,
                              "activeForm": active})
        if in_progress > 1:
            raise ValueError("同时只能有一个任务 in_progress")
        # 卡点：没把程序部署为板上 main.py，不允许宣称"烧录"完成
        for v in validated:
            if ("烧录" in v["content"] and v["status"] == "completed"
                    and not self.deployed_main):
                raise ValueError(
                    "烧录代码不能标记完成：本任务还没有把程序上传为板上的 main.py"
                    "（upload 时设 remote_name='main.py'，开机自启才算烧录；"
                    "仅上传为其他文件名只是拷贝模块，不算烧录）")
        missing = [s for s in MAINLINE
                   if not any(s in v["content"] for v in validated)]
        if missing:
            raise ValueError(f"主线步骤不可删除，缺少: {', '.join(missing)}")
        self.items = validated[:20]
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "（无任务）"
        marks = {"completed": "[x]", "in_progress": "[>]", "pending": "[ ]"}
        lines = [f"{marks[t['status']]} {t['content']}" for t in self.items]
        done = sum(1 for t in self.items if t["status"] == "completed")
        return "\n".join(lines) + f"\n({done}/{len(self.items)} 完成)"


TODO = TodoManager()

# =============================================================================
# System Prompt（动态生成：技能列表会随经验提取增长）
# =============================================================================


def build_system() -> str:
    return f"""你是小红 v3 —— ESP32 单片机开发 agent，运行在 Ubuntu 24.04 虚拟机中，工作目录 {WORKDIR}。

【循环摘要 —— 最高优先级】你的每一轮回复，第一段必须是循环摘要（自然语言，不超过 {SUMMARY_LIMIT} 字），之后才是其他内容。
- 若上一条消息里有【循环状态】（记录第 k 轮工具成败与当前秒数），格式：
  "第k+1轮循环输出结果：完成第k轮循环，成功/失败；第k轮使用了〈技能名，若有〉skill、〈工具名〉tool，做了〈概括〉。正在进行第k+1轮循环，第N秒。"
  其中 k、成败、N 照抄【循环状态】，不得自行估计。提到工具时必须写明类别（照抄【循环状态】里的标注）：MCP 工具写成如 "upload（mcp）"，本地工具写成如 "write_file（本地）"。
- 摘要**只总结上一轮做了什么**：加载技能时只报技能名，**严禁复述技能正文内容**；工具输出只概括结论。
- 若没有【循环状态】（本任务首轮），第一段为："第1轮循环：任务开始，第0秒。"

【工作范围】只处理与 ESP32 单片机相关的任务：编写/调试 MicroPython 程序、上传运行、串口日志分析、麦克风闭环验证实机声音。无关请求礼貌拒绝。

【用户输入约定】用户只描述**要完成的目标**（如"让绿灯闪三下"、"按键播放一个音"），不会也不需要写操作指示。收到目标后你自动执行完整主线，绝不反问"要不要烧录/要不要运行"。

【主线任务】每个任务固定走四步主线，用 TodoWrite 工具维护进度（开工把当前步骤设 in_progress，做完设 completed，可在主线间插入子步骤但四个主线步骤不可删除）：
1. 编写代码 —— 在主机上写好 MicroPython 程序
2. 烧录代码 —— 把程序上传为板上的 **main.py**（upload 时设 remote_name='main.py'），让它成为开机自启的主程序，这才叫烧录；仅上传为其他文件名只是拷贝模块，不算烧录，也无法把该步标记完成。覆盖前系统会自动把板上原 main.py 备份到 backups/，无需你操作
3. 测试代码 —— 验证**烧录进去的 main.py 本体**能在板上跑出预期效果：用 repl_exec 执行 exec(open('main.py').read())（或带超时的 run_script）读输出；有声音时加麦克风闭环（play_and_record + analyze_wav）。只 import 某个模块名不算烧录后的验证。若 main.py 含 while True 主循环，验证启动段后超时软复位属正常
4. 完成 —— 硬件验证通过，向用户汇报结果（包括备份文件位置）
代码写完不算完成，硬件验证通过才算。一次只改一个变量。每轮【循环状态】会带上用户原始需求和主线进度，防止走偏——始终对照原始需求做事。

【工具总览】主要功能精简版（详细参数以工具定义为准）：
- 本地：bash（shell）/ read_file / write_file / edit_file（文件自动落任务文件夹）/ Skill（按需加载知识）/ TodoWrite（主线进度）
- MCP·设备通道：list_ports（列串口）/ upload（传文件，目标 main.py 才算烧录）/ run_script（带超时运行）/ repl_exec（板上执行代码）/ device_ls / device_rm（板上文件管理）/ soft_reset（打断死循环）
- MCP·音频闭环：mic_check（录音通道自检）/ record_audio / play_and_record（软触发播放并录音）/ analyze_wav（基频/包络/哒声）/ compare_audio（录音 vs 预览对比）

【当前接线】以下是用户维护的接线记录（wiring.md），做任何硬件操作前先对照，严禁与之矛盾的假设。记录用简写：Gxx = GPIOxx（如 "G25连G25"、"G05,G12,G14,G18分别连接发光二极管连GND"）；"没有插线" = 板子仅 USB 供电，排针上没有任何外接（板载蜂鸣器/LED/按键等原生外设不受影响，仍可用）：
{read_wiring()}

【技能】涉及具体硬件模块或历史经验时，先用 Skill 工具加载对应技能，只加载与当前任务相关的分块（exp- 开头的是从过往任务提取的经验）：
{SKILLS.get_descriptions()}

【文件存放】本任务专属项目文件夹：{CURRENT_TASK_DIR}
你生成的一切文件（MicroPython 程序、录音 WAV、preview、分析产物）都必须放进该文件夹：write_file / 录音 out_path 用**不带斜杠的纯文件名**即可，系统会自动落到该文件夹；读取项目已有文件（如 KEY.py）仍可用原路径。禁止往项目根目录散落文件。任务结束后流程日志与报告也归档进同一文件夹。

【实机验证红线】闭环判定只认数字，禁止模糊话充当结论：
1. 录音有效性：峰值必须 ≥ 5×噪声底（以本次 mic_check 的 RMS 为准）。达不到 = 闭环无效 = 验证失败；应把麦克风凑近喇叭、加大音量重录，仍不行就如实报告"实机验证失败"。**严禁**用静态代码检查、乐理推算等替代实机录音宣布通过
2. 响度/包络类需求：必须先在主机生成 preview WAV，再用 compare_audio 对比录音，包络相关系数 ≥0.8 才算通过；不达标 = 不合格，回改代码重来
3. 汇报必须引用具体指标（相关系数、音分偏差、峰值/噪声底比值），"确认发声""包络前大后小"之类描述不构成合格结论

【禁止的操作 —— 安全红线】
1. 禁止擦除 Flash（erase_flash）、刷写固件（esptool）
2. 禁止危险 shell 命令：rm -rf /、sudo、shutdown、reboot、mkfs、dd 写设备
3. 文件操作仅限当前工作目录内；串口仅限 /dev/ttyACM* 与 /dev/ttyUSB*
4. GPIO34/35 是输入专用引脚，禁止配置为输出

【迭代限制】单个任务最多 {MAX_ITERATIONS} 轮工具调用，耗尽后输出进度报告（已完成什么、卡在哪里、下一步建议）。"""


# =============================================================================
# 工具定义与实现
# =============================================================================


def base_tools() -> list:
    return [
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
         "description": f"加载技能获得硬件分块知识或历史经验。任务匹配时立即使用。\n\n可用技能：\n{SKILLS.get_descriptions()}",
         "input_schema": {"type": "object",
                          "properties": {"skill": {"type": "string"}},
                          "required": ["skill"]}},
        {"name": "TodoWrite",
         "description": "更新主线任务清单（提交完整清单）。四个主线步骤（编写代码/烧录代码/测试代码/完成）不可删除，可插入子步骤。",
         "input_schema": {"type": "object",
                          "properties": {"items": {
                              "type": "array",
                              "items": {"type": "object",
                                        "properties": {
                                            "content": {"type": "string"},
                                            "status": {"type": "string",
                                                       "enum": ["pending", "in_progress", "completed"]},
                                            "activeForm": {"type": "string"}},
                                        "required": ["content", "status"]}}},
                          "required": ["items"]}},
    ]


def get_all_tools() -> list:
    return base_tools() + MCP_TOOL_DEFS


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"路径越出工作目录: {p}")
    return path


def task_file(p: str, for_write: bool) -> str:
    """把不带路径分隔符的纯文件名定位到当前任务文件夹。

    写入：纯文件名一律落到任务文件夹；
    读取：任务文件夹里有就用它，没有则回落原路径（项目已有文件）。"""
    if CURRENT_TASK_DIR is None or "/" in p or p.startswith("."):
        return p
    cand = CURRENT_TASK_DIR / p
    if for_write or cand.exists():
        return str(cand)
    return p


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


def _backup_board_main() -> str:
    """覆盖板上 main.py 前，把原 main.py 自动备份到主机 backups/。"""
    backups = WORKDIR / "backups"
    backups.mkdir(exist_ok=True)
    dest = backups / f"main_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    try:
        r = subprocess.run(
            ["mpremote", "connect", "/dev/ttyACM0", "cp", ":main.py", str(dest)],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            return f"（已自动备份板上原 main.py → {dest.relative_to(WORKDIR)}）"
    except Exception:
        pass
    if dest.exists():
        dest.unlink()
    return "（板上无 main.py 或备份失败，未备份）"


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
        return run_read(task_file(args["path"], False), args.get("limit"))
    if name == "write_file":
        return run_write(task_file(args["path"], True), args["content"])
    if name == "edit_file":
        return run_edit(task_file(args["path"], False),
                        args["old_text"], args["new_text"])
    if name == "Skill":
        return run_skill(args["skill"])
    if name == "TodoWrite":
        try:
            return TODO.update(args["items"])
        except Exception as e:
            return f"Error: {e}"
    if name == "upload" and name in MCP_CLIENTS:
        dest = (args.get("remote_name") or "").strip() \
            or Path(args.get("local_path", "")).name
        note = ""
        if dest == "main.py":
            note = "\n" + _backup_board_main()     # 覆盖前先备份原 main.py
        try:
            out = MCP_CLIENTS[name].call_tool(name, args)
        except Exception as e:
            return f"Error: MCP 工具 {name} 调用失败: {e}"
        if dest == "main.py" and not out.startswith("Error"):
            TODO.deployed_main = True
        return out + note
    if name in MCP_CLIENTS:
        # 录音输出、脚本/上传的本地路径同样定位到当前任务文件夹
        for key, for_write in (("out_path", True), ("local_path", False),
                               ("path", False)):
            if isinstance(args.get(key), str):
                args[key] = task_file(args[key], for_write)
        try:
            return MCP_CLIENTS[name].call_tool(name, args)
        except Exception as e:
            return f"Error: MCP 工具 {name} 调用失败: {e}"
    return f"Unknown tool: {name}"


# =============================================================================
# Agent 主循环（注入【循环状态】；Skill 只报名称不带正文）
# =============================================================================


def _text_of(response) -> str:
    return "".join(b.text for b in response.content
                   if getattr(b, "type", None) == "text")


def agent_loop(messages: list, run_log: dict):
    """run_log 收集本任务流程：rounds / final_text / elapsed，供归档。"""
    SKILLS.reload()                 # 对话中新写入的经验技能即时可见
    system = build_system()
    tools = get_all_tools()
    round_no = 0
    task_start = time.time()
    while True:
        response = llm_create(model=MODEL, system=system, messages=messages,
                              tools=tools, max_tokens=8000)

        # 用户端输出结构：中间轮只显示循环摘要一行；最终轮显示完整汇报。
        # 工具调用明细、中间盘算不上屏（完整内容仍在上下文与归档里）。
        if response.stop_reason != "tool_use":
            for block in response.content:
                if getattr(block, "type", None) == "text" and block.text.strip():
                    print(block.text)
            messages.append({"role": "assistant", "content": response.content})
            run_log["final_text"] = _text_of(response)
            run_log["elapsed"] = int(time.time() - task_start)
            return

        text = _text_of(response).strip()
        if text:
            summary = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
            print(summary)

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
            report = llm_create(model=MODEL, system=system,
                                messages=messages, max_tokens=4000)
            for block in report.content:
                if getattr(block, "type", None) == "text":
                    print(block.text)
            messages.append({"role": "assistant", "content": report.content})
            run_log["final_text"] = _text_of(report)
            run_log["elapsed"] = int(time.time() - task_start)
            run_log["hit_limit"] = True
            return

        results = []
        used = []                             # [(标签, 类别, 成功?, 概要)]
        for tc in tool_calls:
            kind = "MCP" if tc.name in MCP_CLIENTS else "本地"
            if tc.name == "Skill":
                label = f"Skill({tc.input.get('skill', '?')})"
            else:
                label = tc.name
            output = execute_tool(tc.name, tc.input)     # 输出内容不上屏
            ok = not output.startswith(("Error", "Unknown tool"))
            # Skill 的输出是技能正文：循环状态里只报名称，严禁把正文带进摘要
            if tc.name == "Skill":
                brief = "技能说明已注入（正文不进摘要）" if ok else output[:80]
            else:
                brief = output[:80].replace("\n", " ")
            used.append((label, kind, ok, brief))
            results.append({"type": "tool_result", "tool_use_id": tc.id,
                            "content": output})

        # 每轮工具调用情况上屏，MCP 工具明确标注
        print("  └ 第%d轮调用: %s" % (round_no, "，".join(
            f"[{kind}]{label}{'✓' if ok else '✗失败'}"
            for label, kind, ok, _ in used)))

        elapsed = int(time.time() - task_start)
        run_log["rounds"].append(
            {"round": round_no, "elapsed_s": elapsed,
             "tools": [{"tool": n, "kind": k, "ok": ok, "brief": b}
                       for n, k, ok, b in used]})
        detail = "；".join(f"{n}（{k}工具）→{'成功' if ok else '失败'}（{brief}）"
                          for n, k, ok, brief in used)
        todo_line = TODO.render().replace("\n", " ")
        results.append({"type": "text",
                        "text": f"【循环状态】第 {round_no} 轮循环已完成：{detail}。"
                                f"当前任务计时第 {elapsed} 秒。\n"
                                f"【主线任务】用户原始需求：{TODO.goal}\n"
                                f"进度：{todo_line}\n"
                                f"现在开始第 {round_no + 1} 轮循环，请先输出不超过 "
                                f"{SUMMARY_LIMIT} 字的循环摘要（只总结上一轮，"
                                f"不复述技能正文），然后对照原始需求与主线进度继续。"})
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": results})


# =============================================================================
# 任务归档 + 经验提取为 skill
# =============================================================================


def _serialize_content(content):
    """assistant 消息里的 anthropic 对象 → 可 JSON 化的 dict。"""
    if isinstance(content, str):
        return content
    out = []
    for b in content:
        if isinstance(b, dict):
            out.append(b)
        elif hasattr(b, "model_dump"):
            out.append(b.model_dump())
        else:
            out.append(str(b))
    return out


def render_flow_md(user_input: str, run_log: dict) -> str:
    lines = [f"# 任务流程记录",
             f"",
             f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             f"- 模型：{MODEL}",
             f"- 用户需求：{user_input}",
             f"- 总耗时：{run_log.get('elapsed', '?')} 秒，"
             f"共 {len(run_log['rounds'])} 轮工具调用"
             + ("（达到迭代上限）" if run_log.get("hit_limit") else ""),
             f"",
             f"## 逐轮流程", ""]
    if not run_log["rounds"]:
        lines.append("（本任务未调用工具，直接回答）")
    for r in run_log["rounds"]:
        lines.append(f"### 第 {r['round']} 轮（第 {r['elapsed_s']} 秒）")
        for t in r["tools"]:
            mark = "✓" if t["ok"] else "✗"
            lines.append(f"- {mark} {t['tool']}：{t['brief']}")
        lines.append("")
    lines += ["## 主线任务最终状态", "", "```", TODO.render(), "```", "",
              "## 最终回复", "", run_log.get("final_text", "(无)")]
    return "\n".join(lines)


EXTRACT_SYSTEM = """你是经验提取器。阅读一次 ESP32 单片机 agent 的任务流程记录，判断其中是否有值得沉淀为技能的**特殊经验**——即"遇到某种情况应该怎么做"的可复用结论（如：某种报错的真实原因与解法、某个工具的正确用法、某类硬件现象的排查顺序）。

只提取满足全部条件的经验：1) 流程中真实发生过；2) 下次遇到同类情况能直接复用；3) 不是常识、不是现有技能已覆盖的内容。

有则输出严格 JSON（不要代码块包裹）：
{"name": "exp-英文短横线小写名", "description": "一句话：什么情况下加载本技能", "body": "Markdown 正文：现象 → 原因 → 应对步骤，控制在 300 字内"}

无则只输出：NONE"""


def _save_exp_skill(name: str, desc: str, body: str, source: str):
    skill_dir = SKILLS_DIR / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {desc}\n---\n\n{body}\n"
        f"\n> 来源：{source} 任务提取，已经用户确认\n")
    SKILLS.reload()                 # 下一个任务立即可用


def extract_skill(flow_md: str, run_dir: Path):
    """从流程记录提取经验技能，保存前需用户确认。

    返回 (结果说明, pending_context)：pending_context 非空表示用户选择
    "保留上下文继续对话修改"，将拼进下一轮用户消息。"""
    try:
        existing = "\n现有技能（勿重复提取）：\n" + SKILLS.get_descriptions()
        resp = llm_create(model=MODEL, max_tokens=1500, system=EXTRACT_SYSTEM,
                          messages=[{"role": "user",
                                     "content": flow_md[:8000] + existing}])
        raw = _text_of(resp).strip()
    except Exception as e:
        note = f"经验提取调用失败：{e}"
        (run_dir / "经验提取.md").write_text(note)
        return note, None

    if raw.upper().startswith("NONE"):
        (run_dir / "经验提取.md").write_text("本轮无值得沉淀的特殊经验。")
        return "本轮无特殊经验可提取", None

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else None
        name = data["name"].strip()
        desc = data["description"].strip()
        body = data["body"].strip()
        assert re.fullmatch(r"exp-[a-z0-9-]{3,40}", name)
    except Exception:
        note = f"提取输出无法解析，原文已存档：\n\n{raw}"
        (run_dir / "经验提取.md").write_text(note)
        return "经验提取输出无法解析（原文见归档）", None

    candidate = f"名称：{name}\n适用：{desc}\n正文：\n{body}"

    # ---- 用户确认步骤 ----
    print(f"\n📝 提取到候选经验：\n  名称：{name}\n  适用：{desc}\n"
          f"  ---- 正文 ----\n{body}\n  --------------")
    try:
        ans = input("确认保存该经验为技能？[y=保存 / n=不保存]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"                   # 无交互环境默认不保存
    if ans in ("y", "yes", "是"):
        _save_exp_skill(name, desc, body, run_dir.name)
        (run_dir / "经验提取.md").write_text(
            f"已提取技能（用户确认保存） **{name}**：{desc}\n\n"
            f"正文见 skills/{name}/SKILL.md")
        return f"已保存经验技能：{name}（{desc}）", None

    try:
        ans2 = input("是否保留本轮上下文历史，继续对话修改（程序或该经验）？"
                     "[y=继续对话 / n=放弃保存]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans2 = "n"
    if ans2 in ("y", "yes", "是"):
        (run_dir / "经验提取.md").write_text(
            f"候选经验用户未确认，转入对话修改：\n\n{candidate}")
        pending = (
            "【候选经验待修改】用户对下面这条自动提取的经验暂不确认，"
            "选择在原有记忆基础上继续多轮对话（可能要求进一步修改程序，"
            "或修改这条经验本身）。之后若用户表示满意并要求保存经验，"
            f"用 write_file 将修改后的经验写入 "
            f"{SKILLS_DIR}/<名称>/SKILL.md（保留 name/description "
            f"frontmatter 格式）。\n{candidate}")
        return "候选经验未保存，已带入上下文，可继续对话修改", pending

    (run_dir / "经验提取.md").write_text(
        f"候选经验用户拒绝保存：\n\n{candidate}")
    return "候选经验未保存（用户不确认）", None


def new_task_dir(user_input: str) -> Path:
    """每个新任务在 files/ 下开一个专属项目文件夹。"""
    slug = re.sub(r"[^\w一-鿿]+", "-", user_input)[:24].strip("-") or "task"
    task_dir = FILES_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slug}"
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def archive_run(user_input: str, run_log: dict, messages: list,
                task_dir: Path) -> Path:
    """日志与报告归档进本任务的项目文件夹（与产出文件放在一起）。"""
    flow_md = render_flow_md(user_input, run_log)
    (task_dir / "流程.md").write_text(flow_md)
    transcript = [{"role": m["role"], "content": _serialize_content(m["content"])}
                  for m in messages]
    (task_dir / "transcript.json").write_text(
        json.dumps(transcript, ensure_ascii=False, indent=1, default=str))
    return task_dir


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
    for t in base_tools():
        print(f"  - [本地] {t['name']}: {t['description'].splitlines()[0]}")
    print("== MCP 工具 (esp32-piano 服务器) ==")
    if not MCP_TOOL_DEFS:
        print("  (无 —— MCP 服务器未启动)")
    for t in MCP_TOOL_DEFS:
        desc = t["description"].strip().splitlines()
        print(f"  - [MCP] {t['name']}: {desc[0] if desc else '(无描述)'}")


def cmd_skill():
    print("== 可用技能（Skill 工具按需加载；exp- 开头为自动提取的经验）==")
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
    print(f"  上传/运行/删除板上文件: {'✓ 可用' if board else '✗ 依赖上面三项'}")
    mic = "✗ 探测失败"
    if "mic_check" in MCP_CLIENTS:
        try:
            out = MCP_CLIENTS["mic_check"].call_tool("mic_check", {})
            mic = ("✓ " + out.splitlines()[0]) if out.startswith("麦克风正常") \
                else "✗ 录到全零（VirtualBox 设备→音频→勾选音频输入）"
        except Exception as e:
            mic = f"✗ {e}"
    else:
        mic = "✗ MCP 工具未注册"
    print(f"  麦克风闭环: {mic}")
    print(f"  技能知识库: {'✓ ' + str(len(SKILLS.skills)) + ' 个分块' if SKILLS.skills else '✗ 无'}")
    print(f"  任务文件夹: ✓ {FILES_DIR}（每任务一个项目文件夹，产出+日志+报告同放）")
    print(f"  大模型 API: {'✓ ' + MODEL if preset_key(MODEL) else '✗ 缺 Key（输入 /model 看指引）'}")
    print("  固件烧录 (esptool/erase_flash): ✗ 安全红线，永久禁止")


def cmd_wiring():
    print(f"== 当前接线（{WIRING_FILE}）==")
    print(read_wiring())
    print("修改方法：直接编辑该文件（如 nano wiring.md），下一个任务的"
          " system prompt 自动更新，无需重启。")


def cmd_doc(arg: str):
    """导入硬件说明文档为技能。文档须符合 SKILL.md 格式：
    frontmatter 含 name（kebab-case）与 description（何时加载）。"""
    path = Path(arg.strip()).expanduser()
    if not arg.strip():
        print("用法：/doc <硬件说明md路径>\n"
              "文档格式要求（缺一不可）：\n"
              "  ---\n  name: 短横线小写英文名\n"
              "  description: 一句话说明什么任务该加载本技能\n"
              "  ---\n  正文（Markdown）")
        return
    if not path.exists():
        print(f"文件不存在: {path}")
        return
    parsed = SKILLS.parse(path)
    if parsed is None:
        print(f"格式不合规：{path.name} 缺少 frontmatter 或 name/description。\n"
              "要求开头为：\n  ---\n  name: xxx\n  description: xxx\n  ---")
        return
    name = parsed["name"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", name):
        print(f"name 不合规：'{name}'（需小写字母/数字/短横线）")
        return
    dest = SKILLS_DIR / name / "SKILL.md"
    if dest.exists():
        print(f"技能 '{name}' 已存在，将覆盖更新。")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, dest)
    SKILLS.reload()
    print(f"✅ 已导入技能 '{name}'：{parsed['description']}\n"
          f"   存放于 {dest}，立即生效（/skill 可查看）。")


COMMANDS = {"/model": cmd_model, "/tool": cmd_tool,
            "/skill": cmd_skill, "/work": cmd_work,
            "/wiring": cmd_wiring}


# =============================================================================
# 主 REPL
# =============================================================================


def main():
    print(f"小红 v3 —— ESP32 单片机 agent - {WORKDIR}")
    if not apply_model(MODEL):
        print("（暂无可用 Key，仅斜杠命令可用；存好 Key 后 /model 激活）")
    print(f"技能: {', '.join(SKILLS.skills) or '无'}")
    init_mcp()
    print("命令: /model 切换模型 | /tool 看工具 | /skill 看技能 | /work 看能力 | "
          "/wiring 看接线 | /doc <md> 导入硬件文档 | exit 退出\n")

    history = []
    pending_context = None          # 用户选"继续对话修改"时的候选经验上下文
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
        if user_input == "/doc" or user_input.startswith("/doc "):
            cmd_doc(user_input[4:])
            print()
            continue
        if user_input.startswith("/"):
            print(f"未知命令 {user_input}。可用: "
                  f"{', '.join(list(COMMANDS) + ['/doc <md路径>'])}\n")
            continue
        if not API_KEY:
            print(key_guidance(MODEL) + "\n")
            continue

        content = user_input
        if pending_context:         # 在原有记忆基础上继续多轮对话
            content = f"{pending_context}\n\n【用户本轮输入】{user_input}"
            pending_context = None
        history.append({"role": "user", "content": content})
        TODO.start(user_input)                # 主线清单就位，记住原始需求
        global CURRENT_TASK_DIR
        CURRENT_TASK_DIR = new_task_dir(user_input)
        print(f"[任务文件夹] {CURRENT_TASK_DIR.relative_to(SCRIPT_DIR)}")
        run_log = {"rounds": []}
        try:
            agent_loop(history, run_log)
        except Exception as e:
            print(f"Error: {e}")
            run_log.setdefault("final_text", f"(异常中止: {e})")
        print("\n⏳ 正在保存本轮记录并提取经验，请先不要关闭程序……")
        try:
            run_dir = archive_run(user_input, run_log, history, CURRENT_TASK_DIR)
            note, pending = extract_skill((run_dir / "流程.md").read_text(), run_dir)
            if pending:
                pending_context = pending
            print(f"[归档] {run_dir.relative_to(SCRIPT_DIR)} | {note}")
            print("✅ 记录已保存，本轮任务完成，可以继续提问或退出。")
        except Exception as e:
            print(f"[归档失败] {e}")
        print()


if __name__ == "__main__":
    main()
