"""Windchill Skill 测试。"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from zhixing.plugins import auto_register_skill


def test_skill_import():
    """验证 Skill 可导入。"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from windchill_skill import WindchillSkill

    skill = WindchillSkill()
    assert skill.name == "windchill"
    assert skill.version == "2.0.0"
    print(f"✅ Skill 导入成功: {skill.name} v{skill.version}")
    return skill


def test_auto_register():
    """验证 cmd_* 方法自动注册。"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from windchill_skill import WindchillSkill

    skill = WindchillSkill()
    commands, schemas = auto_register_skill(skill)

    print(f"📊 自动注册: {len(commands)} 个命令")
    assert len(commands) >= 30, f"应至少注册 30 个命令，实际 {len(commands)}"

    # 验证关键命令存在
    key_commands = [
        "query_by_number", "query_bom", "query_workitems",
        "create_part", "approve_task", "server_status",
        "server_oracle", "oracle_sql", "view_log",
        "desktop_agent_list", "send_wecom_message",
    ]
    for name in key_commands:
        assert name in commands, f"缺少命令: {name}"
    print(f"✅ 关键命令检查通过 ({len(key_commands)}/{len(key_commands)})")

    # 验证 schema 生成
    assert "query_by_number" in schemas
    schema = schemas["query_by_number"]
    assert "number" in str(schema)
    print(f"✅ Schema 自动生成: query_by_number → {schema}")

    return commands, schemas


def test_categories():
    """验证命令全部分类。"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from windchill_skill import WindchillSkill

    skill = WindchillSkill()
    commands, _ = auto_register_skill(skill)

    # 按功能分类计数
    query_ops = [c for c in commands if c.startswith("query_") or c.startswith("get_") or c.startswith("list_") or c.startswith("view_")]
    action_ops = [c for c in commands if c.startswith("create_") or c.startswith("delete_") or c.startswith("revise_") or c.startswith("update_") or c.startswith("add_") or c.startswith("edit_") or c.startswith("obsolete_")]
    workflow_ops = [c for c in commands if c.endswith("_task") or c == "save_workitem"]
    system_ops = [c for c in commands if c.startswith("server_") or c.startswith("worker_") or c.startswith("system_") or c.startswith("set_") or c.startswith("add_worker")]
    oracle_ops = [c for c in commands if "oracle" in c]
    event_ops = [c for c in commands if "event" in c or "subscription" in c]
    desktop = [c for c in commands if "desktop" in c]
    gen_ops = [c for c in commands if c.startswith("generate_")]
    other = [c for c in commands if c not in query_ops + action_ops + workflow_ops + system_ops + oracle_ops + event_ops + desktop + gen_ops]

    print(f"\n📊 命令分类统计:")
    print(f"   查询类:           {len(query_ops):2d}")
    print(f"   操作类(CRUD):      {len(action_ops):2d}")
    print(f"   审批/工作流:       {len(workflow_ops):2d}")
    print(f"   系统管理:          {len(system_ops):2d}")
    print(f"   Oracle DBA:        {len(oracle_ops):2d}")
    print(f"   事件订阅:          {len(event_ops):2d}")
    print(f"   桌面代理:          {len(desktop):2d}")
    print(f"   生成XML工具:       {len(gen_ops):2d}")
    if other:
        print(f"   其他:              {len(other):2d} → {other}")

    assert len(query_ops) >= 12
    assert len(action_ops) >= 7
    assert len(workflow_ops) >= 4
    print(f"\n✅ 分类验证通过 ({len(commands)} 总计)")


def test_nl_rules():
    """验证自然语言规则。"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from windchill_skill import WindchillSkill

    skill = WindchillSkill()
    rules = skill.get_nl_rules()
    assert len(rules) >= 8, f"应至少 8 条 NL 规则，实际 {len(rules)}"
    print(f"✅ NL 规则: {len(rules)} 条")


if __name__ == "__main__":
    skill = test_skill_import()
    cmd, schema = test_auto_register()
    test_categories()
    test_nl_rules()
    print(f"\n{'='*40}")
    print("🎉 Windchill Skill 测试全部通过")
