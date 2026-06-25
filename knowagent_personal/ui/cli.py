"""Mac Agent Personal REPL — 本地交互终端，无需后端"""

import cmd
import json
import os
import readline
import re
import shlex
import shutil
import subprocess
import sys
import time

from knowagent_personal.agent.tools import COMMANDS, cmd_system_status, cmd_music_search_online
from knowagent_personal.agent.core import Agent
from knowagent_personal.agent.skill_manager import SkillManager, SKILL_DIR
from knowagent_personal.agent.llm import LLMClient
from knowagent_personal.agent.funnel import (
    increment_launch,
    get_funnel_message,
    open_github,
    open_sponsor,
    get_sponsor_text,
    set_dismissed,
)
from knowagent_personal.config import Config, CONFIG_DIR
from knowagent_personal.agent.aliases import resolve_cn


# ── 颜色 ──────────────────────────────────────────────────

class Color:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    CLEAR = '\033[2J\033[H'

    @staticmethod
    def ok(text): return f"{Color.GREEN}{text}{Color.RESET}"
    @staticmethod
    def info(text): return f"{Color.CYAN}{text}{Color.RESET}"
    @staticmethod
    def warn(text): return f"{Color.YELLOW}{text}{Color.RESET}"
    @staticmethod
    def err(text): return f"{Color.RED}{text}{Color.RESET}"
    @staticmethod
    def bold(text): return f"{Color.BOLD}{text}{Color.RESET}"
    @staticmethod
    def dim(text): return f"{Color.DIM}{text}{Color.RESET}"


# ── 自然语言解析器 ──────────────────────────────────────

# TODO: 逐步迁移到 aliases.py CN_ALIASES 和 IN_ALIASES
# 简单映射（无参数提取需求）已移至 CN_ALIASES。
# 剩下的规则多数需要 _parse_mail_date 等参数提取逻辑，
# 待 aliases.py 支持参数提取后再整体迁移。
NL_RULES = [
    (["播放", "听", "唱", "放", "music"], lambda kw: ("music_search_online", {"keyword": kw or "随机"})),
    (["搜索", "搜", "find", "查找", "search"], lambda kw: ("music_search_online", {"keyword": kw}) if kw else ("help", {})),
    (["邮箱大师", "MailMaster", "mailmaster"], lambda kw: ("mail_master", {"limit": kw}) if kw and kw.isdigit() else ("mail_master", {"limit": "10"})),
    (["读邮件", "收件箱", "邮件", "mail", "收到"], lambda kw: (
        "mail_master", {"date": _parse_mail_date(kw), "limit": "30"}
    ) if _parse_mail_date(kw) else ("mail_master", {"limit": "10"})),
    (["系统", "状态", "status", "info", "system"], lambda _: ("system_status", {})),
    (["cpu", "内存", "磁盘", "性能"], lambda _: ("system_status", {})),
    (["电池", "电量", "battery"], lambda _: ("battery_status", {})),
    (["wifi", "网络", "无线"], lambda _: ("wifi_status", {})),
    (["截图", "屏幕", "screenshot", "ss", "截屏"], lambda kw: ("screenshot_analyze", {"region": kw}) if kw and kw.replace(",", "").isdigit() else ("screenshot", {})),
    (["ocr", "识别", "文字"], lambda _: ("screenshot_analyze", {})),
    (["ui", "界面", "元素", "tree", "树"], lambda kw: ("ui_tree", {"app": kw}) if kw and not any(x in kw for x in ["点击","点一下","按"]) else ("ui_click", {"desc": kw}) if kw else ("help", {})),
    (["帮助", "help", "h", "?"], lambda _: ("help", {})),
    (["输入", "打字", "key", "type"], lambda kw: ("keyboard_type", {"text": kw})),
    (["按", "press", "快捷键"], lambda kw: ("keyboard_press", {"key": kw})),
    (["通知", "提醒", "notify"], lambda kw: ("notification", {"text": kw}) if kw else ("notification", {"text": "Hello from Mac Agent!"})),
    (["文件", "目录", "ls", "dir"], lambda kw: ("file_list", {"path": kw or "~"})),
    (["日历", "日程", "今天"], lambda _: ("calendar", {})),
    (["剪贴板", "clipboard", "复制"], lambda _: ("clipboard_read", {})),
    (["锁屏", "锁定"], lambda _: ("lock_screen", {})),
    (["番茄", "番茄钟", "番茄时钟", "timer", "计时", "专注"], lambda kw: (
        ("timer", {"minutes": _extract_number(kw) or 25, "name": "番茄钟"})
    )),
    (["朗读", "说", "speak", "say"], lambda kw: ("speak", {"text": kw or "你好"})),
    (["打开", "启动", "open"], lambda kw: ("open_app", {"name": kw}) if kw else ("help", {})),
    (["知识库", "知识", "文档", "笔记", "rag"], lambda kw: ("rag", {"subcmd": "search", "query": kw}) if kw and kw != "知识库" else ("help", {})),
    (["语音", "说话", "voice", "麦克风"], lambda _: ("voice_input", {})),
    (["工作流", "workflow", "auto"], lambda _: None),
]


