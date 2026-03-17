#!/usr/bin/env python3
"""
Author Tweet Digest - Gathers today's tweets from author_list and outputs structured data.
Usage: python3 author_digest.py [--days 1] [--json]
"""
import json
import sys
import os
import io
import contextlib
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import search

CONFIG_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "config.json")
SHANGHAI_TZ = timezone(timedelta(hours=8))


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_tweets_for_author(author, days=1):
    """Get recent tweets for an author using search.py."""
    try:
        # 直接调用 search 模块内部的方法，并通过重定向拦截其中的 print 打印信息
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            data = search.fetch_user_tweets(
                username=author, 
                days=days, 
                max_results=20, 
                output_json=True
            )
            
        tweets = data.get("data", [])
        # Filter to recent N days (Shanghai time)
        today = datetime.now(SHANGHAI_TZ).date()
        # 修复之前在函数内引用全局局部变量 args.days 的 bug，改用局部参数 days
        cutoff = today - timedelta(days=days - 1)
        filtered = []
        for t in tweets:
            created = datetime.strptime(t["created_at"], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc)
            if cutoff <= created.astimezone(SHANGHAI_TZ).date() <= today:
                filtered.append(t)
        return filtered
    except Exception as e:
        print(f"[WARN] Error fetching {author}: {e}", file=sys.stderr)
        return []


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    parser.add_argument("--max-per-author", type=int, default=5, help="Max tweets per author (default: 5)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    config = load_config()
    authors = config.get("author_list", [])
    all_tweets = []

    for author in authors:
        tweets = get_tweets_for_author(author, args.days)
        tweets = tweets[:args.max_per_author]
        for t in tweets:
            t["_author_handle"] = author
        all_tweets.extend(tweets)

    if args.json:
        print(json.dumps(all_tweets, ensure_ascii=False, indent=2))
    else:
        # Human-readable output
        if not all_tweets:
            print("近7天无推文。")
            return

        # Group by author
        by_author = {}
        for t in all_tweets:
            author = t["_author_handle"]
            if author not in by_author:
                by_author[author] = []
            by_author[author].append(t)

        total = len(all_tweets)
        author_count = len(by_author)
        print(f"共获取 {author_count} 位作者的 {total} 条近7天推文\n")

        for author, tweets in by_author.items():
            print(f"=== @{author} ({len(tweets)} 条) ===")
            for t in tweets:
                created = datetime.strptime(t["created_at"], "%Y-%m-%dT%H:%M:%S.000Z")
                created_str = created.strftime("%H:%M")
                # 获取各项指标数据
                metrics = t.get("public_metrics", {})
                likes = metrics.get("like_count", 0)
                rts = metrics.get("retweet_count", 0)
                replies = metrics.get("reply_count", 0)
                quotes = metrics.get("quote_count", 0)
                views = metrics.get("impression_count", 0)
                
                # 拼接指标展示字符串
                metrics_str = f"❤️{likes} 🔁{rts} 💬{replies} 🔄{quotes}"
                if views > 0:
                    metrics_str += f" 👁️{views}"
                    
                print(f"  [{created_str}] {metrics_str}")
                text = t["text"]
                # Expand t.co links
                if "entities" in t and "urls" in t["entities"]:
                    for u in t["entities"]["urls"]:
                        text = text.replace(u["url"], u.get("expanded_url", u["url"]))
                print(f"  {text}")
                print(f"  https://x.com/{author}/status/{t['id']}")
                print()
            print()


if __name__ == "__main__":
    main()
