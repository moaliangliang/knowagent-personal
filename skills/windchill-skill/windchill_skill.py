"""Windchill PLM Skill — PTC Windchill 全功能集成。

支持两种模式:
  bridge  — 通过 HTTP 桥接后端 (个人版默认)
  direct  — 直接连接 Windchill OData API (后端)

安装:
  ka skill install gh:knowagent/windchill-skill

使用:
  ka 查零件 number=ABC-123
  ka 查BOM part_number=ABC-123
  ka 审批 task_id=123 comment="已确认"
  ka oracle status
"""

import json
import os
import time
from typing import Any

from knowagent_personal.plugins import Skill

# ── 配置 ─────────────────────────────────────────────────
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(
    os.path.dirname(SKILL_DIR),
    "windchill_skill.yaml",
)
DEFAULT_CONFIG = {
    "mode": "bridge",
    "bridge": {"url": "http://localhost:8000"},
    "direct": {
        "host": "61.169.97.58",
        "http_port": "7380",
        "ssh_port": "2222",
        "odata_user": "wcadmin",
        "odata_password": "",
        "ssh_user": "administrator",
        "ssh_password": "",
        "windchill_home": "D:/ptc/Windchill_12.1/Windchill",
        "oracle_home": "D:/app/oracle/product/12.1.0/dbhome_1",
    },
}

# ── Windchill 别名映射 ──────────────────────────────────
_ALIASES = {
    # 状态/服务器
    "status": "server_status",
    "server": "server_status",
    "server_status": "server_status",
    "methodserver": "server_methodserver",
    "worker_status": "worker_agent_status",
    "worker": "worker_control",
    # 查询
    "parts": "query_parts_list",
    "part": "query_by_number",
    "query_part": "query_by_number",
    "bom": "query_bom",
    "query_bom": "query_bom",
    "documents": "query_documents",
    "docs": "query_documents",
    "users": "query_users",
    "groups": "query_groups",
    "tasks": "query_workitems",
    "workitems": "query_workitems",
    "pr": "query_problem_reports",
    "problem_reports": "query_problem_reports",
    "variance": "query_variances",
    "part_lists": "query_part_lists",
    # 变更管理
    "cr": "query_change_requests",
    "change_requests": "query_change_requests",
    "co": "query_change_orders",
    "change_orders": "query_change_orders",
    "create_cr": "create_cr",
    "create_co": "create_co",
    # 操作
    "create_part": "create_part",
    "create_doc": "create_document",
    "delete_part": "delete_part",
    "revise": "revise_part",
    "update": "update_part",
    "add_bom": "add_bom_item",
    "delete_bom": "delete_bom_item",
    "obsolete": "obsolete_part",
    "security_labels": "edit_part_security_labels",
    # 审批
    "approve": "approve_task",
    "reject": "reject_task",
    "reassign": "reassign_task",
    "save_workitem": "save_workitem",
    "save": "save_workitem",
    # 日志
    "logs": "query_logs",
    "view_log": "view_log",
    "viewlog": "view_log",
    # Oracle
    "oracle": "server_oracle",
    "sql": "oracle_sql",
    "oracle_sql": "oracle_sql",
    "backup": "oracle_backup",
    # 系统
    "rehost": "system_rehost",
    "clone": "system_clone",
    "set_pref": "set_preference",
    "preference": "set_preference",
    # 事件
    "events": "list_events",
    "event_subs": "list_event_subscriptions",
    "create_sub": "create_event_subscription",
    "delete_sub": "delete_event_subscription",
    # 桌面代理
    "agents": "desktop_agent_list",
    "agent_cmd": "desktop_agent_command",
    # 实施工具
    "gen_type": "generate_type_xml",
    "gen_class": "generate_class_xml",
    "gen_lifecycle": "generate_lifecycle_xml",
    "gen_oir": "generate_oir_xml",
    # 其他
    "wecom": "send_wecom_message",
    "send_wecom": "send_wecom_message",
    "common_props": "update_common_properties",
    "workitem_reassign_users": "get_workitem_reassign_user_list",
}

