#!/usr/bin/env python3
"""
Universal web content extractor (Scrapling + html2text).
Returns clean Markdown with headings, links, images, lists, and code blocks.

Usage:
  python3 fetch.py <url> [max_chars] [--stealth]

Modes:
  (default)   Fast HTTP fetch via Fetcher — works for most sites (~1-3s)
  --stealth   Headless browser via StealthyFetcher — for JS-rendered or
              anti-scraping sites like WeChat, Zhihu, Juejin (~5-15s)

Examples:
  python3 fetch.py https://sspai.com/post/73145
  python3 fetch.py https://mp.weixin.qq.com/s/xxx 30000 --stealth
  python3 fetch.py https://zhuanlan.zhihu.com/p/12345 --stealth
"""

import sys
import re
import json
import logging
import argparse
import os
from datetime import datetime, timezone, timedelta


def check_dependencies():
    """Check if required packages are installed and provide install instructions."""
    missing = []
    try:
        import scrapling  # noqa: F401
    except ImportError:
        missing.append("scrapling")
    try:
        import html2text  # noqa: F401
    except ImportError:
        missing.append("html2text")
    try:
        import curl_cffi  # noqa: F401
    except ImportError:
        missing.append("curl_cffi")
    try:
        import browserforge  # noqa: F401
    except ImportError:
        missing.append("browserforge")
    try:
        import patchright  # noqa: F401
    except ImportError:
        missing.append("patchright")
    try:
        import msgspec  # noqa: F401
    except ImportError:
        missing.append("msgspec")

    if missing:
        err_msg = (
            f"Error: missing dependencies: {', '.join(missing)}\n"
            f"Install with:\n"
            f"  pip install {' '.join(missing)}"
        )
        if "patchright" in missing:
            err_msg += "\n\n  After installing patchright, you MUST install its browsers:\n  python -m patchright install"
        
        print(err_msg, file=sys.stderr)
        sys.exit(1)


def fix_lazy_images(html_raw):
    """
    Promote data-src to src for lazy-loaded images (WeChat, Zhihu, etc.).
    Many Chinese platforms use data-src for the real image URL while src
    holds a tiny placeholder. html2text only reads src, so we swap them.
    """
    return re.sub(
        r'<img([^>]*?)\sdata-src="([^"]+)"([^>]*?)>',
        lambda m: f'<img{m.group(1)} src="{m.group(2)}"{m.group(3)}>',
        html_raw,
    )


# CSS selectors in priority order — the first match with enough content wins.
# Covers most blog/article platforms without needing per-site customization.
CONTENT_SELECTORS = [
    "article",
    "main",
    ".post-content",
    ".entry-content",
    ".article-content",
    ".article-body",
    ".article-detail",         # 36kr
    ".article-holder",         # InfoQ
    ".post_body",              # 163.com (NetEase)
    ".markdown-body",          # GitHub
    ".Post-RichText",          # Zhihu
    "#article_content",        # CSDN
    ".article-area",           # Juejin
    ".ssa-article",            # Toutiao
    '[role="article"]',
    '[itemprop="articleBody"]',
]

# WeChat has a unique DOM structure — try these first for mp.weixin.qq.com
WECHAT_SELECTORS = [
    "div#js_content",
    "div.rich_media_content",
]

# Minimum characters for a selector match to be considered "real content"
MIN_CONTENT_LENGTH = 200


def html_to_markdown(html_raw, max_chars=100000):
    """Convert raw HTML to clean Markdown."""
    import html2text

    html_raw = fix_lazy_images(html_raw)

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0       # No line wrapping
    h.skip_internal_links = True
    h.ignore_emphasis = False

    md = h.handle(html_raw)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md[:max_chars]


def extract_content(page, url, max_chars=100000):
    """
    Try content selectors to find the article body.
    Returns (markdown_text, matched_selector).
    """
    raw_html = page.html_content
    
    # 尝试判断是否是直接返回了纯 JSON (或者被浏览器包裹在了 <pre> 标签里)
    import json
    import html
    import re
    # 去除 HTML 标签，避免 headless 浏览器用 <pre> 标签包裹原生 JSON
    text_content = html.unescape(re.sub(r'<[^>]+>', '', raw_html).strip())
    if text_content.startswith("{") or text_content.startswith("["):
        try:
            json.loads(text_content)
            # 如果成功解析为 JSON，则直接返回完整的 JSON 字符串，不再转换为 markdown 和截断
            return text_content, "json(native)"
        except Exception:
            pass

    is_wechat = "mp.weixin.qq.com" in url
    selectors = (WECHAT_SELECTORS + CONTENT_SELECTORS) if is_wechat else CONTENT_SELECTORS

    for selector in selectors:
        els = page.css(selector)
        if els:
            md = html_to_markdown(els[0].html_content, max_chars)
            if len(md) >= MIN_CONTENT_LENGTH:
                return md, selector

    # Fallback: convert the entire page
    md = html_to_markdown(page.html_content, max_chars)
    return md, "body(fallback)"


