#!/usr/bin/env python3
import argparse
import urllib.request
import urllib.parse
import json
import sys
import os

# Define config path relative to script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "../config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load config.json: {e}", file=sys.stderr)
    return {}

def send_notification(key, title, description=""):
    if not key:
        print("Error: SendKey is required. Provide it via --key or config.json.", file=sys.stderr)
        return False

    url = f"https://sctapi.ftqq.com/{key}.send"
    
    data = {
        'title': title,
        'desp': description
    }
    
    encoded_data = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=encoded_data, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            result = response.read().decode('utf-8')
            json_result = json.loads(result)
            if json_result.get('code') == 0 or json_result.get('errno') == 0:
                print(f"Successfully sent notification: {title}")
                return True
            else:
                print(f"Failed to send. API Response: {result}", file=sys.stderr)
                return False
    except Exception as e:
        print(f"Error sending notification: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    config = load_config()
    default_key = config.get("default_key")

    parser = argparse.ArgumentParser(description="Send WeChat notification via ServerChan")
    parser.add_argument("--key", default=default_key, help="ServerChan SendKey (defaults to value in config.json)")
    parser.add_argument("--title", required=True, help="Notification title")
    parser.add_argument("--body", default="", help="Notification body/description (Markdown supported)")
    
    args = parser.parse_args()
    
    send_notification(args.key, args.title, args.body)