_WINDCHILL_COMMANDS = {}


def _load_config() -> dict:
    """加载 Skill 配置。"""
    import yaml as _yaml
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                loaded = _yaml.safe_load(f) or {}
            _deep_merge(config, loaded)
        except Exception:
            pass
    return config


def _deep_merge(base: dict, override: dict):
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _resolve_action(action: str) -> str:
    """解析别名 → 完整 action 名。"""
    return _ALIASES.get(action, action) if action in _ALIASES else action


# ═══════════════════════════════════════════════════════════
# 1. 查询类 (17 个)
# ═══════════════════════════════════════════════════════════


def cmd_query_by_number(params: dict) -> str:
    """按物料编号查询零件。:param number: 物料编号"""
    return _bridge("query_by_number", params)


def cmd_query_by_name(params: dict) -> str:
    """按名称模糊搜索物料。:param name: 物料名称 :param limit: 返回数量"""
    return _bridge("query_by_name", params)


def cmd_query_parts_list(params: dict) -> str:
    """列出最近物料列表。:param max_results: 返回数量(默认20)"""
    return _bridge("list_parts", params)


def cmd_query_bom(params: dict) -> str:
    """查询 BOM 结构树。:param part_number: 物料编号"""
    return _bridge("query_bom", params)


def cmd_get_parts_list(params: dict) -> str:
    """获取汇总 BOM（唯一零件合计数量）。:param part_number: 物料编号"""
    return _bridge("get_parts_list", params)


def cmd_query_change_orders(params: dict) -> str:
    """查询变更通告(CO)列表。:param max_results: 返回数量(默认20)"""
    return _bridge("query_change_orders", params)


def cmd_query_change_requests(params: dict) -> str:
    """查询变更请求(CR)列表。:param max_results: 返回数量(默认20)"""
    return _bridge("query_change_requests", params)


def cmd_query_users(params: dict) -> str:
    """查询用户列表。:param max_results: 返回数量(默认20)"""
    return _bridge("query_users", params)


def cmd_query_groups(params: dict) -> str:
    """查询用户组列表。:param max_results: 返回数量(默认20)"""
    return _bridge("query_groups", params)


def cmd_query_documents(params: dict) -> str:
    """查询文档列表。:param max_results: 返回数量(默认20)"""
    return _bridge("query_documents", params)


def cmd_query_workitems(params: dict) -> str:
    """查询工作流任务列表。:param status: 状态(ACTIVE/COMPLETED) :param max_results: 返回数量(默认20)"""
    return _bridge("query_workitems", params)


def cmd_query_part_lists(params: dict) -> str:
    """查询零件清单列表。:param max_results: 返回数量(默认20)"""
    return _bridge("query_part_lists", params)


def cmd_query_problem_reports(params: dict) -> str:
    """查询问题报告(PR)列表。:param max_results: 返回数量(默认20)"""
    return _bridge("query_problem_reports", params)


def cmd_query_variances(params: dict) -> str:
    """查询偏差列表。:param max_results: 返回数量(默认20)"""
    return _bridge("query_variances", params)


def cmd_get_workitem_reassign_user_list(params: dict) -> str:
    """查询可转派用户列表。:param task_id: 任务ID"""
    return _bridge("get_workitem_reassign_user_list", params)


def cmd_query_logs(params: dict) -> str:
    """查询 Windchill 日志文件列表。
    :param directory: 日志目录(wt.logs.dir/methodserver.logs.dir)
    :param file_pattern: 文件匹配模式
    :param max_age: 最大天数
    :param max_results: 返回数量默认30"""
    return _bridge("query_logs", params)


def cmd_view_log(params: dict) -> str:
    """查看日志文件内容。:param filename: 文件名 :param max_lines: 行数(默认50) :param search: 搜索关键词"""
    return _bridge("view_log", params)


