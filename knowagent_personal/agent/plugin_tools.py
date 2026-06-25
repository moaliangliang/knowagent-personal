"""技能管理命令模块

安装、列举、搜索、移除技能。
所有 cmd_* 函数统一返回 str（纯文本），格式：
  ✅ 成功信息
  ❌ 错误信息
  📦 技能列表/详情信息
"""

from knowagent_personal.agent.skill_manager import SkillManager

_SM = SkillManager()


# ── 命令处理器（全部返回 str）───────────────────────────

def cmd_skill(params: dict) -> str:
    """管理技能。action=list/search/install/remove/info, query=, source=, name="""
    action = params.get("action", "list")

    if action == "list":
        skills = _SM.list_skills()
        if not skills:
            return "📦 未安装任何技能"
        lines = [f"📦 已安装 {len(skills)} 个技能:"]
        for s in skills:
            lines.append(f"  {s['name']:20s}  {s['path']}")
        return "\n".join(lines)

    if action == "search":
        query = params.get("query", "")
        skills = _SM.search_skills(query)
        if not skills:
            return f"📦 未找到匹配「{query}」的技能"
        lines = [f"📦 搜索「{query}」找到 {len(skills)} 个技能:"]
        for s in skills:
            lines.append(f"  {s['name']:20s}  {s['path']}")
        return "\n".join(lines)

    if action == "install":
        source = params.get("source", "")
        if not source:
            return "❌ 需要 source 参数（如 gh:user/repo, 本地路径, 远程 URL）"
        try:
            return _SM.install_skill(source)
        except Exception as e:
            return f"❌ 安装失败: {e}"

    if action == "remove":
        name = params.get("name", "")
        if not name:
            return "❌ 需要 name 参数（技能名称）"
        try:
            return _SM.remove_skill(name)
        except FileNotFoundError:
            return f"❌ 未找到技能「{name}」"
        except Exception as e:
            return f"❌ 移除失败: {e}"

    if action == "info":
        name = params.get("name", "")
        if not name:
            return "❌ 需要 name 参数（技能名称）"
        info = _SM.get_skill(name)
        if not info:
            return f"❌ 未找到技能「{name}」"
        from datetime import datetime as _dt
        lines = [
            f"📦 技能详情: {info['name']}",
            f"  文件: {info['file']}",
            f"  路径: {info['path']}",
            f"  大小: {info['size']} bytes",
            f"  修改: {_dt.fromtimestamp(info['modified']).strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        return "\n".join(lines)

    return f"❌ 未知 action: {action}，可用: list, search, install, remove, info"


# ── 命令注册 ─────────────────────────────────────────────

COMMANDS: dict = {
    "skill": cmd_skill,
}

TOOL_SCHEMAS: dict = {
    "skill": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作: list(列举), search(搜索), install(安装), remove(移除), info(详情)",
                "enum": ["list", "search", "install", "remove", "info"],
                "default": "list",
            },
            "query": {
                "type": "string",
                "description": "搜索关键词（action=search 时使用）",
            },
            "source": {
                "type": "string",
                "description": "安装来源（action=install 时使用），支持 gh:user/repo、本地路径、远程 URL",
            },
            "name": {
                "type": "string",
                "description": "技能名称（action=remove/info 时使用）",
            },
        },
    },
}
