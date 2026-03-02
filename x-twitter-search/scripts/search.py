#!/usr/bin/env python3
"""
Search X/Twitter using the X API.
Supports keyword search (Recent Search) and user timeline (/2/users/:id/tweets).
Requires X_BEARER_TOKEN environment variable.

Usage:
  python search.py "search query"           # keyword search
  python search.py --user elonmusk           # user timeline
  python search.py --user elonmusk "AI"      # user tweets matching keyword
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")


X_API_BASE = "https://api.x.com"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
DEFAULT_DAYS = int(os.environ.get("SEARCH_X_DAYS", "7"))


def load_config():
    """Load configuration from config.json."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_bearer_token():
    """Get bearer token from config.json first, then environment variables."""
    config = load_config()
    token = config.get("x_bearer_token", "").strip()
    if token:
        return token
    return os.environ.get("X_BEARER_TOKEN") or os.environ.get("TWITTER_BEARER_TOKEN")


def get_date_range(days):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    return start.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_query(query, handles=None, exclude=None):
    q = query

    if handles:
        from_clause = " OR ".join(f"from:{h}" for h in handles)
        q = f"({from_clause}) {q}"

    if exclude:
        exclude_clause = " ".join(f"-from:{h}" for h in exclude)
        q = f"{q} {exclude_clause}"

    q = f"{q} -is:retweet"
    return q


def api_request(path, bearer_token):
    """Make an authenticated GET request to the X API."""
    url = f"{X_API_BASE}{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {bearer_token}",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"❌ X API Error ({e.code}): {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"❌ Request failed: {e.reason}", file=sys.stderr)
        sys.exit(1)


def lookup_user_id(username, bearer_token):
    """Resolve a username to a user ID via /2/users/by/username/:username."""
    data = api_request(f"/2/users/by/username/{username}?user.fields=name,username", bearer_token)
    if "data" not in data:
        errors = data.get("errors", [{}])
        msg = errors[0].get("detail", "User not found") if errors else "User not found"
        print(f"❌ {msg}", file=sys.stderr)
        sys.exit(1)
    return data["data"]


def fetch_user_tweets(username, days=DEFAULT_DAYS, max_results=20,
                      output_json=False, compact=False, links_only=False):
    """Fetch recent tweets from a specific user."""
    bearer_token = get_bearer_token()
    if not bearer_token:
        print("❌ No X API Bearer Token found.", file=sys.stderr)
        print("   Set X_BEARER_TOKEN environment variable.", file=sys.stderr)
        sys.exit(1)

    user_info = lookup_user_id(username, bearer_token)
    user_id = user_info["id"]
    display_name = user_info.get("name", username)

    params = urllib.parse.urlencode({
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,public_metrics,entities",
        "start_time": get_date_range(days),
        "exclude": "retweets",
    })

    data = api_request(f"/2/users/{user_id}/tweets?{params}", bearer_token)

    # Full JSON output
    if output_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data

    tweets = data.get("data", [])
    if not tweets:
        print(f"No recent tweets found for @{username}.")
        return {"text": "", "citations": []}

    citations = []
    lines = []

    for tweet in tweets:
        tweet_url = f"https://x.com/{username}/status/{tweet['id']}"
        citations.append(tweet_url)

        if not links_only:
            date_str = ""
            if "created_at" in tweet:
                dt = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d %H:%M")

            metrics = tweet.get("public_metrics", {})
            engagement = f" (❤️ {metrics['like_count']})" if metrics.get("like_count") else ""

            lines.append(f"**@{username}** ({display_name}) — {date_str}{engagement}")
            lines.append(tweet["text"])
            lines.append(f"🔗 {tweet_url}")
            lines.append("")

    if links_only:
        for url in citations:
            print(url)
        return {"text": "", "citations": citations}

    output_text = "\n".join(lines)
    print(output_text)

    if not compact:
        print(f"\n📊 Found {len(tweets)} tweets from @{username}")

    return {"text": output_text, "citations": citations}