# ═══════════════════════════════════════════════════════════
# 2. 操作类 (9 个)
# ═══════════════════════════════════════════════════════════


def cmd_create_part(params: dict) -> str:
    """创建新物料。:param name: 物料名称 :param number: 物料编号(可选自动生成)"""
    return _bridge("create_part", params)


def cmd_create_document(params: dict) -> str:
    """创建新文档。:param name: 文档名称 :param filepath: 文件路径(可选)"""
    return _bridge("create_document", params)


def cmd_delete_part(params: dict) -> str:
    """删除物料。:param number: 物料编号"""
    return _bridge("delete_part", params)


def cmd_revise_part(params: dict) -> str:
    """修订/升版物料。:param number: 物料编号"""
    return _bridge("revise_part", params)


def cmd_update_part(params: dict) -> str:
    """更新物料属性。:param number: 物料编号 :param field: 字段名 :param value: 新值"""
    return _bridge("update_part", params)


def cmd_update_common_properties(params: dict) -> str:
    """更新通用属性。:param number: 物料编号 :param field: 字段名 :param value: 新值"""
    return _bridge("update_common_properties", params)


def cmd_add_bom_item(params: dict) -> str:
    """添加 BOM 子件。:param parent_number: 父物料号 :param child_number: 子物料号 :param quantity: 数量(默认1.0)"""
    return _bridge("add_bom_item", params)


def cmd_delete_bom_item(params: dict) -> str:
    """删除 BOM 子件。:param parent_number: 父物料号 :param child_number: 子物料号"""
    return _bridge("delete_bom_item", params)


def cmd_edit_part_security_labels(params: dict) -> str:
    """编辑物料安全标签。:param number: 物料编号 :param labels: 标签"""
    return _bridge("edit_part_security_labels", params)


# ═══════════════════════════════════════════════════════════
# 3. 审批/工作流类 (4 个)
# ═══════════════════════════════════════════════════════════


def cmd_approve_task(params: dict) -> str:
    """审批通过工作流任务。:param task_id: 任务ID :param comment: 审批意见"""
    return _bridge("approve_task", params)


def cmd_reject_task(params: dict) -> str:
    """驳回工作流任务。:param task_id: 任务ID :param comment: 驳回原因"""
    return _bridge("reject_task", params)


def cmd_reassign_task(params: dict) -> str:
    """转派工作流任务。:param task_id: 任务ID :param user_name: 目标用户 :param comment: 转派原因"""
    return _bridge("reassign_task", params)


def cmd_save_workitem(params: dict) -> str:
    """暂存工作流任务（不提交审批）。:param task_id: 任务ID :param comment: 备注"""
    return _bridge("save_workitem", params)


# ═══════════════════════════════════════════════════════════
# 4. 系统管理类 (11 个)
# ═══════════════════════════════════════════════════════════


def cmd_server_status(params: dict) -> str:
    """查询 Windchill 服务器整体状态。"""
    return _bridge("server_status", params)


def cmd_server_methodserver(params: dict) -> str:
    """MethodServer 启停查。:param action: status/start/stop/restart"""
    return _bridge("server_methodserver", params)


def cmd_worker_agent_status(params: dict) -> str:
    """查询 Worker Agent 状态。"""
    return _bridge("worker_agent_status", params)


def cmd_worker_control(params: dict) -> str:
    """控制 Worker Agent。:param action: status/start/stop/reload/restart :param name: Worker名"""
    return _bridge("worker_control", params)


def cmd_add_worker(params: dict) -> str:
    """添加新 Worker。:param name: Worker名 :param host: 主机 :param exe_path: 执行路径 :param instances: 实例数"""
    return _bridge("add_worker", params)


def cmd_obsolete_part(params: dict) -> str:
    """作废物料。:param number: 物料编号"""
    return _bridge("obsolete_part", params)


