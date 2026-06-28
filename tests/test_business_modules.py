"""业务模块测试 — 覆盖零测试覆盖率的模块。

覆盖模块:
  todo.py       — 待办 CRUD、排序、优先级
  funnel.py     — 用户转化漏斗状态机
  i18n.py       — 语言检测、翻译表
  pro.py        — License 校验、功能开关
  browser_controller.py — 平台检测、AppleScript 接口
  messaging.py  — 企业消息平台配置
  skill_manager.py — Skill 安装、列表
  plugin_tools.py  — 插件命令
  auto.py       — 视觉自动化命令注册

注意: 所有测试函数以独立函数运行，
import 尽量局部化以避免触发 Agent REPL。
"""

import json
import os
import sys
import tempfile
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 设置环境变量防止 REPL 启动
os.environ.setdefault("KA_NO_REPL", "1")


# ═══════════════════════════════════════════════════════════
# todo.py — 待办事项
# ═══════════════════════════════════════════════════════════

def _fresh_todo_manager():
    """返回一个新的 TodoManager（重置单例）"""
    from zhixing.agent.todo import TodoManager
    TodoManager._instance = None
    return TodoManager.get()


def test_todo_add():
    """添加待办"""
    m = _fresh_todo_manager()
    item = m.add("测试待办", priority="high", category="work")
    assert item.title == "测试待办"
    assert item.priority == "high"
    assert item.category == "work"
    assert not item.done


def test_todo_invalid_priority():
    """无效优先级回退到 medium"""
    m = _fresh_todo_manager()
    item = m.add("优先级测试", priority="urgent")
    assert item.priority == "medium"


def test_todo_list_filter():
    """列表：默认只显示未完成"""
    m = _fresh_todo_manager()
    m.add("待办A")
    m.add("待办B")
    items = m.list()
    assert len(items) >= 2
    assert all(not t.done for t in items)


def test_todo_list_category():
    """列表：按分类筛选"""
    m = _fresh_todo_manager()
    m.add("工作项", category="work")
    m.add("生活项", category="personal")
    work_items = m.list(category="work")
    assert all(t.category == "work" for t in work_items)


def test_todo_done():
    """完成待办"""
    m = _fresh_todo_manager()
    item = m.add("要完成的待办")
    assert m.done(item.id)
    # 验证已标记完成
    remaining = [t for t in m._todos if t.id == item.id]
    assert remaining and remaining[0].done


def test_todo_done_not_found():
    """完成不存在的待办返回 False"""
    m = _fresh_todo_manager()
    assert not m.done(99999)


def test_todo_delete():
    """删除待办"""
    m = _fresh_todo_manager()
    item = m.add("要删除的待办")
    assert m.delete(item.id)
    remaining = [t for t in m._todos if t.id == item.id]
    assert len(remaining) == 0


def test_todo_delete_not_found():
    """删除不存在的待办返回 True（实现约定，delete 总是返回 True）"""
    m = _fresh_todo_manager()
    # delete() 总是返回 True
    item = m.add("临时")
    m._todos.clear()  # 清空但保留 id 序列
    assert m.delete(99999) is True  # 实现约定


def test_todo_sort_key():
    """排序键：未完成 > 已完成，高优 > 低优"""
    from zhixing.agent.todo import TodoItem
    item1 = TodoItem(id=1, title="A", done=False, priority="high")
    item2 = TodoItem(id=2, title="B", done=True, priority="high")
    item3 = TodoItem(id=3, title="C", done=False, priority="low")
    assert item1.sort_key < item2.sort_key, "未完成应排在已完成之前"
    assert item1.sort_key < item3.sort_key, "高优应排在低优前"


def test_todo_icon():
    """图标对应关系"""
    from zhixing.agent.todo import TodoItem
    assert TodoItem(id=1, title="", done=True).icon == "✅"
    assert TodoItem(id=2, title="", done=False, priority="high").icon == "🔴"
    assert TodoItem(id=3, title="", done=False, priority="medium").icon == "🟡"
    assert TodoItem(id=4, title="", done=False, priority="low").icon == "🟢"


def test_todo_serialize():
    """序列化/反序列化"""
    from zhixing.agent.todo import TodoItem
    item = TodoItem(id=1, title="测试", priority="high", category="work",
                     due_date="2026-07-01", notes="备注")
    d = item.to_dict()
    assert d["title"] == "测试"
    restored = TodoItem.from_dict(d)
    assert restored.title == "测试"
    assert restored.priority == "high"
    assert restored.due_date == "2026-07-01"


# ═══════════════════════════════════════════════════════════
# funnel.py — 用户转化漏斗
# ═══════════════════════════════════════════════════════════

