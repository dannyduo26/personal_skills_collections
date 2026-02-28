#!/usr/bin/env python3
import json
import time
import urllib.request
import urllib.parse
import sys

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def _to_float_percent(s):
    if not s:
        return float("nan")
    s = str(s).strip().replace("%", "").replace("+", "")
    try:
        return float(s)
    except Exception:
        return float("nan")

def _fetch_jisilu_api(url, params):
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.jisilu.cn/data/qdii/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    
    try:
        params["___jsl"] = f"LST___t={int(time.time()*1000)}"
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode("utf-8", errors="ignore")
            return json.loads(data)
    except Exception as e:
        return None

def fetch_fund_data():
    results = []
    
    # Only fetch ETF QDII (E) and LOF QDII (C) for now, as shown in curl example
    qdii_cats = ["E", "C"] 
    
    for cat in qdii_cats:
        url = f"https://www.jisilu.cn/data/qdii/qdii_list/{cat}"
        params = {"rp": "25"} 
        if cat == "E":
            params.update({"only_lof": "y", "only_etf": "y"})
            
        data = _fetch_jisilu_api(url, params)
        if data and isinstance(data, dict):
            for row in data.get("rows", []):
                cell = row.get("cell", {})
                results.append(cell)

    # LOF Data
    lof_url = "https://www.jisilu.cn/data/lof/index_lof_list/"
    lof_params = {"rp": "100", "page": "1"}
    
    data = _fetch_jisilu_api(lof_url, lof_params)
    if data and isinstance(data, dict):
        for row in data.get("rows", []):
            cell = row.get("cell", {})
            results.append(cell)
            
    return results

def filter_funds(funds, threshold=2.0):
    candidates = []
    seen_codes = set()
    
    for f in funds:
        code = str(f.get("fund_id", ""))
        name = str(f.get("fund_nm", ""))
        
        if code in seen_codes:
            continue
        seen_codes.add(code)
        
        premium_str = str(f.get("discount_rt", ""))
        premium = _to_float_percent(premium_str)
        status = str(f.get("apply_status", ""))
        
        # CHANGED: Allow ALL funds with high premium, regardless of status
        # We just want to notify about the premium existence.
        
        if (premium == premium) and (premium > threshold): 
             candidates.append({
                "code": code,
                "name": name,
                "premium_rate": f"{premium:.2f}%",
                "status": status,
                "nav": f.get("fund_nav", ""),
                "price": f.get("price", "")
            })

    candidates.sort(key=lambda x: float(x["premium_rate"].strip("%")), reverse=True)
    return candidates

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=2.0)
    args = parser.parse_args()
    
    try:
        raw_data = fetch_fund_data()
        results = filter_funds(raw_data, args.threshold)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