def cmd_set_preference(params: dict) -> str:
    """设置系统首选项。:param name: 首选项名 :param value: 值"""
    return _bridge("set_preference", params)


def cmd_system_rehost(params: dict) -> str:
    """系统重托管（修改主机名/端口）。:param new_hostname: 新主机名 :param new_http_port: 新HTTP端口 :param new_rmi_port: 新RMI端口"""
    return _bridge("system_rehost", params)


def cmd_system_clone(params: dict) -> str:
    """系统克隆准备。:param output_dir: 输出目录 :param db_schema: 数据库Schema :param oracle_home: Oracle路径"""
    return _bridge("system_clone", params)


def cmd_create_cr(params: dict) -> str:
    """创建变更请求。:param subject: 主题 :param description: 描述"""
    return _bridge("create_cr", params)


def cmd_create_co(params: dict) -> str:
    """创建变更通告。:param subject: 主题 :param description: 描述"""
    return _bridge("create_co", params)


# ═══════════════════════════════════════════════════════════
# 5. Oracle DBA (3 个)
# ═══════════════════════════════════════════════════════════


def cmd_server_oracle(params: dict) -> str:
    """Oracle 数据库运维。
    :param action: 操作(status/start/stop/restart/tablespace/session/top_sql/size/wait/user/kill_session/resize/autoextend/awr)
    :param sid: Session SID(kill_session需要)
    :param serial: Session Serial(kill_session需要)
    :param size_mb: 大小MB(resize需要)"""
    return _bridge("server_oracle", params)


def cmd_oracle_sql(params: dict) -> str:
    """执行 Oracle SQL 语句。:param sql: SQL语句"""
    return _bridge("oracle_sql", params)


def cmd_oracle_backup(params: dict) -> str:
    """Oracle 数据库备份。:param method: expdp/rman :param schemas: Schema列表(:分隔)"""
    return _bridge("oracle_backup", params)


# ═══════════════════════════════════════════════════════════
# 6. 实施/配置工具类 (4 个)
# ═══════════════════════════════════════════════════════════


def cmd_generate_type_xml(params: dict) -> str:
    """生成类型属性定义 XML。:param name: 类型名 :param base_type: 基类型(默认WTPart) :param attributes: 属性定义"""
    return _bridge("generate_type_xml", params)


def cmd_generate_class_xml(params: dict) -> str:
    """生成分类定义 XML。:param name: 分类名 :param nodes: 节点定义"""
    return _bridge("generate_class_xml", params)


def cmd_generate_lifecycle_xml(params: dict) -> str:
    """生成生命周期模板 XML。:param name: 模板名 :param states: 状态定义"""
    return _bridge("generate_lifecycle_xml", params)


def cmd_generate_oir_xml(params: dict) -> str:
    """生成对象初始化规则 OIR XML。:param name: 规则名 :param type_name: 类型(默认wt.part.WTPart) :param attributes: 属性"""
    return _bridge("generate_oir_xml", params)


# ═══════════════════════════════════════════════════════════
# 7. 事件订阅类 (3 个)
# ═══════════════════════════════════════════════════════════


def cmd_list_events(params: dict) -> str:
    """查询可订阅的事件类型。:param max_results: 返回数量(默认50)"""
    return _bridge("list_events", params)


def cmd_list_event_subscriptions(params: dict) -> str:
    """查询事件订阅列表。:param max_results: 返回数量(默认20)"""
    return _bridge("list_event_subscriptions", params)


def cmd_create_event_subscription(params: dict) -> str:
    """创建事件订阅（回调通知）。:param name: 订阅名 :param callback_url: 回调URL :param event_name: 事件名 :param entity_type: 实体类型(可选) :param entity_id: 实体ID(可选)"""
    return _bridge("create_event_subscription", params)


def cmd_delete_event_subscription(params: dict) -> str:
    """删除事件订阅。:param subscription_id: 订阅ID"""
    return _bridge("delete_event_subscription", params)


