#!/usr/bin/env python3
import urllib.request
import datetime
import json
import sys
import argparse

def fetch_daily_report(target_date):
    url = f"http://175.24.206.252/api/report/{target_date}"
    
    print(f"Fetching report for: {target_date} from {url}...", file=sys.stderr)

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = response.read().decode('utf-8')
            
            # Try to parse as JSON for pretty printing, otherwise just print text
            try:
                json_data = json.loads(data)
                return json.dumps(json_data, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                return data
                
    except urllib.error.HTTPError as e:
        print(f"Error: Failed to fetch report. HTTP Status Code: {e.code}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"Error: Network issue or invalid URL. Reason: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    date_str = args.date or datetime.date.today().strftime("%Y-%m-%d")
    report = fetch_daily_report(date_str)
    if report:
        print(report)
    else:
        sys.exit(1)