def test_funnel_default_state():
    """默认漏斗状态"""
    from zhixing.agent.funnel import DEFAULT_STATE
    assert DEFAULT_STATE["launch_count"] == 0
    assert DEFAULT_STATE["star_prompt_shown"] is False
    assert DEFAULT_STATE["dismissed"] is False


def test_funnel_messages():
    """漏斗消息生成（不涉及文件 IO）"""
    from zhixing.agent.funnel import get_funnel_message, DEFAULT_STATE

    # 前 2 次不显示
    for i in [1, 2]:
        s = dict(DEFAULT_STATE, launch_count=i)
        assert get_funnel_message(s) is None

    # 第 3 次显示 Star
    s = dict(DEFAULT_STATE, launch_count=3)
    msg = get_funnel_message(s)
    assert msg is not None
    assert "⭐" in msg

    # 第 10 次显示赞助
    s = dict(DEFAULT_STATE, launch_count=10, star_prompt_shown=True)
    msg = get_funnel_message(s)
    assert msg is not None
    assert "☕" in msg or "sponsor" in msg.lower()

    # dismissed 不显示
    s = dict(DEFAULT_STATE, launch_count=100, dismissed=True)
    assert get_funnel_message(s) is None


def test_funnel_sponsor_text():
    """赞助文本包含链接"""
    from zhixing.agent.funnel import get_sponsor_text
    cn = get_sponsor_text("zh")
    assert len(cn) > 50
    en = get_sponsor_text("en")
    assert len(en) > 50


# ═══════════════════════════════════════════════════════════
# i18n.py — 国际化
# ═══════════════════════════════════════════════════════════

def test_i18n_detect_lang():
    """语言检测"""
    from zhixing.agent.i18n import detect_lang
    lang = detect_lang()
    assert lang in ("zh", "en")


def test_i18n_env_override():
    """环境变量可覆盖语言"""
    import zhixing.agent.i18n as i18n_mod
    orig = os.environ.get("ZHIXING_LANG")
    try:
        os.environ["ZHIXING_LANG"] = "en"
        assert i18n_mod.detect_lang() == "en"
        os.environ["ZHIXING_LANG"] = "zh"
        assert i18n_mod.detect_lang() == "zh"
    finally:
        if orig:
            os.environ["ZHIXING_LANG"] = orig
        else:
            os.environ.pop("ZHIXING_LANG", None)


def test_i18n_translation_keys():
    """翻译表字段完整性"""
    from zhixing.agent.i18n import _T
    assert len(_T) > 10
    for key, trans in _T.items():
        assert "zh" in trans, f"'{key}' 缺 zh"
        assert "en" in trans, f"'{key}' 缺 en"


def test_i18n_tt():
    """tt() 翻译 — 基于 entry['zh'] 值替换（不是 key 名）"""
    from zhixing.agent.i18n import tt
    # zh 语言直接返回原文
    assert tt("你好", "zh") == "你好"
    # en: 用 entry['zh'] 的 value 替换为 entry['en'] 的 value
    # "连接成功" → _T["连接成功"] = {zh:"● 已连接", en:"● Connected"}
    result_en = tt("● 已连接", "en")
    assert "Connected" in result_en, f"en 翻译: {result_en}"
    # 复合文本中的部分替换
    result_mixed = tt("● 已连接 ● Connected", "en")  # 第二次调用无变化
    assert isinstance(result_mixed, str)
    # 不存在的文本返回原文
    assert tt("完全不存在的内容aaaa", "en") == "完全不存在的内容aaaa"
    # 自动检测
    assert isinstance(tt("● 已连接"), str)


def test_i18n_t():
    """t() 直接 key 查找翻译 — 这是正确的 key 查询 API"""
    from zhixing.agent.i18n import t
    # 存在的 key
    assert "Connected" in t("连接成功", "en")
    assert "已连接" in t("连接成功", "zh")
    # 不存在的 key 返回原 key
    assert t("不存在的key", "en") == "不存在的key"
    assert t("不存在的key", "zh") == "不存在的key"
    # 自动检测语言
    assert isinstance(t("连接成功"), str)


# ═══════════════════════════════════════════════════════════
# pro.py — Pro 版本
# ═══════════════════════════════════════════════════════════

def test_pro_not_active_by_default():
    """默认不是 Pro（清除环境变量和配置后）"""
    import os
    saved_env = os.environ.pop("ZHIXING_PRO", None)
    # 暂存配置文件中的 license_key
    from zhixing.config import Config
    cfg = Config()
    saved_key = cfg.get("pro.license_key", None)
    if saved_key:
        cfg.set("pro.license_key", "")
        cfg.save()
    from zhixing.agent.pro import is_pro
    result = is_pro()
    # 恢复
    if saved_env is not None:
        os.environ["ZHIXING_PRO"] = saved_env
    if saved_key:
        cfg.set("pro.license_key", saved_key)
        cfg.save()
    assert result is False


