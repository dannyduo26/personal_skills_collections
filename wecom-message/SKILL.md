---
name: wecom-message
description: 发送消息到企业微信应用。支持文本和 Markdown 格式，适用于任务完成通知、告警推送等场景。
---

# 企业微信消息发送 Skill

通过企业微信应用 API 向成员/部门发送消息。

## 配置

`config.json` 中存储企业微信凭证：
- `corpid`：企业 ID
- `corpsecret`：应用的 Secret
- `agentid`：应用的 AgentID
- `touser`：默认收件人（默认 `@all` 发送给所有人）

## 使用方法

```bash
# 发送文本消息（使用 config.json 中的默认配置）
python3 scripts/send.py --title "任务完成" --body "爬虫已完成，共抓取 100 条数据。"

# 发送 Markdown 消息
python3 scripts/send.py --title "每日报告" --body "# 报告\n- 成功: 98\n- 失败: 2" --msgtype markdown

# 发送图片消息（本地图片，支持 jpg/png/gif/bmp，最大 10MB）
python3 scripts/send.py --msgtype image --image /path/to/image.png

# 发送图文消息（News 结构：标题 + 描述 + 图片）
python3 scripts/send.py --msgtype news --title "报表摘要" --body "详细数据内容..." --image /path/to/image.png

# 发送模板卡片消息（更现代的卡片布局，支持长文本分项显示）
python3 scripts/send.py --msgtype template_card --title "每日报告" --body "第一行内容\n第二行内容" --image /path/to/image.png

# 发送 Markdown 消息（不支持图片，仅限文本格式）
python3 scripts/send.py --title "提醒" --body "请查看最新结果" --touser "UserID1|UserID2"

# 获取企业微信回调 IP 段（用于防火墙配置）
python3 scripts/send.py --get-ips
```

## 配置消息接收服务器（IP 白名单验证前置步骤）

企业微信后台配置"接收消息服务器"时，需要先通过 URL 验证。启动本地服务器：

```bash
# 安装 AES 解密依赖
pip install pycryptodome

# 启动服务器（默认端口 8088）
python3 scripts/server.py

# 自定义端口
python3 scripts/server.py --port 80
```

在 `config.json` 中添加以下字段（从企业微信后台应用配置页获取）：
- `callback_token`：企业微信后台填写的 Token
- `encoding_aes_key`：企业微信后台生成的 EncodingAESKey

启动后将公网 IP/域名填写到企业微信后台的"接收消息 URL"，点击验证即可通过。
