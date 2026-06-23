"""插件系统 — 基类和加载器。

插件是一个放在 ~/.knowagent/plugins/ 下的 Python 文件，
继承 Plugin 基类并实现 get_commands() 等方法。
Agent 启动时自动扫描加载。
"""

import importlib.util
import inspect
import os
import sys

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
    """从单个 Python 文件加载插件。"""
    module_name = os.path.splitext(os.path.basename(fpath))[0]

    try:
        spec = importlib.util.spec_from_file_location(module_name, fpath)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 查找 Plugin 子类
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin:
                instance = obj()
                instance.on_load()
                return instance

        return None
    except Exception as e:
        print(f"  ⚠ 插件加载失败 [{os.path.basename(fpath)}]: {e}")
        return None
