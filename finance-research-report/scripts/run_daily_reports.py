#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily Eastmoney broker research report collector."""

import argparse
import base64
import datetime as dt
import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


CATEGORY_LABELS = {
    "stock": "个股研报",
    "industry": "行业研报",
    "macro": "宏观研究",
}

DEFAULT_CONFIG = {
    "sources": {
        "eastmoney": {
            "enabled": True,
            "page_size": 50,
            "max_pages": 3,
            "categories": ["stock", "industry", "macro"],
            "api_url": "https://reportapi.eastmoney.com/report/list",
            "pages": {
                "stock": "https://data.eastmoney.com/report/stock.jshtml",
                "industry": "https://data.eastmoney.com/report/industry.jshtml",
                "macro": "https://data.eastmoney.com/report/macresearch.jshtml",
            },
            "q_types": {
                "stock": 0,
                "industry": 1,
                "macro": 3,
            },
        }
    },
    "filters": {
        "broker_allowlist": [],
        "keyword_allowlist": [],
        "keyword_blocklist": [],
        "max_items_per_category": 20,
        "max_total_items": 60,
    },
    "storage": {
        "sqlite_path": "data/reports.sqlite",
        "log_path": "logs/daily-broker-reports.log",
    },
    "notification": {
        "provider": "wework",
        "webhook_env": "WEWORK_BOT_WEBHOOK",
        "secret_env": "WEWORK_BOT_SECRET",
        "notify_empty": False,
        "group_by_category": True,
        "message_interval_seconds": 1,
        "max_markdown_chars": 3800,
    },
}


@dataclass
class Report:
    source: str
    category: str
    title: str
    broker: str
    analyst: str
    report_date: str
    target: str
    rating: str
    url: str
    raw: Dict[str, Any]

    @property
    def dedupe_key(self) -> str:
        # 中文注释：用稳定字段生成去重键，避免同一研报重复推送。
        parts = [self.source, self.category, self.title, self.broker, self.report_date]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Eastmoney broker research reports.")
    parser.add_argument("--config", help="Path to YAML/JSON config.")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD. Defaults to local today.")
    parser.add_argument("--lookback-days", type=int, default=1, help="Days to include, ending at --date.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and format without DB writes or WeCom send.")
    parser.add_argument("--self-test", action="store_true", help="Run offline self tests.")
    return parser.parse_args()


def strip_comment(line: str) -> str:
    in_quote = False
    quote_char = ""
    result = []
    for char in line:
        if char in ("'", '"'):
            if not in_quote:
                in_quote = True
                quote_char = char
            elif quote_char == char:
                in_quote = False
        if char == "#" and not in_quote:
            break
        result.append(char)
    return "".join(result).rstrip()


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if value in ("null", "None", "~"):
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def parse_simple_yaml(text: str) -> Dict[str, Any]:
    # 中文注释：解析配置样例使用的少量 YAML 语法，避免强依赖 PyYAML。
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = strip_comment(raw_line)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError(f"Unsupported YAML indent: {raw_line}")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        stripped = line.strip()
        if ":" not in stripped:
            raise ValueError(f"Unsupported YAML line: {raw_line}")
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            child: Dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = parse_scalar(value)
    return root


def load_config(config_path: Optional[str]) -> Tuple[Dict[str, Any], Path]:
    if not config_path:
        config = DEFAULT_CONFIG.copy()
        return config, Path.cwd()

    path = Path(config_path).expanduser().resolve()
    text = path.read_text(encoding="utf-8")
    data: Dict[str, Any]
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(text) or {}
        except Exception:
            data = parse_simple_yaml(text)
    config = deep_merge(DEFAULT_CONFIG, data)
    config = expand_env_values(config)
    return config, path.parent


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = json.loads(json.dumps(base, ensure_ascii=False))
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def expand_env_values(value: Any) -> Any:
    # 中文注释：支持在配置里写 ${ENV_NAME} 引用环境变量。
    if isinstance(value, dict):
        return {k: expand_env_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env_values(v) for v in value]
    if isinstance(value, str):
        match = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", value)
        if match:
            return os.getenv(match.group(1), "")
    return value


def setup_logging(config: Dict[str, Any], config_dir: Path) -> None:
    log_path = resolve_path(config["storage"]["log_path"], config_dir)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(str(log_path), encoding="utf-8"), logging.StreamHandler(sys.stderr)],
    )