# ═══════════════════════════════════════════════════════════
# 8. 桌面代理类 (2 个)
# ═══════════════════════════════════════════════════════════


def cmd_desktop_agent_list(params: dict) -> str:
    """列出所有已连接的桌面 Agent。"""
    return _bridge("desktop_agent_list", params)


def cmd_desktop_agent_command(params: dict) -> str:
    """向桌面 Agent 发送命令。:param agent_id: AgentID :param command: 命令名 :param params: JSON参数"""
    return _bridge("desktop_agent_command", params)


# ═══════════════════════════════════════════════════════════
# 9. 其他 (2 个)
# ═══════════════════════════════════════════════════════════


def cmd_send_wecom_message(params: dict) -> str:
    """通过企业微信发送消息。:param user_id: 用户ID :param content: 消息内容"""
    return _bridge("send_wecom_message", params)


def cmd_windchill_generic(params: dict) -> str:
    """通用 Windchill 操作入口（支持别名简写）。
    可通过 `action=xxx` 指定操作名，支持别名。
    :param action: 操作名(status/parts/part/bom/users/tasks/cr/co/approve/reject/oracle/sql/logs...)
    :param keyword: 简写操作名(备用)"""
    action = params.get("action") or params.get("keyword", "")
    if not action:
        return "❌ 需要 action 参数。可用: status, parts, part, bom, users, tasks, cr, co, approve, reject, oracle, sql, logs"
    resolved = _resolve_action(action.lower().strip())
    return _bridge(resolved, {k: v for k, v in params.items() if k not in ("action", "keyword")})


# ═══════════════════════════════════════════════════════════
# 桥接层
# ═══════════════════════════════════════════════════════════

def _bridge(action: str, params: dict) -> str:
    """通过 HTTP 桥接到后端 KnowAgent 服务。"""
    config = _load_config()
    mode = config.get("mode", "bridge")

    if mode == "direct":
        return _execute_direct(action, params, config.get("direct", {}))

    # bridge 模式
    url = config.get("bridge", {}).get("url", "http://localhost:8000")
    try:
        import httpx as _httpx
        resp = _httpx.post(
            f"{url}/api/agent/windchill",
            json={"action": f"windchill_{action}", "params": params},
            timeout=60,
        )
        result = resp.json()
        if result.get("success"):
            return str(result.get("data", ""))
        return f"❌ {result.get('error', '未知错误')}"
    except ImportError:
        return "❌ 需要 httpx: pip install httpx"
    except Exception as e:
        return f"❌ 桥接调用失败: {e}"


def _execute_direct(action: str, params: dict, direct_cfg: dict) -> str:
    """直接模式：后端直接操作 Windchill OData API（占位，后端实现）。"""
    # 后端模式：直接调用 WindchillODataClient
    # 这个路径由 knowagent 后端 tools.py 中的函数实现
    return f"⚠️ 直接模式需要 knowagent 后端支持。action={action} params={params}"


# ═══════════════════════════════════════════════════════════
# Skill 类
# ═══════════════════════════════════════════════════════════


