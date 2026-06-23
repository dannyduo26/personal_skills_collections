---
name: napcat-history
description: "使用 NapCat (OneBot 11) API 获取和管理 QQ 群历史消息。支持分页、群组过滤和本地 JSON 日志保存。"
---

# NapCat History Fetcher

## 概览 (Overview)
此技能允许您通过 NapCat (OneBot 11) HTTP API 检索、分页和存储 QQ 群的历史消息。

## 核心功能 (Core Features)
1. **获取群列表**：快速查看已加入的群组、成员数量和群 ID。
2. **分页历史检索**：通过迭代 `message_seq` 并配合 `reverseOrder` 获取更早的历史记录。
3. **可配置采集**：设置页数、每页消息数以及请求延迟，兼顾速度与安全。
4. **本地日志**：消息以结构化 JSON 格式保存到 `logs/` 目录下的 `.log` 文件中。

## 使用指南 (Usage Guide)

### 1) 配置 (Configuration)
确保项目根目录下的 `config.json` 配置正确：
- `apiUrl`: NapCat 实例的 HTTP API 地址。
- `accessToken`: (可选) 授权令牌。
- `groupId`: 目标群号。

### 2) 获取群 ID (Get Group IDs)
运行列表脚本以查找群号：
```bash
python scripts/get_group_list.py
```

### 3) 拉取历史记录 (Fetch History)
使用所需参数运行主脚本：
```bash
# 默认 (10页, 20条/页, 无延迟)
python scripts/get_history.py

# 深度采集 (总计拉取 2000 条，带有安全延迟)
python scripts/get_history.py --pages 20 --count 100 --delay 1.5
```

## 命令行参数 (Parameters)
- `-p, --pages`: 获取的页数。
- `-c, --count`: 每页获取的消息数量（建议不超过 100）。
- `-d, --delay`: 分页请求之间的延迟秒数（大规模采集建议设置 1.0 以上）。
