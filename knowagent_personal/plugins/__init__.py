"""插件系统 — 基类和加载器。

插件是一个放在 ~/.knowagent/plugins/ 下的 Python 文件，
继承 Plugin 基类并实现 get_commands() 等方法。
Agent 启动时自动扫描加载。
"""

import importlib.util
import inspect
import os
import sys
from typing import Any

PLUGIN_DIR = os.path.expanduser("~/.knowagent/plugins")


class Plugin:
    """所有插件的基类。

    子类只需覆盖 get_commands() 和/或 get_nl_rules()。
    """

    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    author: str = ""

    def get_commands(self) -> dict:
        """返回 {命令名: 处理函数}。

        处理函数签名: func(params: dict) -> str
        """
        return {}

    def get_nl_rules(self) -> list:
        """返回 [(关键词列表, handler), ...]，格式同 cli.py 的 NL_RULES。"""
        return []

    def on_load(self):
        """插件加载时的回调。"""
        pass

    def on_unload(self):
        """插件卸载时的回调。"""
        pass


class Skill(Plugin):
    """Plugin 的扩展子类，支持 cmd_ 方法自动注册和 OpenAI 兼容的 tool schema 生成。

    用法:
        class MySkill(Skill):
            name = "my_skill"
            description = "示例技能"

            def cmd_greet(self, name: str) -> str:
                \"\"\"向用户打招呼。

                Args:
                    name: 用户的名字
                \"\"\"
                return f"你好, {name}!"
    """

    tool_schema: dict[str, Any] | None = None
    auto_register: bool = True

    def get_commands(self) -> dict:
        """当 auto_register=True 时，从 cmd_ 方法自动注册。"""
        if self.auto_register:
            commands, _ = auto_register_skill(self)
            return commands
        return super().get_commands()

    def get_tool_schema(self, cmd_name: str) -> dict:
        """返回指定命令的 OpenAI 兼容 tool schema。

        如果 tool_schema 已设置且包含该命令则直接返回；
        否则从函数的 docstring 和签名自动生成。
        """
        # 如果已显式设置了 tool_schema，优先使用
        if self.tool_schema and cmd_name in self.tool_schema:
            return self.tool_schema[cmd_name]

        # 查找 cmd_ 前缀的方法
        func = getattr(self, cmd_name, None)
        if func is None:
            func = getattr(self, f"cmd_{cmd_name}", None)
        if func is None or not callable(func):
            return {}

        doc = inspect.getdoc(func) or ""
        doc_lines = [line.strip() for line in doc.split("\n") if line.strip()]
        description = doc_lines[0] if doc_lines else cmd_name

        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        # 从 docstring 提取 :param name: description 格式的参数描述
        param_descs: dict[str, str] = {}
        for line in doc_lines:
            if line.startswith(":param "):
                rest = line[len(":param "):]
                if ":" in rest:
                    pname, pdesc = rest.split(":", 1)
                    param_descs[pname.strip()] = pdesc.strip()
            elif line.startswith("param "):
                rest = line[len("param "):]
                if ":" in rest:
                    pname, pdesc = rest.split(":", 1)
                    param_descs[pname.strip()] = pdesc.strip()

        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in params:
            if param.name in ("self", "cls"):
                continue
            json_type = _pytype_to_json_schema_type(param.annotation)
            prop: dict[str, Any] = {"type": json_type}
            desc = param_descs.get(param.name, "")
            if desc:
                prop["description"] = desc
            if param.default is inspect.Parameter.empty:
                required.append(param.name)
            properties[param.name] = prop

        return {
            "type": "function",
            "function": {
                "name": cmd_name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


def _pytype_to_json_schema_type(pytype) -> str:
    """将 Python 类型映射为 JSON Schema 类型字符串。"""
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
    }
    # 处理 typing 模块的泛型类型
    origin = getattr(pytype, "__origin__", None)
    if origin is not None:
        return _pytype_to_json_schema_type(origin)
    return type_map.get(pytype, "string")


def auto_register_skill(skill: Skill) -> tuple[dict, dict]:
    """扫描 Skill 实例中所有 cmd_ 方法，返回 (commands_dict, schemas_dict)。
    自动去除 cmd_ 前缀，如 cmd_hello → 注册为 hello 命令。
    """
    commands: dict[str, Any] = {}
    schemas: dict[str, Any] = {}

    for attr_name in dir(skill):
        if not attr_name.startswith("cmd_"):
            continue
        func = getattr(skill, attr_name, None)
        if not callable(func):
            continue
        # 去掉 cmd_ 前缀注册（cmd_hello → hello）
        cmd_name = attr_name[4:]
        commands[cmd_name] = func
        schemas[cmd_name] = skill.get_tool_schema(attr_name)

    return commands, schemas


def discover_plugins() -> list[Plugin]:
    """扫描 ~/.knowagent/plugins/ 目录，加载所有插件。"""
    os.makedirs(PLUGIN_DIR, exist_ok=True)
    plugins = []

    if not os.path.isdir(PLUGIN_DIR):
        return plugins

    for fname in sorted(os.listdir(PLUGIN_DIR)):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        fpath = os.path.join(PLUGIN_DIR, fname)
        plugin = _load_plugin_from_file(fpath)
        if plugin:
            plugins.append(plugin)

    return plugins


def _load_plugin_from_file(fpath: str) -> Plugin | None:
    """从单个 Python 文件加载插件。

    优先识别 Skill 子类（因为它们继承 Plugin），
    回退到普通 Plugin 子类。
    """
    module_name = os.path.splitext(os.path.basename(fpath))[0]

    try:
        spec = importlib.util.spec_from_file_location(module_name, fpath)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 优先查找 Skill 子类（Skill is-a Plugin，但更具体）
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Skill) and obj is not Skill:
                instance = obj()
                instance.on_load()
                return instance

        # 回退到普通 Plugin 子类
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin:
                instance = obj()
                instance.on_load()
                return instance

        return None
    except Exception as e:
        print(f"  ⚠ 插件加载失败 [{os.path.basename(fpath)}]: {e}")
        return None
