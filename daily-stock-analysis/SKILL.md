---
name: daily-stock-analysis
description: Analyze stocks using a local Python service (A-shares, HK, US). Provides asynchronous analysis reports via API integration.
---

# SKILL.md - Daily Stock Analysis (API Integration)

This skill integrates the `daily-stock-analysis` system into Clawdbot by calling its local API (port 8000). It allows for rapid stock analysis and automatic synchronization to configured channels (like WeCom).

## Capabilities
- **API-Driven Analysis**: Submit stock codes to the local WebUI service for asynchronous processing.
- **Multi-Market Support**: A-shares (6 digits), HK stocks (e.g., `hk00700`), and US stocks (e.g., `AAPL`).
- **Synchronized Notification**: Results are automatically pushed to configured external channels (WeCom, Feishu, etc.) and tracked in the local database.

## Prerequisites
The WebUI service must be running. If not started, use `clawdbot exec` to run:
`python3 /data/app/daily_stock_analysis/main.py --webui-only`

## Usage
### 1. Analyze Stocks
User: "分析股票 600519, AAPL"
Agent:
1. Call `GET http://127.0.0.1:8000/analysis?code={code}&report_type=full`.
2. Report the task submission status to the user.

### 2. Check Task Status
User: "查看任务 600519_20260130_..."
Agent:
1. Call `GET http://127.0.0.1:8000/task?id={task_id}`.
2. If completed, show the summary results.

## Implementation Details
Use `exec` with `curl` to interact with the API (web_fetch blocks localhost):

```bash
# Analyze a stock (asynchronous)
curl "http://127.0.0.1:8000/analysis?code=600519&report_type=full"

# List tasks
curl "http://127.0.0.1:8000/tasks?limit=5"

# Health check
curl "http://127.0.0.1:8000/health"
```

## Constraints
- Ensure the API is reachable.
- Analysis is asynchronous; the API returns a `task_id`.
- The actual detailed report will be delivered via the configured Webhook (e.g., WeCom).