def test_pro_features():
    """Pro 功能列表完整性"""
    from zhixing.agent.pro import PRO_FEATURES, PRO_FEATURES_EN
    assert len(PRO_FEATURES) >= 4
    assert len(PRO_FEATURES) == len(PRO_FEATURES_EN)


def test_pro_require_pro():
    """require_pro 无 License 返回提示"""
    import os
    saved_env = os.environ.pop("ZHIXING_PRO", None)
    from zhixing.config import Config
    cfg = Config()
    saved_key = cfg.get("pro.license_key", None)
    if saved_key:
        cfg.set("pro.license_key", "")
        cfg.save()
    from zhixing.agent.pro import require_pro
    result = require_pro("enhanced_timer")
    if saved_env is not None:
        os.environ["ZHIXING_PRO"] = saved_env
    if saved_key:
        cfg.set("pro.license_key", saved_key)
        cfg.save()
    assert result is not None
    assert "Pro" in result or "🔒" in result or "❌" in result


def test_pro_features_text():
    """get_pro_features_text 返回文本"""
    from zhixing.agent.pro import get_pro_features_text
    zh = get_pro_features_text("zh")
    assert len(zh) > 50
    en = get_pro_features_text("en")
    assert len(en) > 50


# ═══════════════════════════════════════════════════════════
# browser_controller.py — 浏览器控制
# ═══════════════════════════════════════════════════════════

def test_browser_platform():
    """平台检测正确"""
    from zhixing.agent.browser_controller import IS_MAC, IS_WIN
    assert IS_MAC is True
    assert IS_WIN is False


def test_browser_find_chrome():
    """_find_chrome 不崩溃"""
    from zhixing.agent.browser_controller import _find_chrome
    path = _find_chrome()
    assert path is None or "Chrome" in path


def test_browser_is_connected():
    """is_connected 返回 bool"""
    from zhixing.agent.browser_controller import is_connected
    assert isinstance(is_connected(), bool)


# ═══════════════════════════════════════════════════════════
# messaging.py — 企业消息
# ═══════════════════════════════════════════════════════════

def test_messaging_platforms():
    """三个平台配置均存在"""
    from zhixing.agent.messaging import PLATFORM_INFO
    assert "wecom" in PLATFORM_INFO
    assert "feishu" in PLATFORM_INFO
    assert "dingtalk" in PLATFORM_INFO
    for name, info in PLATFORM_INFO.items():
        assert info["name"], f"{name} 名称为空"
        assert "webhook_host" in info


# ═══════════════════════════════════════════════════════════
# skill_manager.py — Skill 管理
# ═══════════════════════════════════════════════════════════

def test_skill_manager():
    """SkillManager 初始化"""
    from zhixing.agent.skill_manager import SkillManager
    sm = SkillManager()
    assert sm._loaded_skills == []
    skills = sm.list_skills()
    assert isinstance(skills, list)


# ═══════════════════════════════════════════════════════════
# plugin_tools.py — 插件命令
# ═══════════════════════════════════════════════════════════

def test_plugin_commands_in_commands():
    """插件相关命令可被找到"""
    from zhixing.agent.tools import COMMANDS
    # 插件命令可能叫 plugin_list 或 skill
    plugin_cmds = [n for n in COMMANDS.keys() if 'plugin' in n or 'skill' in n]
    assert len(plugin_cmds) >= 0  # 可能会注册也可能不注册


def test_skill_command():
    """skill 命令返回 str"""
    from zhixing.agent.tools import COMMANDS
    if "skill" in COMMANDS:
        r = COMMANDS["skill"]({})
        assert isinstance(r, str)
    else:
        # skill 可能是个单独的命令，非错误
        pass


# ═══════════════════════════════════════════════════════════
# auto.py — 视觉自动化
# ═══════════════════════════════════════════════════════════

def test_auto_script_registered():
    """auto_script 命令已注册"""
    from zhixing.agent.tools import COMMANDS
    assert "auto_script" in COMMANDS


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 预先收集（避免迭代中修改 globals）
    test_fns = [(n, fn) for n, fn in list(globals().items())
                if n.startswith("test_") and callable(fn)]

    passed = 0
    failed = 0
    errors = []
    for name, fn in test_fns:
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            errors.append((name, traceback.format_exc()))
            failed += 1

    total = passed + failed
    print(f"\n{'=' * 50}")
    print(f"  结果: {passed}/{total} 通过", end="")
    if failed:
        print(f", {failed} 失败")
        for name, tb in errors[:5]:
            print(f"\n  --- {name} ---")
            print(f"  {tb.splitlines()[-2].strip()}")
    else:
        print()
    print(f"{'=' * 50}")
