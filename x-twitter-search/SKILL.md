---
name: x-twitter-search
description: Search X/Twitter in real-time using the X API. Find tweets, trends, and discussions by keyword, handle, and time range.
---

# X Twitter Search

通过 X API 原生接口实时搜索推文，支持关键词、用户、时间范围过滤。

## Setup

1. 在 [console.x.com](https://console.x.com) 获取 X API Bearer Token
2. 复制 `config.json.template` 为 `config.json`，填入 Token：

```json
{
  "x_bearer_token": "YOUR-BEARER-TOKEN-HERE",
  "default_days": 7,
  "max_results": 20
}
```

也可通过环境变量配置（config.json 优先）：
```bash
export X_BEARER_TOKEN="YOUR-BEARER-TOKEN"
```

> [!NOTE]
> X API 使用按量付费模式，无需订阅。Recent Search 端点最多支持 7 天内的推文。

## Commands

### 基本搜索
```bash
python3 {baseDir}/scripts/search.py "AI video editing"
```

### 获取用户推文
```bash
python3 {baseDir}/scripts/search.py --user elonmusk                  # 获取用户最新推文
python3 {baseDir}/scripts/search.py --user @OpenAI "AI"              # 搜索用户推文中包含关键词的
python3 {baseDir}/scripts/search.py --user elonmusk --days 3         # 最近 3 天的推文
```

### 时间过滤
```bash
python3 {baseDir}/scripts/search.py --days 7 "breaking news"
python3 {baseDir}/scripts/search.py --days 1 "trending today"
```

### 用户过滤
```bash
python3 {baseDir}/scripts/search.py --handles @elonmusk,@OpenAI "AI announcements"
python3 {baseDir}/scripts/search.py --exclude @bots "real discussions"
```

### 输出格式
```bash
python3 {baseDir}/scripts/search.py --json "topic"        # 完整 JSON 响应
python3 {baseDir}/scripts/search.py --compact "topic"     # 仅推文，无额外信息
python3 {baseDir}/scripts/search.py --links-only "topic"  # 仅输出推文链接
python3 {baseDir}/scripts/search.py --max 50 "topic"      # 更多结果（最大 100）
```

## Options

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--user` | `-u` | 获取指定用户推文（@ 可选） | - |
| `--days` | `-d` | 搜索最近 N 天（最大 7） | 7 |
| `--handles` | | 仅搜索指定用户（逗号分隔） | - |
| `--exclude` | `-e` | 排除指定用户 | - |
| `--max` | `-n` | 最大结果数（最大 100） | 20 |
| `--compact` | `-c` | 精简输出 | false |
| `--links-only` | `-l` | 仅输出链接 | false |
| `--json` | `-j` | 输出完整 JSON | false |

## Environment Variables

- `X_BEARER_TOKEN` — X API Bearer Token（必需）
- `TWITTER_BEARER_TOKEN` — 备选环境变量名
- `SEARCH_X_DAYS` — 默认搜索天数（默认 7）
