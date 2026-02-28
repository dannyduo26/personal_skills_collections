#!/usr/bin/env python3
import urllib.request
import datetime
import json
import sys

def fetch_daily_report():
    # Check if date argument is provided
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        # Get today's date in YYYY-MM-DD format
        target_date = datetime.date.today().strftime("%Y-%m-%d")
    
    url = f"http://175.24.206.252/api/report/{target_date}"
    
    import base64
    auth_str = "dannyduo:265252"
    encoded_auth = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
    headers = {"Authorization": f"Basic {encoded_auth}"}
    
    print(f"Fetching report for: {target_date} from {url}...", file=sys.stderr)

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode('utf-8')
            
            # Try to parse as JSON for pretty printing, otherwise just print text
            try:
                json_data = json.loads(data)
                print(json.dumps(json_data, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                print(data)
                
    except urllib.error.HTTPError as e:
        print(f"Error: Failed to fetch report. HTTP Status Code: {e.code}", file=sys.stderr)
        if e.code == 404:
             print("The report for today might not be generated yet.", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"Error: Network issue or invalid URL. Reason: {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    fetch_daily_report()