class WindchillSkill(Skill):
    """Windchill PLM Integration Skill — 56 个命令。"""

    name = "windchill"
    description = "PTC Windchill PLM 集成 — 零件/BOM/工作流/文档/变更/Oracle 运维"
    version = "2.0.0"
    author = "KnowAgent"
    auto_register = True

    # ── 查询类 ──
    def cmd_query_by_number(self, number: str) -> str: return cmd_query_by_number({"number": number})
    def cmd_query_by_name(self, name: str, limit: int = 20) -> str: return cmd_query_by_name({"name": name, "limit": str(limit)})
    def cmd_query_bom(self, part_number: str) -> str: return cmd_query_bom({"part_number": part_number})
    def cmd_query_parts_list(self, max_results: str = "20") -> str: return cmd_query_parts_list({"max_results": max_results})
    def cmd_get_parts_list(self, part_number: str) -> str: return cmd_get_parts_list({"part_number": part_number})
    def cmd_query_change_orders(self, max_results: str = "20") -> str: return cmd_query_change_orders({"max_results": max_results})
    def cmd_query_change_requests(self, max_results: str = "20") -> str: return cmd_query_change_requests({"max_results": max_results})
    def cmd_query_users(self, max_results: str = "20") -> str: return cmd_query_users({"max_results": max_results})
    def cmd_query_groups(self, max_results: str = "20") -> str: return cmd_query_groups({"max_results": max_results})
    def cmd_query_documents(self, max_results: str = "20") -> str: return cmd_query_documents({"max_results": max_results})
    def cmd_query_workitems(self, status: str = "ACTIVE", max_results: str = "20") -> str: return cmd_query_workitems({"status": status, "max_results": max_results})
    def cmd_query_part_lists(self, max_results: str = "20") -> str: return cmd_query_part_lists({"max_results": max_results})
    def cmd_query_problem_reports(self, max_results: str = "20") -> str: return cmd_query_problem_reports({"max_results": max_results})
    def cmd_query_variances(self, max_results: str = "20") -> str: return cmd_query_variances({"max_results": max_results})
    def cmd_query_logs(self, directory: str = "wt.logs.dir", file_pattern: str = "", max_results: str = "30") -> str: return cmd_query_logs({"directory": directory, "file_pattern": file_pattern, "max_results": max_results})
    def cmd_view_log(self, filename: str, max_lines: str = "50", search: str = "") -> str: return cmd_view_log({"filename": filename, "max_lines": max_lines, "search": search})
    def cmd_get_workitem_reassign_user_list(self, task_id: str) -> str: return cmd_get_workitem_reassign_user_list({"task_id": task_id})

    # ── 操作类 ──
    def cmd_create_part(self, name: str, number: str = "") -> str: return cmd_create_part({"name": name, "number": number})
    def cmd_create_document(self, name: str, filepath: str = "") -> str: return cmd_create_document({"name": name, "filepath": filepath})
    def cmd_delete_part(self, number: str) -> str: return cmd_delete_part({"number": number})
    def cmd_revise_part(self, number: str) -> str: return cmd_revise_part({"number": number})
    def cmd_update_part(self, number: str, field: str = "", value: str = "") -> str: return cmd_update_part({"number": number, "field": field, "value": value})
    def cmd_update_common_properties(self, number: str, field: str = "", value: str = "") -> str: return cmd_update_common_properties({"number": number, "field": field, "value": value})
    def cmd_add_bom_item(self, parent_number: str, child_number: str, quantity: float = 1.0) -> str: return cmd_add_bom_item({"parent_number": parent_number, "child_number": child_number, "quantity": quantity})
    def cmd_delete_bom_item(self, parent_number: str, child_number: str) -> str: return cmd_delete_bom_item({"parent_number": parent_number, "child_number": child_number})
    def cmd_edit_part_security_labels(self, number: str, labels: str = "") -> str: return cmd_edit_part_security_labels({"number": number, "labels": labels})

    # ── 审批/工作流 ──
    def cmd_approve_task(self, task_id: str, comment: str = "") -> str: return cmd_approve_task({"task_id": task_id, "comment": comment})
    def cmd_reject_task(self, task_id: str, comment: str = "") -> str: return cmd_reject_task({"task_id": task_id, "comment": comment})
    def cmd_reassign_task(self, task_id: str, user_name: str, comment: str = "") -> str: return cmd_reassign_task({"task_id": task_id, "user_name": user_name, "comment": comment})
    def cmd_save_workitem(self, task_id: str, comment: str = "") -> str: return cmd_save_workitem({"task_id": task_id, "comment": comment})

    # ── 系统管理 ──
    def cmd_server_status(self) -> str: return cmd_server_status({})
    def cmd_server_methodserver(self, action: str = "status") -> str: return cmd_server_methodserver({"action": action})
    def cmd_worker_agent_status(self) -> str: return cmd_worker_agent_status({})
    def cmd_worker_control(self, action: str = "status", name: str = "") -> str: return cmd_worker_control({"action": action, "name": name})
    def cmd_add_worker(self, name: str = "OFFICE", host: str = "", exe_path: str = "") -> str: return cmd_add_worker({"name": name, "host": host, "exe_path": exe_path})
    def cmd_obsolete_part(self, number: str) -> str: return cmd_obsolete_part({"number": number})
    def cmd_set_preference(self, name: str = "", value: str = "") -> str: return cmd_set_preference({"name": name, "value": value})
    def cmd_system_rehost(self, new_hostname: str = "", new_http_port: str = "") -> str: return cmd_system_rehost({"new_hostname": new_hostname, "new_http_port": new_http_port})
    def cmd_system_clone(self, output_dir: str = "") -> str: return cmd_system_clone({"output_dir": output_dir})
    def cmd_create_cr(self, subject: str, description: str = "") -> str: return cmd_create_cr({"subject": subject, "description": description})
    def cmd_create_co(self, subject: str, description: str = "") -> str: return cmd_create_co({"subject": subject, "description": description})

    # ── Oracle DBA ──
    def cmd_server_oracle(self, action: str = "status", sid: str = "", serial: str = "", size_mb: str = "") -> str: return cmd_server_oracle({"action": action, "sid": sid, "serial": serial, "size_mb": size_mb})
    def cmd_oracle_sql(self, sql: str = "") -> str: return cmd_oracle_sql({"sql": sql})
    def cmd_oracle_backup(self, method: str = "expdp", schemas: str = "") -> str: return cmd_oracle_backup({"method": method, "schemas": schemas})

    # ── 实施工具 ──
    def cmd_generate_type_xml(self, name: str, attributes: str = "") -> str: return cmd_generate_type_xml({"name": name, "attributes": attributes})
    def cmd_generate_lifecycle_xml(self, name: str = "") -> str: return cmd_generate_lifecycle_xml({"name": name})

    # ── 事件订阅 ──
    def cmd_list_events(self, max_results: str = "50") -> str: return cmd_list_events({"max_results": max_results})
    def cmd_create_event_subscription(self, name: str, callback_url: str, event_name: str) -> str: return cmd_create_event_subscription({"name": name, "callback_url": callback_url, "event_name": event_name})

    # ── 桌面代理 ──
    def cmd_desktop_agent_list(self) -> str: return cmd_desktop_agent_list({})
    def cmd_desktop_agent_command(self, agent_id: str, command: str, params: str = "") -> str: return cmd_desktop_agent_command({"agent_id": agent_id, "command": command, "params": params})

    # ── 其他 ──
    def cmd_send_wecom_message(self, user_id: str, content: str) -> str: return cmd_send_wecom_message({"user_id": user_id, "content": content})

    # ── NL 规则 ──
    def get_nl_rules(self):
        return [
            (["查零件", "零件查询", "query_part"], lambda kw: ("query_by_number", {"number": kw}) if kw else None),
            (["查BOM", "BOM", "产品结构"], lambda kw: ("query_bom", {"part_number": kw}) if kw else None),
            (["审批", "通过任务"], lambda kw: ("approve_task", {"task_id": kw}) if kw else None),
            (["查文档", "文档列表", "文档查询"], lambda _: ("query_documents", {})),
            (["服务器", "server_status", "服务状态"], lambda _: ("server_status", {})),
            (["待办", "任务", "workitems", "待办任务"], lambda _: ("query_workitems", {})),
            (["日志", "log", "查看日志"], lambda kw: ("view_log", {"filename": kw}) if kw else ("query_logs", {})),
            (["oracle", "数据库", "Oracle"], lambda kw: ("server_oracle", {"action": kw}) if kw else ("server_oracle", {})),
            (["Windchill", "windchill"], lambda kw: ("windchill_generic", {"action": kw})),
        ]
