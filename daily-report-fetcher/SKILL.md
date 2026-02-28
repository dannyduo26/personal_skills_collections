---
name: daily-report-fetcher
description: Fetches the daily report from the custom API endpoint (http://175.24.206.252/api/report/YYYY-MM-DD). Use when the user asks for "daily report", "today's news", or "today's message".
---

# Daily Report Fetcher

This skill retrieves a daily summary/report from a specific API server. It automatically uses the current date to construct the request URL.

## Usage

```bash
python3 scripts/fetch_report.py
```

## Logic
1.  Generates today's date (e.g., `2026-01-27`).
2.  Requests `http://175.24.206.252/api/report/2026-01-27`.
3.  Outputs the JSON response.
