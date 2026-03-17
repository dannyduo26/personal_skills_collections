#!/usr/bin/env python3
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

CONFIG_PATH = Path(__file__).resolve().parent.parent / 'config.json'
BJ = ZoneInfo('Asia/Shanghai')


def load_config():
    if not CONFIG_PATH.exists():
        raise SystemExit(f'config.json not found: {CONFIG_PATH}')
    cfg = json.loads(CONFIG_PATH.read_text())
    cookie = cfg.get('cookie', '').strip()
    if not cookie:
        raise SystemExit('config.json missing cookie')
    return {
        'cookie': cookie,
        'dynamicsUrl': cfg.get('dynamicsUrl', 'https://wx.zsxq.com/dynamics'),
        'apiBase': cfg.get('apiBase', 'https://api.zsxq.com/v2'),
        'pageCount': int(cfg.get('pageCount', 3)),
        'pageSize': int(cfg.get('pageSize', 20)),
    }


def get_json(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8', errors='ignore'))


def parse_dt(s: str) -> datetime:
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f%z').astimezone(BJ)


def topic_text(topic: dict) -> tuple[str, str]:
    typ = topic.get('type', '')
    payload = topic.get(typ, {}) if isinstance(topic.get(typ), dict) else {}
    owner = payload.get('owner', {}).get('name', '') or topic.get('owner', {}).get('name', '')
    text = payload.get('text', '') or payload.get('title', '') or ''
    if not text and typ == 'question':
        text = topic.get('question', {}).get('text', '')
    if not text and typ == 'answer':
        text = topic.get('answer', {}).get('text', '')
    text = (text or '[无纯文本，可能是图片/文件/结构化内容]').strip()
    return owner, text


def fetch_group_topics(api_base, gid, headers, page_size, max_pages):
    out = []
    end_time = ''
    for _ in range(max_pages):
        params = {'count': page_size}
        if end_time:
            params['end_time'] = end_time
        url = f"{api_base}/groups/{gid}/topics?" + urllib.parse.urlencode(params)
        data = get_json(url, headers)
        topics = data.get('resp_data', {}).get('topics', [])
        if not topics:
            break
        out.extend(topics)
        last_time = topics[-1].get('create_time')
        if not last_time or len(topics) < page_size:
            break
        end_time = last_time
    return out


def collect_today_items():
    cfg = load_config()
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Cookie': cfg['cookie'],
        'Accept': 'application/json, text/plain, */*',
        'Referer': cfg['dynamicsUrl'],
        'Origin': 'https://wx.zsxq.com'
    }

    groups_data = get_json(f"{cfg['apiBase']}/groups", headers)
    groups = groups_data.get('resp_data', {}).get('groups', [])
    today = datetime.now(BJ).date()
    items = []

    for group in groups:
        gid = group['group_id']
        gname = group['name']
        try:
            topics = fetch_group_topics(cfg['apiBase'], gid, headers, cfg['pageSize'], cfg['pageCount'])
        except Exception:
            continue
        for topic in topics:
            create_time = topic.get('create_time')
            if not create_time:
                continue
            dt = parse_dt(create_time)
            if dt.date() != today:
                continue
            owner, text = topic_text(topic)
            items.append({
                'group_name': gname,
                'time': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'type': topic.get('type', ''),
                'owner': owner,
                'text': text,
                'topic_id': topic.get('topic_id')
            })

    dedup = {}
    for item in items:
        dedup[item['topic_id']] = item
    final_items = sorted(dedup.values(), key=lambda x: x['time'], reverse=True)
    return {'today_count': len(final_items), 'items': final_items}


def print_text(payload):
    print(f"TODAY_DYNAMICS_COUNT={payload['today_count']}")
    for idx, item in enumerate(payload['items'], start=1):
        print(f"\n--- ITEM {idx} ---")
        print(f"星球: {item['group_name']}")
        print(f"时间: {item['time']}")
        print(f"作者: {item['owner']}")
        print(f"类型: {item['type']}")
        print('原文:')
        print(item['text'])
        print(f"topic_id: {item['topic_id']}")


def main():
    payload = collect_today_items()
    if '--json' in sys.argv:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text(payload)


if __name__ == '__main__':
    main()
