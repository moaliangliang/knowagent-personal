---
name: windchill
description: >
  PTC Windchill PLM Integration — 56 个命令覆盖零件/BOM/工作流/文档/
  变更管理/事件订阅/Worker 管理/系统管理/Oracle DBA
version: 2.0.0
author: ZhiXing
triggers:
  - windchill
  - 零件
  - part
  - BOM
  - 图纸
  - drawing
  - PLM
  - 审批
  - approve
  - 变更
  - change
  - oracle
  - 数据库
  - worker
  - 日志
  - log
---

# Windchill PLM Skill

PTC Windchill 全功能集成 Skill。支持两种模式：

- **bridge 模式**（个人版默认）：通过 HTTP 桥接后端 ZhiXing 服务
- **direct 模式**（后端）：直接使用 `WindchillODataClient` 操作 Windchill

## 安装

```bash
# 从 GitHub 安装
ka skill install gh:knowagent/windchill-skill

# 从本地安装
ka skill install /path/to/windchill-skill/windchill_skill.py

# 查看已安装
ka skill list
```

## 配置

编辑 `~/.zhixing/skills/windchill_skill.yaml`：

```yaml
mode: bridge  # bridge 或 direct

# bridge 模式：个人版通过后端 HTTP 代理
bridge:
  url: http://localhost:8000

# direct 模式：后端直接连接 Windchill OData
direct:
  host: 61.169.97.58
  http_port: "7380"
  ssh_port: "2222"
  odata_user: wcadmin
  odata_password: ""
  ssh_user: administrator
  ssh_password: ""
  windchill_home: "D:/ptc/Windchill_12.1/Windchill"
  oracle_home: "D:/app/oracle/product/12.1.0/dbhome_1"
```

## 命令分组

| 分组 | 命令数 | 说明 |
|------|:------:|------|
| 查询类 | 17 | 查零件/BOM/文档/用户/组/任务/变更/日志 |
| 操作类 | 9 | 创建/删除/修订/更新物料/文档/BOM |
| 审批工作流 | 4 | 审批/驳回/转派/暂存 |
| 系统管理 | 11 | MethodServer/Worker/首选项/克隆/重托管 |
| Oracle DBA | 3 | 数据库状态/SQL/备份 |
| 实施工具 | 6 | 生成 XML (类型/分类/生命周期/OIR) |
| 事件订阅 | 3 | 创建/删除/查询订阅 |
| 桌面代理 | 2 | 列出手/远程命令 |
| 其他 | 1 | 企业微信通知 |
