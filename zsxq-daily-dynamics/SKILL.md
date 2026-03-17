---
name: zsxq-daily-dynamics
description: Fetch today’s latest Knowledge Planet (知识星球 / zsxq) updates from the authenticated web/API flow. Use when the user asks for today’s newest dynamics, latest posts, or recent updates in 知识星球. Prefer API access with a configured cookie in config.json. Default output should show the original full text of each item. If cookie auth is unavailable, fall back to opening https://wx.zsxq.com/dynamics and asking the user to complete mobile-phone login / SMS verification.
---

# zsxq-daily-dynamics

Fetch today’s newest Knowledge Planet updates. Prefer authenticated API access because it is more stable than scraping the rendered web page.

## Preferred path: cookie-based API fetch

Store a valid authenticated cookie in `config.json`, then run:

```bash
python3 scripts/fetch_today_dynamics.py
```

This default mode prints:

- Today item count
- Group name, time, author, type
- **Original full text** (`原文`)
- Topic id

To get JSON instead, run:

```bash
python3 scripts/fetch_today_dynamics.py --json
```

The script:

- Reads `config.json`
- Calls `https://api.zsxq.com/v2/groups`
- Fetches recent topics from each joined group
- Filters topics to **today** using the Asia/Shanghai date boundary
- Sorts newest first
- Prints the original full text by default

## Rendering for WeCom

If you need the output formatted for Enterprise WeChat (WeCom) or similar messaging platforms, run the wrapper script:

```bash
python3 scripts/render_wecom_message.py
```

This script directly imports `fetch_today_dynamics` internally for better performance, formatting the JSON data into a clean, readable text structure.

## config.json shape

```json
{
  "dynamicsUrl": "https://wx.zsxq.com/dynamics",
  "apiBase": "https://api.zsxq.com/v2",
  "pageCount": 3,
  "pageSize": 20,
  "cookie": "<authenticated cookie string>"
}
```

## Fallback path: browser login

If cookie auth is missing or expired:

1. Open `https://wx.zsxq.com/dynamics`
2. Trigger 手机号登录
3. Ask the user to complete SMS verification themselves if needed
4. After login, either keep using the browser session or refresh `config.json` with a new authenticated cookie

Important:

- Do not store SMS codes in files
- Do not echo sensitive cookies back into chat unless the user explicitly asks
- Treat `config.json` as sensitive local state

## Limitations

- This script currently fetches a few recent pages per joined group; very busy groups could need deeper pagination
- Non-text-heavy topics may show as placeholder text
- Cookie expiry will break API access until refreshed