def resolve_path(path_text: str, base_dir: Path) -> Path:
    path = Path(path_text).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def date_range(target_date: str, lookback_days: int) -> Tuple[str, str]:
    end = dt.datetime.strptime(target_date, "%Y-%m-%d").date()
    start = end - dt.timedelta(days=max(lookback_days, 1) - 1)
    return start.isoformat(), end.isoformat()


def http_get_json(url: str, params: Dict[str, Any], referer: str) -> Dict[str, Any]:
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    request = urllib.request.Request(
        full_url,
        headers={
            "User-Agent": "Mozilla/5.0 finance-research-report/1.0",
            "Accept": "application/json,text/javascript,*/*;q=0.8",
            "Referer": referer,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        text = response.read().decode("utf-8", errors="replace")
    return parse_json_or_jsonp(text)


def http_get_text(url: str, referer: str = "https://data.eastmoney.com/report/") -> str:
    # 中文注释：兜底读取页面源码，用于解析页面内嵌的 initdata。
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 finance-research-report/1.0",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Referer": referer,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_json_or_jsonp(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    match = re.search(r"\((\{.*\})\)\s*;?$", text, flags=re.S)
    if match:
        return json.loads(match.group(1))
    raise ValueError("Response is not JSON or JSONP")


def extract_initdata_from_html(html: str) -> Dict[str, Any]:
    match = re.search(r"var\s+initdata\s*=\s*(\{.*?\})\s*;", html, flags=re.S)
    if not match:
        return {}
    return json.loads(match.group(1))


def extract_payload_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    # 中文注释：兼容不同接口包装层，尽量找出列表数据。
    candidates: List[Any] = [
        payload.get("data"),
        payload.get("Data"),
        payload.get("result"),
        payload.get("Result"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict):
            nested = candidate.get("data") or candidate.get("list") or candidate.get("items")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    for value in payload.values():
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return value
    return []


def first_value(raw: Dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = raw.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return ""


def normalize_date(value: str) -> str:
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", value or "")
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    match = re.search(r"(\d{4})(\d{2})(\d{2})", value or "")
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    return ""


def build_report_url(raw: Dict[str, Any], page_url: str) -> str:
    url = first_value(raw, ["url", "URL", "reportUrl", "REPORT_URL", "attachUrl", "ATTACH_URL", "pdfUrl", "PDF_URL"])
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http"):
        return url

    encode_url = first_value(raw, ["encodeUrl", "ENCODE_URL", "infoCode", "INFO_CODE", "art_code", "ART_CODE"])
    if encode_url:
        if encode_url.startswith("http"):
            return encode_url
        suffix = encode_url if encode_url.endswith(".html") else f"{encode_url}.html"
        return "https://data.eastmoney.com/report/info/" + suffix
    return page_url


def normalize_report(raw: Dict[str, Any], category: str, page_url: str) -> Optional[Report]:
    title = first_value(raw, ["title", "TITLE", "reportName", "REPORT_NAME", "notice_title", "NOTICE_TITLE"])
    broker = first_value(raw, ["orgSName", "ORG_S_NAME", "orgName", "ORG_NAME", "institution", "INSTITUTION"])
    analyst = first_value(raw, ["author", "AUTHOR", "researcher", "RESEARCHER", "analyst", "ANALYST"])
    date_text = first_value(raw, ["publishDate", "PUBLISH_DATE", "reportDate", "REPORT_DATE", "datetime", "DATETIME"])
    report_date = normalize_date(date_text)
    rating = first_value(raw, ["emRatingName", "EM_RATING_NAME", "rating", "RATING", "investRating", "INVEST_RATING"])
    target = first_value(
        raw,
        [
            "stockName",
            "SECURITY_NAME_ABBR",
            "industryName",
            "INDUSTRY_NAME",
            "indvInduName",
            "INDV_INDU_NAME",
            "emIndustryName",
            "EM_INDUSTRY_NAME",
            "keyword",
            "KEYWORD",
        ],
    )
    if category == "macro" and not target:
        target = title
    if not title or not report_date:
        return None
    return Report(
        source="eastmoney",
        category=category,
        title=title,
        broker=broker,
        analyst=analyst,
        report_date=report_date,
        target=target,
        rating=rating,
        url=build_report_url(raw, page_url),
        raw=raw,
    )


def fetch_eastmoney_category(config: Dict[str, Any], category: str, begin_date: str, end_date: str) -> List[Report]:
    source_cfg = config["sources"]["eastmoney"]
    api_url = source_cfg["api_url"]
    page_url = source_cfg["pages"][category]
    page_size = int(source_cfg.get("page_size", 50))
    max_pages = int(source_cfg.get("max_pages", 3))
    q_type = source_cfg.get("q_types", {}).get(category, 0)
    reports: List[Report] = []

    for page_no in range(1, max_pages + 1):
        params = {
            "pageSize": page_size,
            "pageNo": page_no,
            "p": page_no,
            "pageNum": page_no,
            "beginTime": begin_date,
            "endTime": end_date,
            "qType": q_type,
            "orgCode": "",
            "code": "*",
            "industryCode": "*",
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
        }
        try:
            payload = http_get_json(api_url, params, page_url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            logging.warning("Fetch failed for %s page %s: %s", category, page_no, exc)
            break

        items = extract_payload_items(payload)
        if not items:
            break
        for item in items:
            report = normalize_report(item, category, page_url)
            if report:
                reports.append(report)
        if len(items) < page_size:
            break

    if reports:
        return reports

    # 中文注释：宏观等页面会直接内嵌 initdata，接口无数据时用页面数据兜底。
    try:
        html = http_get_text(page_url)
        payload = extract_initdata_from_html(html)
        items = extract_payload_items(payload)
        for item in items:
            report = normalize_report(item, category, page_url)
            if report:
                reports.append(report)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logging.warning("Embedded page fallback failed for %s: %s", category, exc)

    return reports


def apply_filters(reports: List[Report], config: Dict[str, Any], begin_date: str, end_date: str) -> List[Report]:
    filters = config.get("filters", {})
    brokers = [str(x) for x in filters.get("broker_allowlist", []) if str(x).strip()]
    keyword_allow = [str(x) for x in filters.get("keyword_allowlist", []) if str(x).strip()]
    keyword_block = [str(x) for x in filters.get("keyword_blocklist", []) if str(x).strip()]
    kept: List[Report] = []

    for report in reports:
        if not (begin_date <= report.report_date <= end_date):
            continue
        searchable = f"{report.title} {report.broker} {report.target}"
        if brokers and not any(broker in report.broker for broker in brokers):
            continue
        if keyword_allow and not any(keyword in searchable for keyword in keyword_allow):
            continue
        if keyword_block and any(keyword in searchable for keyword in keyword_block):
            continue
        kept.append(report)

    return kept


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            dedupe_key TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            broker TEXT,
            analyst TEXT,
            report_date TEXT NOT NULL,
            target TEXT,
            rating TEXT,
            url TEXT,
            raw_json TEXT,
            first_seen_at TEXT NOT NULL
        )
        """
    )
    return conn


def filter_new_reports(reports: List[Report], db_path: Path, dry_run: bool) -> List[Report]:
    if dry_run:
        if not db_path.exists():
            return reports
        conn = sqlite3.connect(str(db_path))
    else:
        conn = init_db(db_path)

    new_reports: List[Report] = []
    now = dt.datetime.now().isoformat(timespec="seconds")
    try:
        for report in reports:
            existing = conn.execute("SELECT 1 FROM reports WHERE dedupe_key = ?", (report.dedupe_key,)).fetchone()
            if existing:
                continue
            new_reports.append(report)
            if not dry_run:
                conn.execute(
                    """
                    INSERT INTO reports (
                        dedupe_key, source, category, title, broker, analyst, report_date,
                        target, rating, url, raw_json, first_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report.dedupe_key,
                        report.source,
                        report.category,
                        report.title,
                        report.broker,
                        report.analyst,
                        report.report_date,
                        report.target,
                        report.rating,
                        report.url,
                        json.dumps(report.raw, ensure_ascii=False),
                        now,
                    ),
                )
        if not dry_run:
            conn.commit()
    finally:
        conn.close()
    return new_reports


def collect_reports(config: Dict[str, Any], begin_date: str, end_date: str) -> List[Report]:
    source_cfg = config["sources"]["eastmoney"]
    if not source_cfg.get("enabled", True):
        return []
    reports: List[Report] = []
    for category in source_cfg.get("categories", ["stock", "industry", "macro"]):
        if category not in CATEGORY_LABELS:
            logging.warning("Skip unknown category: %s", category)
            continue
        category_reports = fetch_eastmoney_category(config, category, begin_date, end_date)
        logging.info("Fetched %s reports for %s", len(category_reports), category)
        reports.extend(category_reports)
    return apply_filters(reports, config, begin_date, end_date)


def group_reports(reports: List[Report]) -> Dict[str, List[Report]]:
    grouped = {category: [] for category in CATEGORY_LABELS}
    for report in reports:
        grouped.setdefault(report.category, []).append(report)
    for values in grouped.values():
        values.sort(key=lambda item: (item.report_date, item.broker, item.title), reverse=True)
    return grouped


def build_markdown(reports: List[Report], target_date: str, config: Dict[str, Any]) -> str:
    filters = config.get("filters", {})
    max_per_category = int(filters.get("max_items_per_category", 20))
    max_total = int(filters.get("max_total_items", 60))
    grouped = group_reports(reports[:max_total])
    counts = {category: len([r for r in reports if r.category == category]) for category in CATEGORY_LABELS}
    lines = [
        f"## {target_date} 券商研报摘要",
        f"新增 {len(reports)} 篇：个股 {counts['stock']}，行业 {counts['industry']}，宏观 {counts['macro']}",
        "",
    ]

    for category, label in CATEGORY_LABELS.items():
        items = grouped.get(category, [])
        lines.append(f"### {label}")
        if not items:
            lines.append("无新增")
            lines.append("")
            continue
        for report in items[:max_per_category]:
            meta_parts = [part for part in [report.broker, report.report_date, report.rating or report.target] if part]
            meta = " | ".join(meta_parts)
            lines.append(f"- [{escape_markdown(report.title)}]({report.url})")
            if meta:
                lines.append(f"  {escape_markdown(meta)}")
        hidden = max(0, counts[category] - max_per_category)
        if hidden:
            lines.append(f"- 还有 {hidden} 篇未展示")
        lines.append("")

    content = "\n".join(lines).strip()
    max_chars = int(config.get("notification", {}).get("max_markdown_chars", 3800))
    if len(content) > max_chars:
        content = content[: max_chars - 20].rstrip() + "\n\n...内容已截断"
    return content


def build_category_markdown(
    category: str,
    items: List[Report],
    total_count: int,
    target_date: str,
    config: Dict[str, Any],
) -> str:
    filters = config.get("filters", {})
    label = CATEGORY_LABELS[category]
    max_per_category = int(filters.get("max_items_per_category", 20))
    lines = [
        f"## {target_date} {label}",
        f"新增 {total_count} 篇",
        "",
    ]

    if not items:
        lines.append("无新增")
    else:
        for report in items[:max_per_category]:
            meta_parts = [part for part in [report.broker, report.report_date, report.rating or report.target] if part]
            meta = " | ".join(meta_parts)
            lines.append(f"- [{escape_markdown(report.title)}]({report.url})")
            if meta:
                lines.append(f"  {escape_markdown(meta)}")
        hidden = max(0, total_count - max_per_category)
        if hidden:
            lines.append(f"- 还有 {hidden} 篇未展示")

    return trim_markdown("\n".join(lines).strip(), config)


def build_markdown_messages(reports: List[Report], target_date: str, config: Dict[str, Any]) -> List[str]:
    notification = config.get("notification", {})
    if not notification.get("group_by_category", True):
        return [build_markdown(reports, target_date, config)]

    # 中文注释：按分类拆成多条企业微信消息，避免单条 Markdown 过长。
    grouped = group_reports(reports)
    counts = {category: len([r for r in reports if r.category == category]) for category in CATEGORY_LABELS}
    notify_empty = bool(notification.get("notify_empty", False))
    messages: List[str] = []
    for category in CATEGORY_LABELS:
        if counts[category] == 0 and not notify_empty:
            continue
        messages.append(build_category_markdown(category, grouped.get(category, []), counts[category], target_date, config))
    return messages


def trim_markdown(content: str, config: Dict[str, Any]) -> str:
    max_chars = int(config.get("notification", {}).get("max_markdown_chars", 3800))
    if len(content) > max_chars:
        return content[: max_chars - 20].rstrip() + "\n\n...内容已截断"
    return content


def escape_markdown(text: str) -> str:
    # 中文注释：企业微信 Markdown 对普通中文兼容较好，只压缩换行。
    return re.sub(r"\s+", " ", text).strip()


def signed_wework_url(webhook: str, secret: str) -> str:
    if not secret:
        return webhook
    timestamp = str(int(time.time() * 1000))
    sign_source = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), sign_source, hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(digest).decode("utf-8"))
    separator = "&" if "?" in webhook else "?"
    return f"{webhook}{separator}timestamp={timestamp}&sign={sign}"


def send_wework_markdown(content: str, config: Dict[str, Any]) -> None:
    notification = config.get("notification", {})
    webhook_env = notification.get("webhook_env", "WEWORK_BOT_WEBHOOK")
    secret_env = notification.get("secret_env", "WEWORK_BOT_SECRET")
    webhook = os.getenv(webhook_env, "")
    secret = os.getenv(secret_env, "")
    if not webhook:
        logging.warning("WeCom webhook env %s is empty; print message only.", webhook_env)
        print(content)
        return

    url = signed_wework_url(webhook, secret)
    body = json.dumps({"msgtype": "markdown", "markdown": {"content": content}}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8", errors="replace"))
    if result.get("errcode") not in (0, None):
        raise RuntimeError(f"WeCom robot returned error: {result}")


def run(args: argparse.Namespace) -> int:
    if args.self_test:
        run_self_test()
        return 0

    config, config_dir = load_config(args.config)
    setup_logging(config, config_dir)
    target_date = args.date or dt.date.today().isoformat()
    begin_date, end_date = date_range(target_date, args.lookback_days)
    logging.info("Collect reports from %s to %s", begin_date, end_date)

    reports = collect_reports(config, begin_date, end_date)
    db_path = resolve_path(config["storage"]["sqlite_path"], config_dir)
    new_reports = filter_new_reports(reports, db_path, args.dry_run)
    logging.info("New reports: %s", len(new_reports))

    if not new_reports and not config.get("notification", {}).get("notify_empty", False):
        print(f"{target_date} no new reports.")
        return 0

    markdown_messages = build_markdown_messages(new_reports, target_date, config)
    if args.dry_run:
        print("\n\n---\n\n".join(markdown_messages))
        return 0
    interval = float(config.get("notification", {}).get("message_interval_seconds", 1))
    for index, markdown in enumerate(markdown_messages):
        send_wework_markdown(markdown, config)
        if interval > 0 and index < len(markdown_messages) - 1:
            time.sleep(interval)
    return 0


def run_self_test() -> None:
    # 中文注释：离线自检覆盖解析、去重和企业微信签名，避免依赖外网。
    payload = {
        "data": [
            {
                "title": "宏观经济周报：政策继续发力",
                "orgSName": "示例证券",
                "author": "张三",
                "publishDate": "2026-06-23 08:00:00",
                "encodeUrl": "AP20260623000001",
            }
        ]
    }
    items = extract_payload_items(payload)
    html_payload = extract_initdata_from_html("<script>var initdata = " + json.dumps(payload, ensure_ascii=False) + ";</script>")
    assert extract_payload_items(html_payload)[0]["title"] == "宏观经济周报：政策继续发力"
    report = normalize_report(items[0], "macro", DEFAULT_CONFIG["sources"]["eastmoney"]["pages"]["macro"])
    assert report is not None
    assert report.category == "macro"
    assert report.report_date == "2026-06-23"
    assert report.target == report.title
    assert report.url.endswith("AP20260623000001.html")

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "reports.sqlite"
        first = filter_new_reports([report], db_path, dry_run=False)
        second = filter_new_reports([report], db_path, dry_run=False)
        assert len(first) == 1
        assert len(second) == 0

    url = signed_wework_url("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=x", "secret")
    assert "timestamp=" in url and "sign=" in url

    messages = build_markdown_messages([report], "2026-06-23", DEFAULT_CONFIG)
    assert len(messages) == 1
    assert "宏观研究" in messages[0] and "示例证券" in messages[0]
    print("self-test passed")


if __name__ == "__main__":
    try:
        raise SystemExit(run(parse_args()))
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        logging.exception("Unhandled error: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
