---
name: finance-research-report
description: Collect daily Chinese broker research reports from public Eastmoney research-report pages, deduplicate them with SQLite, and send grouped WeCom robot Markdown summaries. Use when Codex or OpenClaw needs to run a scheduled finance research report digest covering stock, industry, and macro research reports.
---

# Finance Research Report

## Overview

Use this skill to run a daily public research-report collection task for OpenClaw. The bundled script collects Eastmoney stock, industry, and macro research reports, stores metadata in SQLite for deduplication, and sends new items to a WeCom group robot as category-grouped Markdown messages.

## Quick Start

Copy `references/config.example.yaml` to your runtime config path, then set the webhook secret values with environment variables:

```powershell
$env:WEWORK_BOT_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
$env:WEWORK_BOT_SECRET="optional-signing-secret"
python scripts/run_daily_reports.py --config config.yaml --dry-run
python scripts/run_daily_reports.py --config config.yaml
```

For OpenClaw, schedule the same command once per day in China time, for example at `08:30`.

## Workflow

1. Run `scripts/run_daily_reports.py` with `--config`.
2. Use `--date YYYY-MM-DD` to pin the report date when replaying a day.
3. Use `--lookback-days 1` for the normal daily run; increase it only when backfilling.
4. Use `--dry-run` before enabling the robot. Dry run fetches and formats results but does not write SQLite or send WeCom messages.
5. Keep the generated SQLite database between runs so duplicate reports are not pushed again.

## Data Sources

The default categories are:

- `stock`: `https://data.eastmoney.com/report/stock.jshtml`
- `industry`: `https://data.eastmoney.com/report/industry.jshtml`
- `macro`: `https://data.eastmoney.com/report/macresearch.jshtml`

The script calls Eastmoney's public report API first and keeps each page URL as a fallback reference. If Eastmoney changes API fields, update the category `api_url`, `q_type`, or normalization aliases in `scripts/run_daily_reports.py`.

## Output Behavior

- Store only report metadata and public links; do not download or redistribute PDF bodies.
- Normalize each report to title, category, broker, analyst, date, target/topic, rating, URL, and source.
- Deduplicate with `source + category + title + broker + report_date`.
- Send separate WeCom Markdown messages for stock reports, industry reports, and macro research by default.
- Allow empty macro ratings.
- Continue other categories when one category fails, and log failures.

## Resources

- `scripts/run_daily_reports.py`: deterministic daily collector and notifier.
- `references/config.example.yaml`: copyable configuration template.

## Validation

Run the built-in offline checks after editing the script:

```powershell
python scripts/run_daily_reports.py --self-test
```
