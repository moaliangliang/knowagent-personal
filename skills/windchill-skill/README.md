# 🌀 Windchill PLM Skill

PTC Windchill 全功能集成 Skill for ZhiXing。

## 安装

```bash
# 从 GitHub 安装
ka skill install gh:knowagent/windchill-skill

# 从本地安装
ka skill install /path/to/windchill_skill.py
```

## 配置

首次使用前，创建 `~/.zhixing/windchill_skill.yaml`：

```yaml
mode: bridge  # bridge(个人版) 或 direct(后端)
bridge:
  url: http://localhost:8000  # 后端 ZhiXing 地址
```

配置自动生效。

## 命令分类

| 分组 | 数量 | 说明 |
|------|:----:|------|
| 查询类 | 18 | 按编号/名称查零件，BOM 展开，文档/用户/组/任务/变更查询 |
| 操作类 | 14 | 创建/删除/修订/更新 物料/文档/BOM，安全标签 |
| 审批/工作流 | 4 | 审批/驳回/转派/暂存 |
| 系统管理 | 9 | 服务器状态，MethodServer，Worker，首选项，系统迁移 |
| Oracle DBA | 3 | 数据库状态/SQL/备份 |
| 事件订阅 | 2 | 创建/查询事件订阅 |
| 桌面代理 | 2 | 列出手/远程命令 |
| 生成工具 | 2 | 类型/生命周期 XML |
| 其他 | 1 | 企业微信通知 |
| **总计** | **56** | |

## 使用示例

```bash
# 查询
ka 查零件 number=ABC-123
ka 查BOM part_number=ABC-123
ka 待办任务
ka 查文档

# 操作
ka 创建物料 name=新零件 number=NEW-001
ka 审批 task_id=123 comment="已确认"
ka 作废物料 number=OBS-001

# 系统
ka 服务器状态
ka oracle status
ka 日志
ka 查看日志 filename=methodserver.log.0

# 别名简写（Windchill 通用入口）
ka windchill status
ka windchill parts
ka windchill bom number=ABC
```

## 架构

```
用户输入 "查零件 ABC-123"
  │
  ├─ Skill NL 规则匹配 → cmd_query_by_number("ABC-123")
  │
  ├─ bridge 模式 (个人版)
  │   └─ HTTP → knowagent 后端 /api/agent/windchill
  │       └─ WindchillODataClient → Windchill OData API
  │
  └─ direct 模式 (后端)
      └─ WindchillODataClient → Windchill OData API
```

## 开发

```bash
# 运行测试
python skills/windchill-skill/tests/test_skill.py

# 安装到用户目录
cp skills/windchill-skill/windchill_skill.py ~/.zhixing/skills/
```
