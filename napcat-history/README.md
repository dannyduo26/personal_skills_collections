# NapCat History Fetcher

一个用于获取 NapCat (OneBot 11) 群历史消息的 Python 项目，支持分页抓取、多页配置及安全延迟。

## 🛠️ 配置

在根目录下的 `config.json` 中配置 API 信息与目标群号：

```json
{
    "apiUrl": "http://127.0.0.1:3000",
    "accessToken": "你的密钥(如果有)",
    "groupId": 123456789
}
```

## 🚀 使用方法

### 1. 获取群组列表
若不确定群号，可运行此脚本列出所有加入的群名及群号：
```bash
python scripts/get_group_list.py
```

### 2. 拉取历史消息
运行主脚本开始采集，消息将自动保存至 `logs/` 目录：
```bash
# 默认拉取 10 页 (每页 20 条)
python scripts/get_history.py

# 深度采集：拉取 20 页，每页 100 条，每页间隔延迟 1.5 秒
python scripts/get_history.py -p 20 -c 100 -d 1.5
```

## 📋 命令行参数

- `-p, --pages`: 获取总页数 (默认 10)
- `-c, --count`: 每页获取的消息条数 (默认 20，建议最大 100)
- `-d, --delay`: 请求之间的延迟秒数 (默认 0，建议 1.0+)

## ✨ 功能特点

- **分页连续抓取**：自动提取消息序号配合 `reverseOrder` 机制，确保历史记录无缝衔接。
- **本地 JSON 日志**：采集结果自动保存至 `logs/` 文件夹下的 `.log` 文件中。
- **采集安全**：内置请求延迟机制，降低大规模采集时触发风控的概率。
- **零依赖**：仅使用 Python 原生 `urllib` 库，无需安装任何第三方依赖。