def _suppress_scrapling_logs():
    """Scrapling's logger is noisy (deprecation warnings, fetch info). Silence it."""
    logging.getLogger("scrapling").setLevel(logging.CRITICAL)


def fetch_fast(url, max_chars=100000, timeout=15):
    """
    Fast HTTP fetch — no JavaScript execution.
    Works for most blogs and static sites.
    """
    from scrapling.fetchers import Fetcher
    _suppress_scrapling_logs()

    page = Fetcher().get(url, timeout=timeout, stealthy_headers=True)
    return extract_content(page, url, max_chars)


def fetch_stealth(url, max_chars=100000, timeout=30000):
    """
    Headless browser fetch — executes JavaScript, bypasses anti-scraping.
    Required for: WeChat articles, Zhihu, Juejin, and other JS-rendered pages.
    Slower (~5-15s) but more reliable for protected content.
    """
    from scrapling.fetchers import StealthyFetcher
    _suppress_scrapling_logs()

    page = StealthyFetcher().fetch(
        url,
        headless=True,
        network_idle=True,
        timeout=timeout,
    )
    return extract_content(page, url, max_chars)


def fetch(url, max_chars=100000, stealth=False):
    """
    Main entry point. Fetches URL and returns (markdown, selector, mode).
    If stealth=False, tries fast mode first and falls back to stealth
    when the result is too short (likely a JS-rendered page).
    """
    if stealth:
        md, selector = fetch_stealth(url, max_chars)
        return md, selector, "stealth"

    # Try fast mode first
    md, selector = fetch_fast(url, max_chars)

    # If fast mode got barely any content, the page likely needs JS rendering
    if len(md) < MIN_CONTENT_LENGTH:
        try:
            md_stealth, sel_stealth = fetch_stealth(url, max_chars)
            if len(md_stealth) > len(md):
                return md_stealth, sel_stealth, "stealth(auto-fallback)"
        except Exception:
            pass  # Stick with fast mode result

    return md, selector, "fast"


def main():
    parser = argparse.ArgumentParser(description="Universal web content extractor (Scrapling + html2text)")
    parser.add_argument("--url", required=True, help="Target URL to fetch")
    parser.add_argument("--code", required=True, help="Code identifier for the task (used in filename)")
    parser.add_argument("--max_chars", type=int, default=30000, help="Maximum characters (default: 30000)")
    parser.add_argument("--stealth", action="store_true", help="Use headless browser for JS-rendered sites")
    parser.add_argument("--json", action="store_true", default=True, help="Output as JSON (default: True)")
    parser.add_argument("extra", nargs="*", help="Custom parameters in key=value format (e.g. author=John)")

    # Handle legacy-style arguments if any (but argparse takes care of most)
    args = parser.parse_args()

    # Parse extra parameters into crawler_info
    crawler_info = {"code": args.code}
    for item in args.extra:
        if "=" in item:
            k, v = item.split("=", 1)
            crawler_info[k] = v

    try:
        md, selector, mode = fetch(args.url, args.max_chars, stealth=args.stealth)

        # 把除了content的其他字段放到crawler_info里
        crawler_info.update({
            "url": args.url,
            "mode": mode,
            "selector": selector,
            "data_length": len(md),
            "create_time": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
            "crawler_type": "agent"
        })

        parsed_data = md
        try:
            parsed_data = json.loads(md)
        except Exception:
            pass

        result = {
            "data": parsed_data,
            "crawler_info": crawler_info
        }

        # 默认输出 JSON (控制台仅打印前1000字符，避免日志过长)
        json_output = json.dumps(result, ensure_ascii=False)
        print(json_output[:1000])

        # 保存到本地文件: /json/${code}_yyyy-MM-dd_HH:mm:ss.json
        # 注意: Windows 不支持文件名中包含冒号，使用横杠代替
        tz_east8 = timezone(timedelta(hours=8))
        now = datetime.now(tz_east8)
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{args.code}_{timestamp}.json"
        
        # 确定 json 目录路径 (项目根目录下的 json 文件夹)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        save_dir = os.path.join(project_root, "json")
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        file_path = os.path.join(save_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_output)

    except Exception as e:
        error_msg = f"Error fetching {args.url}: {type(e).__name__}: {e}"
        if "Executable doesn't exist at" in str(e):
            error_msg += "\n\nLooks like the browser binaries are not installed. Please run:\n  python -m patchright install chromium"
        print(json.dumps({"url": args.url, "error": error_msg}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    check_dependencies()
    main()