def _extract_number(text: str) -> int | None:
    """从文本中提取数字，如 '25分钟' → 25, '1小时' → 60。"""
    import re
    m = re.search(r'(\d+)\s*小时', text)
    if m:
        return int(m.group(1)) * 60
    m = re.search(r'(\d+)\s*分钟?', text)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)', text)
    if m:
        return int(m.group(1))
    return None


def _parse_mail_date(text: str) -> str:
    import re
    m = re.search(r'(\d+)\s*月\s*(\d+)\s*[号日]', text)
    if m:
        return f"2026-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r'(\d+)\s*月', text)
    if m:
        return f"2026-{int(m.group(1)):02d}"
    return ""


WORKFLOW_PRESETS = {
    "系统报告": [
        {"cmd": "system_status", "desc": "检查系统"},
        {"cmd": "battery_status", "desc": "检查电池"},
        {"cmd": "wifi_status", "desc": "检查网络"},
        {"cmd": "calendar", "desc": "今日日程"},
    ],
    "音乐时光": [
        {"cmd": "music_search_online", "params": {"keyword": "经典"}, "desc": "播放经典"},
        {"cmd": "notification", "params": {"text": "音乐已开始播放"}, "desc": "通知"},
    ],
    "摸鱼预警": [
        {"cmd": "screenshot", "desc": "截屏"},
        {"cmd": "notification", "params": {"text": "注意! 老板来了!"}, "desc": "警告"},
    ],
}


def parse_natural(text: str):
    """将自然语言转为 (命令, 参数字典)"""
    text = text.strip()
    if not text:
        return None

    if text in COMMANDS:
        return (text, {})

    # NL 规则优先匹配：仅对含计时关键词的文本生效
    # 必须在别名之前，因为别名"打开"会拦截"打开番茄时钟 25分钟"
    import re as _re
    if _re.search(r'(?:番茄|番茄钟|番茄时钟|timer|计时|专注)', text, re.I):
        nl_result = _match_nl_rules(text)
        if nl_result:
            return nl_result

    # 检查中文别名（支持 "翻译 text=hello" 格式）
    resolved = resolve_cn(text)
    if resolved:
        cmd_name, rest = resolved
        params = {}
        if rest:
            try:
                for part in shlex.split(rest):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        params[k] = v
                    else:
                        params["keyword"] = part
                        params["text"] = part
            except Exception:
                params["keyword"] = rest
                params["text"] = rest
        return (cmd_name, params)

    for cmd_name in COMMANDS:
        if text.startswith(cmd_name + " "):
            rest = text[len(cmd_name) + 1:].strip()
            params = {}
            for part in shlex.split(rest):
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k] = v
                else:
                    params["keyword"] = part
                    params["text"] = part
            return (cmd_name, params)

    if "工作流" in text or "workflow" in text.lower():
        return ("_workflow", {})

    return _match_nl_rules(text)