def search_tweets(query, days=DEFAULT_DAYS, handles=None, exclude=None,
                  max_results=20, output_json=False, compact=False, links_only=False):
    bearer_token = get_bearer_token()
    if not bearer_token:
        print("❌ No X API Bearer Token found.", file=sys.stderr)
        print("   Set X_BEARER_TOKEN environment variable.", file=sys.stderr)
        print("   Get your token at: https://console.x.com", file=sys.stderr)
        sys.exit(1)

    days = min(days, 7)
    start_time = get_date_range(days)
    full_query = build_query(query, handles, exclude)

    params = urllib.parse.urlencode({
        "query": full_query,
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,author_id,public_metrics,entities",
        "user.fields": "name,username,verified",
        "expansions": "author_id",
        "start_time": start_time,
    })

    data = api_request(f"/2/tweets/search/recent?{params}", bearer_token)

    # Full JSON output
    if output_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data

    # Build user lookup map
    users = {}
    for user in data.get("includes", {}).get("users", []):
        users[user["id"]] = user

    tweets = data.get("data", [])
    if not tweets:
        print("No results found.")
        return {"text": "", "citations": []}

    citations = []
    lines = []

    for tweet in tweets:
        user = users.get(tweet["author_id"], {"username": "unknown", "name": "Unknown"})
        tweet_url = f"https://x.com/{user['username']}/status/{tweet['id']}"
        citations.append(tweet_url)

        if not links_only:
            date_str = ""
            if "created_at" in tweet:
                dt = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d %H:%M")

            metrics = tweet.get("public_metrics", {})
            engagement = f" (❤️ {metrics['like_count']})" if metrics.get("like_count") else ""

            lines.append(f"**@{user['username']}** ({user['name']}) — {date_str}{engagement}")
            lines.append(tweet["text"])
            lines.append(f"🔗 {tweet_url}")
            lines.append("")

    # Links only output
    if links_only:
        for url in citations:
            print(url)
        return {"text": "", "citations": citations}

    # Standard output
    output_text = "\n".join(lines)
    print(output_text)

    if not compact:
        print(f"\n📊 Found {len(tweets)} tweets via X API")

    return {"text": output_text, "citations": citations}


def main():
    parser = argparse.ArgumentParser(
        description="🔍 Search X — Real-time Twitter/X search via X API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python search.py "Claude Code tips"
  python search.py --days 3 "AI news"
  python search.py --user elonmusk                  # user timeline
  python search.py --user elonmusk "AI"              # user tweets + keyword
  python search.py --max 50 "trending AI"
  python search.py --handles elonmusk,OpenAI "announcements"
  python search.py --links-only "trending tech"

Environment:
  X_BEARER_TOKEN        X API Bearer Token (required)
  TWITTER_BEARER_TOKEN  Alternative env var name
  SEARCH_X_DAYS         Default days to search (default: 7)
        """,
    )
    parser.add_argument("query", nargs="*", help="Search query (optional with --user)")
    parser.add_argument("--user", "-u", type=str, default=None,
                        help="Fetch tweets from a specific user (@ optional)")
    parser.add_argument("--days", "-d", type=int, default=DEFAULT_DAYS,
                        help=f"Search last N days (default: {DEFAULT_DAYS}, max: 7)")
    parser.add_argument("--handles", type=str, default=None,
                        help="Only these handles (comma-separated, @ optional)")
    parser.add_argument("--exclude", "-e", type=str, default=None,
                        help="Exclude these handles (comma-separated)")
    parser.add_argument("--max", "-n", type=int, default=20,
                        help="Max results (default: 20, max: 100)")
    parser.add_argument("--compact", "-c", action="store_true",
                        help="Minimal output (just tweets)")
    parser.add_argument("--links-only", "-l", action="store_true",
                        help="Only output X links")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Full JSON response")

    args = parser.parse_args()

    query = " ".join(args.query) if args.query else ""
    user = args.user.strip().lstrip("@") if args.user else None
    handles = [h.strip().lstrip("@") for h in args.handles.split(",")] if args.handles else None
    exclude = [h.strip().lstrip("@") for h in args.exclude.split(",")] if args.exclude else None

    # Validate: need either --user or a query
    if not user and not query:
        print("❌ Please provide a search query or use --user <username>", file=sys.stderr)
        sys.exit(1)

    days = args.days
    if days > 7:
        print(f"⚠️  X API only supports 7-day lookback (requested {days}), using 7 days.\n",
              file=sys.stderr)
        days = 7

    # User timeline mode
    if user and not query:
        if not args.json and not args.links_only:
            print(f'👤 Fetching tweets from @{user} (last {days} days)...\n', file=sys.stderr)
        fetch_user_tweets(
            username=user,
            days=days,
            max_results=args.max,
            output_json=args.json,
            compact=args.compact,
            links_only=args.links_only,
        )
    # Search mode (with optional --user as handle filter)
    else:
        if user:
            handles = [user] + (handles or [])
        if not args.json and not args.links_only:
            print(f'🔍 Searching X: "{query}" (last {days} days)...\n', file=sys.stderr)
        search_tweets(
            query=query,
            days=days,
            handles=handles,
            exclude=exclude,
            max_results=args.max,
            output_json=args.json,
            compact=args.compact,
            links_only=args.links_only,
        )


if __name__ == "__main__":
    main()
