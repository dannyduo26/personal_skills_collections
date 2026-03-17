#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fetch_today_dynamics

TITLE = '【知识星球今日动态】'


def format_item(idx, item):
    """提取的公共方法：格式化单条动态消息"""
    return '\n'.join([
        '',
        f"--- ITEM {idx} ---",
        f"星球: {item.get('group_name', '')}",
        f"时间: {item.get('time', '')}",
        f"作者: {item.get('owner', '')}",
        f"类型: {item.get('type', '')}",
        '原文:',
        str(item.get('text', '')).strip(),
        f"topic_id: {item.get('topic_id', '')}",
    ])


def main():
    try:
        # 直接通过模块方法调用，更高效且不依赖外部进程
        data = fetch_today_dynamics.collect_today_items()
    except Exception as e:
        print(f"{TITLE}\n执行抓取失败：{e}")
        return 0

    items = data.get('items', []) or []
    if not items:
        # 当数据为空时的提示
        print(f"{TITLE}\n今天没有获取到知识星球动态")
        return 0

    parts = [TITLE, f"今日共 {len(items)} 条动态"]
    for idx, item in enumerate(items, start=1):
        # 提取重复代码到公共方法中
        parts.append(format_item(idx, item))
        
    print('\n'.join(parts))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