def _match_nl_rules(text: str):
    """匹配 NL 规则，返回 (命令名, 参数字典) 或 None。"""
    import re as _re
    for keywords, handler in NL_RULES:
        for kw in keywords:
            if _re.search(r'[一-鿿]', kw):
                if kw in text:
                    _matched = True
                else:
                    _matched = False
            else:
                if _re.search(r'(?<!\w)' + _re.escape(kw.lower()) + r'(?!\w)', text.lower()):
                    _matched = True
                else:
                    _matched = False

            if _matched:
                rest = text
                for k in keywords:
                    if _re.search(r'[一-鿿]', k):
                        if k in rest:
                            rest = rest.replace(k, "", 1).strip()
                    else:
                        m = _re.search(r'(?<!\w)' + _re.escape(k.lower()) + r'(?!\w)', rest.lower())
                        if m:
                            rest = (rest[:m.start()] + rest[m.end():]).strip()
                if callable(handler):
                    result = handler(rest)
                    if result:
                        return result
                break

    return None


# ── 交互式 REPL ──────────────────────────────────────────

HISTORY_FILE = os.path.join(CONFIG_DIR, "history")


class PersonalAgentREPL(cmd.Cmd):
    prompt = f"{Color.info('› ')}"

    def __init__(self, config: Config, interactive=True):
        super().__init__()
        self.config = config
        self._last_output = ""
        self._interactive = interactive
        self._conv_history = []
        self.plugins = []

        # Load plugins
        self._load_plugins()

        # Set language-aware intro
        from knowagent_personal.agent.help_text import get_system_lang
        lang = get_system_lang()
        cmd_count = len(COMMANDS)
        if lang == "zh":
            self.intro = (
                f"\n{Color.bold('🤖 Mac Agent Personal  —  本地 Mac 桌面 AI 助手')}\n"
                f"{Color.dim('╶' * 40)}\n"
                f"  {Color.info('●')}  {cmd_count} 个系统命令  {Color.info('●')}  中文/英文双语言  {Color.info('●')}  OpenAI/Ollama\n"
                f"  {Color.dim('输入')} {Color.bold('help')} {Color.dim('查看所有命令')}   {Color.bold('exit')} {Color.dim('退出')}   {Color.dim('或直接说你想做什么')}\n"
                f"  {Color.dim('例如:')} 播放周杰伦的歌  |  系统状态  |  截个屏  |  翻译 hello\n"
            )
        else:
            self.intro = (
                f"\n{Color.bold('🤖 Mac Agent Personal  —  Local Mac AI Assistant')}\n"
                f"{Color.dim('╶' * 42)}\n"
                f"  {Color.info('●')}  {cmd_count} commands  {Color.info('●')}  CN/EN bilingual  {Color.info('●')}  OpenAI/Ollama\n"
                f"  {Color.dim('Type')} {Color.bold('help')} {Color.dim('for commands')}   {Color.bold('exit')} {Color.dim('to quit')}   {Color.dim('or just say what to do')}\n"
                f"  {Color.dim('e.g.:')} play Jay Chou  |  system status  |  translate hello\n"
            )

        # Create Agent
        self.llm_client = LLMClient(config)
        self.agent = Agent(self.llm_client, config)
        self.agent_available = False

        if interactive:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            try:
                readline.read_history_file(HISTORY_FILE)
            except (FileNotFoundError, PermissionError, OSError):
                pass
            try:
                readline.set_history_length(500)
            except Exception:
                pass

            # Check LLM availability
            self.agent_available, llm_msg = self.llm_client.check_available()
            if self.agent_available:
                print(f"  {Color.ok('✓')} {llm_msg}")
            else:
                print(f"  {Color.warn('⚠')} {llm_msg}")
                print(f"  {Color.dim('  仅可使用本地命令模式，输入 help 查看命令列表')}")

            # ── 用户转化漏斗提示 ────────────────────────────────
            state = increment_launch()
            funnel_msg = get_funnel_message(state, lang)
            if funnel_msg and not self.config.get("conversion.dismissed", False):
                print()
                for line in funnel_msg.split("\n"):
                    print(f"  {line}")
                print()

    def __del__(self):
        try:
            readline.write_history_file(HISTORY_FILE)
        except Exception:
            pass

    def default(self, line):
        if not line.strip():
            return

        # Catch standalone dismiss/star/sponsor typed in response to funnel prompt
        cmd = line.strip().lower()
        if cmd in ("star", "星", "stars"):
            self.do_star("")
            return
        if cmd in ("dismiss", "不再提示", "no"):
            self.do_dismiss("")
            return
        if cmd in ("sponsor", "赞助", "赞助作者", "sponsors"):
            self.do_sponsor("")
            return

        self._process(line)

    def _process(self, text):
        start = time.time()

        # 1. Try local command matching first (fast path)
        result = parse_natural(text)
        if result:
            cmd_name, params = result
            if cmd_name == "_workflow":
                self._show_workflows()
                return
            if cmd_name == "help":
                self.do_help("")
                return
            if cmd_name == "rag":
                # 解析 rag 子命令: "rag init" / "rag index ~/Documents" / "rag search xxx"
                rag_args = params.get("subcmd", "help")
                rag_query = params.get("query", "")
                if rag_args == "search" and rag_query:
                    self.do_rag(f"search {rag_query}")
                else:
                    self.do_rag(rag_args)
                return
            if cmd_name == "voice_input":
                import knowagent_personal.agent.tools as _t
                handler = _t.COMMANDS.get("voice_input")
                if handler:
                    print(handler({}))
                return

            handler = COMMANDS.get(cmd_name)
            if handler:
                try:
                    output = handler(params)
                    elapsed = time.time() - start
                    self._last_output = output
                    if isinstance(output, str):
                        print(output)
                    else:
                        print(json.dumps(output, ensure_ascii=False, indent=2))
                    print(f"\n{Color.dim(f'⏱ {elapsed:.1f}s  {cmd_name}')}")
                except Exception as e:
                    print(f"{Color.err(f'❌ 执行失败: {e}')}")
                return

        # 2. Try LLM agent (if available)
        if self.agent_available:
            self._chat_with_agent(text, start)
        else:
            self._local_chat(text)

    def _local_chat(self, text):
        """Offline chat when no LLM available."""
        t = text.lower()
        if any(k in t for k in ["你是谁", "你叫什么", "what are you"]):
            print(f"{Color.bold('🤖 Mac Agent Personal')} — 你的本地 Mac 桌面 AI 助手")
            print(f"{Color.dim('可以控制音乐、截图、OCR识别、UI自动化、查看系统状态等')}")
        elif any(k in t for k in ["能力", "能做什么", "功能", "capabilities"]):
            print(f"{Color.bold(f'📋 我具备 {len(COMMANDS)} 个命令:')}")
            self.do_help("")
        elif any(k in t for k in ["大模型", "模型", "ai", "llm"]):
            print(f"{Color.bold('🧠 AI 引擎:')}")
            print(f"  对话: Ollama (本地)")
            print(f"  命令执行: 本地离线 ({len(COMMANDS)} 个内置命令)")
            print(f"  OCR: macOS 原生 Vision 框架")
            print(f"  UI 自动化: Swift AX API")
        else:
            print(f"{Color.warn('🤔 没理解你的意思')}")
            print(f"{Color.dim('试试直接说命令: 播放周杰伦的歌 / 系统状态 / 截图 / 帮助')}")
            print(f"{Color.dim('或者确保 Ollama 正在运行以获得 AI 对话能力')}")

    def _chat_with_agent(self, text, start):
        """Use the local Agent (Ollama) for conversation + tool calling."""
        try:
            reply = self.agent.process(text)
            elapsed = time.time() - start
            self._last_output = reply
            print(reply)
            if elapsed > 1:
                print(f"\n{Color.dim(f'⏱ {elapsed:.1f}s')}")
        except Exception as e:
            print(f"{Color.err(f'❌ Agent 错误: {e}')}")
            self._local_chat(text)

    # ── 命令补全 ──────────────────────────────────────────

    def _load_plugins(self):
        """Scan and load plugins from ~/.knowagent/plugins/."""
        try:
            from knowagent_personal.plugins.loader import discover_plugins as _dp

            discovered = _dp()
        except ImportError:
            try:
                from knowagent_personal.plugins import discover_plugins as _dp

                discovered = _dp()
            except ImportError:
                discovered = []

        for p in discovered:
            self.plugins.append(p)
            for cmd_name, handler in p.get_commands().items():
                COMMANDS[cmd_name] = handler
            for rule in p.get_nl_rules():
                NL_RULES.append(rule)
            if self._interactive:
                print(f"  {Color.dim(f'🔌 加载插件: {p.name}')}")

        # Load skills from SKILL_DIR
        try:
            sm = SkillManager()
            sm.discover_skills()
            sm.register_all(COMMANDS, {})
            if self._interactive:
                skills = sm.list_skills()
                for s in skills:
                    print(f"  {Color.dim('🧠 加载技能: ' + s['name'])}")
        except Exception:
            pass

    def completenames(self, text, *ignored):
        return [f"{name} " for name in COMMANDS if name.startswith(text)]

    def completedefault(self, text, line, begidx, endidx):
        return []

    # ── 内置命令 ──────────────────────────────────────────

    def do_star(self, arg):
        """🌟 在 GitHub 上给项目点 Star"""
        open_github()
        print(f"  {Color.ok('✅')} GitHub 页面已打开，谢谢支持！")

    def do_sponsor(self, arg):
        """☕ 查看赞助方式"""
        from knowagent_personal.agent.help_text import get_system_lang
        lang = get_system_lang()
        print()
        print(get_sponsor_text(lang))
        print()
        # 如有赞助链接，询问是否打开
        if get_sponsor_text(lang):
            try:
                resp = input(f"  {Color.info('打开赞助页面? (y/n): ')}").strip().lower()
                if resp in ("y", "yes", "是", "ok"):
                    open_sponsor()
                    print(f"  {Color.ok('✅')} 赞助页面已打开，感谢你的支持！")
            except (EOFError, KeyboardInterrupt):
                print()

    def do_dismiss(self, arg):
        """🙈 不再显示赞助/Star 提示"""
        set_dismissed()
        print(f"  {Color.dim('已关闭提示，输入 star 或 sponsor 可随时查看')}")

    def do_help(self, arg):
        """Show help (auto-detect system language)"""
        from knowagent_personal.agent.help_text import get_help_text, get_system_lang
        from knowagent_personal.agent.aliases import get_cn_aliases

        lang = get_system_lang()
        txt = get_help_text(lang)

        print(f"\n{Color.bold(txt['title'])}")
        print(f"{Color.dim('=' * 50)}")
        print(f"\n{Color.bold(txt['natural_title'])}")
        for cmd, desc in txt['natural_examples']:
            padding = 24 - len(cmd)
            print(f"  {Color.info(cmd)}{' ' * padding}{Color.dim(desc)}")

        cn_available = (lang == "zh")
        cat_title = "Commands (Chinese names supported):" if not cn_available else "分类命令（支持中文调用）:"
        print(f"\n{Color.bold(cat_title)}")

        for title, cmds in txt['ex_categories'].items():
            print(f"\n  {Color.bold(title)}")
            for c in cmds:
                if c in COMMANDS:
                    docs = (COMMANDS[c].__doc__ or "").strip()
                    doc_short = docs.split("\n")[0][:50] if docs else ""
                    aliases = get_cn_aliases(c)
                    alias_str = f" ({', '.join(aliases[:3])})" if cn_available and aliases else ""
                    print(f"    {Color.info(c):30s} {Color.dim(doc_short)}{alias_str}")

        print(f"\n{Color.bold(txt['knowledge_title'])}")
        for cmd, desc in txt['knowledge_cmds']:
            padding = 24 - len(cmd)
            print(f"  {Color.dim(cmd)}{' ' * padding}{desc}")

        print(f"\n{Color.bold(txt['params_title'])}")
        for ex in txt['params_examples']:
            print(f"  {Color.dim(ex)}")

        print(f"\n{Color.dim(txt['footer'])}")

    def do_exit(self, arg):
        """退出"""
        print(f"\n{Color.dim('👋 再见!')}")
        sys.exit(0)

    def do_quit(self, arg):
        """退出"""
        self.do_exit(arg)

    def do_clear(self, arg):
        """清屏"""
        print(Color.CLEAR, end='')

    def do_rag(self, arg):
        """管理个人知识库。用法: rag init | rag index <路径> | rag search <关键词>"""
        from knowagent_personal.memory.rag import PersonalRAG

        parts = arg.strip().split(maxsplit=1)
        subcmd = parts[0] if parts else "help"
        rest = parts[1] if len(parts) > 1 else ""

        # 懒加载 RAG
        rag_instance = None
        if hasattr(self.agent, "_ensure_rag"):
            if self.agent._ensure_rag():
                rag_instance = self.agent.rag

        if subcmd == "init":
            if rag_instance:
                ok = rag_instance.init()
            else:
                rag_instance = PersonalRAG(self.config)
                ok = rag_instance.init()
            if ok:
                print(f"{Color.ok('✅')} 知识库已初始化")
            else:
                print(
                    f"{Color.err('❌')} 知识库初始化失败，"
                    f"请确保已安装: pip install chromadb sentence-transformers"
                )
        elif subcmd == "index":
            path = rest or "~/Documents"
            if rag_instance:
                result = rag_instance.index_directory(path)
            else:
                print(f"{Color.err('❌')} 知识库未初始化，请先运行: rag init")
                return
            print(f"📋 索引结果: {result}")
        elif subcmd == "search":
            if not rest:
                print(f"{Color.err('❌')} 需要搜索关键词，用法: rag search 关键词")
                return
            if hasattr(self.agent, "rag") and self.agent.rag:
                results = self.agent.rag.search(rest)
            else:
                print(f"{Color.err('❌')} 知识库未初始化，请先运行: rag init")
                return
            if not results:
                print(f"📭 未找到与「{rest}」相关的内容")
                return
            print(f"📋 找到 {len(results)} 条结果:\n")
            for r in results:
                print(f"  [{Color.dim(r['source'])}]")
                print(f"  {r['content']}\n")
        elif subcmd == "clear":
            from knowagent_personal.memory.db import clear_history

            clear_history()
            print(f"{Color.ok('✅')} 对话历史已清除")
        else:
            print("rag init             初始化知识库")
            print("rag index <路径>     索引文档目录（默认 ~/Documents）")
            print("rag search <关键词>  搜索知识库")
            print("rag clear           清除对话历史")

    def do_skill(self, arg):
        """管理技能。用法: skill action=list/search/install/remove/info [name=] [source=] [query=]"""
        from knowagent_personal.agent.plugin_tools import cmd_skill

        params = {}
        parts = arg.strip().split()
        if parts:
            params["action"] = parts[0]
            for p in parts[1:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v
                else:
                    params[k] = p
        print(cmd_skill(params))

    def do_workflow(self, arg):
        """运行预设工作流"""
        self._show_workflows()

    def do_history(self, arg):
        """查看命令历史"""
        n = readline.get_current_history_length()
        start = max(0, n - int(arg or 20))
        for i in range(start, n):
            print(f"  {i}: {readline.get_history_item(i)}")

    # ── 工作流 ────────────────────────────────────────────

    def _show_workflows(self):
        print(f"\n{Color.bold('📋 预设工作流:')}")
        wf_names = list(WORKFLOW_PRESETS.keys())
        for i, name in enumerate(wf_names, 1):
            steps = WORKFLOW_PRESETS[name]
            desc = " → ".join(s["desc"] for s in steps)
            print(f"  {i}. {Color.info(name)}: {Color.dim(desc)}")

        try:
            choice = input(f"\n{Color.info('选择工作流 (1-')}{len(wf_names)}{Color.info(') 或回车取消: ')}")
            if choice.isdigit() and 1 <= int(choice) <= len(wf_names):
                name = wf_names[int(choice) - 1]
                self._run_workflow(WORKFLOW_PRESETS[name])
        except (EOFError, KeyboardInterrupt):
            print()

    def _run_workflow(self, steps):
        print(f"\n{Color.bold('▶️ 执行工作流')}")
        total = len(steps)
        results = []
        for i, step in enumerate(steps, 1):
            cmd_name = step["cmd"]
            params = step.get("params", {})
            desc = step.get("desc", cmd_name)
            handler = COMMANDS.get(cmd_name)

            print(f"  [{i}/{total}] {Color.info(desc)}... ", end="", flush=True)
            if handler:
                try:
                    output = handler(params)
                    results.append(output)
                    print(f"{Color.ok('✅')}")
                    if isinstance(output, str) and len(output) > 100:
                        for l in output.split('\n')[:3]:
                            print(f"    {Color.dim(l[:80])}")
                except Exception as e:
                    print(f"{Color.err(f'❌ {e}')}")
                    results.append(f"❌ {e}")
            else:
                print(f"{Color.err('❌ 未知命令')}")
            time.sleep(0.3)

        success = sum(1 for r in results if not isinstance(r, str) or not r.startswith("❌"))
        print(f"\n{Color.bold(f'📊 工作流完成: {success}/{total} 步成功')}")


# ── 单条命令模式 ──────────────────────────────────────────

_CONFIG_CACHE = None


def _get_config(cli_overrides: dict | None = None) -> Config:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = Config(cli_overrides)
    return _CONFIG_CACHE


def single_command(text: str, cli_overrides: dict | None = None):
    """Execute a single command or chat."""
    config = _get_config(cli_overrides)

    result = parse_natural(text)
    if result:
        cmd_name, params = result
        if cmd_name == "help":
            _show_help_simple()
            return
        handler = COMMANDS.get(cmd_name)
        if handler:
            try:
                output = handler(params)
                if isinstance(output, str):
                    print(output)
                else:
                    print(json.dumps(output, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"❌ {e}")
            return

    # No command match → try Agent
    llm = LLMClient(config)
    available, _ = llm.check_available()
    if available:
        try:
            agent = Agent(llm, config)
            reply = agent.process(text)
            print(reply)
        except Exception:
            _chat_local_single(text)
    else:
        _chat_local_single(text)


def _show_help_simple():
    """Show categorized help with language auto-detect."""
    from knowagent_personal.agent.help_text import get_help_text, get_system_lang
    from knowagent_personal.agent.aliases import get_cn_aliases

    lang = get_system_lang()
    txt = get_help_text(lang)

    print(f"\n{Color.bold(txt['title'])}")
    print(f"{Color.dim('=' * 50)}")
    print(f"\n{Color.bold(txt['natural_title'])}")
    for cmd, desc in txt['natural_examples']:
        padding = 24 - len(cmd)
        print(f"  {Color.info(cmd)}{' ' * padding}{Color.dim(desc)}")

    cn_available = (lang == "zh")
    cat_title = "Commands:" if not cn_available else "分类命令:"
    print(f"\n{Color.bold(cat_title)}")

    for title, cmds in txt['ex_categories'].items():
        print(f"\n  {Color.bold(title)}")
        for c in cmds:
            if c in COMMANDS:
                docs = (COMMANDS[c].__doc__ or "").strip()
                doc_short = docs.split("\n")[0][:50] if docs else ""
                aliases = get_cn_aliases(c)
                alias_str = f" ({', '.join(aliases[:3])})" if cn_available and aliases else ""
                print(f"    {Color.info(c):30s} {Color.dim(doc_short)}{alias_str}")

    print(f"\n{Color.dim(txt['footer'])}")


def _chat_local_single(text):
    """Single-command local chat response."""
    t = text.lower()
    if any(k in t for k in ["你是谁", "你叫什么", "what are you"]):
        print(f"🤖 Mac Agent Personal — Mac 桌面 AI 助手，可控制音乐、截图、OCR、UI 自动化等")
    elif any(k in t for k in ["能力", "能做什么", "功能"]):
        print(f"📋 {len(COMMANDS)} 个命令: {', '.join(sorted(COMMANDS.keys()))}")
    elif any(k in t for k in ["大模型", "模型", "ai"]):
        print(f"🧠 对话: Ollama (本地) | 命令: 本地离线 | OCR: Vision | UI: Swift AX")
    else:
        print(f"🤔 试试直接说命令，如: 播放周杰伦的歌 / 系统状态 / 截图")
        print(f"{Color.dim('或: ka help 查看全部命令')}")


# ── 入口 ──────────────────────────────────────────────────

def run_repl(cli_overrides: dict | None = None):
    """Run the interactive REPL."""
    config = _get_config(cli_overrides)

    # Check Swift binaries
    from knowagent_personal.agent.tools import _BIN_DIR
    ax_bin = os.path.join(_BIN_DIR, "ax_inspector")
    ocr_bin = os.path.join(_BIN_DIR, "screen_ocr")
    if not (os.path.exists(ax_bin) and os.path.exists(ocr_bin)):
        print(f"{Color.dim('  ⚠ Swift 工具编译中...')}")

    try:
        PersonalAgentREPL(config).cmdloop()
    except KeyboardInterrupt:
        print(f"\n{Color.dim('👋 再见!')}")
