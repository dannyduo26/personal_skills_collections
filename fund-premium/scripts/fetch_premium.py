#!/usr/bin/env python3
import json
import time
import urllib.request
import urllib.parse
import sys

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def _to_float_percent(s):
    """Convert percentage string to float (e.g., '1.5%' -> 1.5). Returns NaN on failure."""
    if not s:
        return float("nan")
    s = str(s).strip().replace("%", "").replace("+", "")
    try:
        return float(s)
    except Exception:
        return float("nan")

def _fetch_jisilu_api(url, params):
    """Fetch JSON data from Jisilu API using urllib (standard library)."""
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.jisilu.cn/data/qdii/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    
    try:
        # Add timestamp to prevent caching
        params["___jsl"] = f"LST___t={int(time.time()*1000)}"
        
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode("utf-8", errors="ignore")
            return json.loads(data)
    except Exception as e:
        # Silently fail for individual requests to allow partial results
        # print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None

def fetch_fund_data():
    """Fetch both QDII and LOF fund data from Jisilu."""
    results = []
    
    # 1. Fetch QDII Data (Categories: E=ETF-QDII, C=LOF-QDII, A=Index-QDII)
    # Note: 'A' and 'E' categories often overlap or are specific types. 
    # We fetch relevant categories to cover most bases.
    qdii_cats = ["E", "C"] 
    
    for cat in qdii_cats:
        url = f"https://www.jisilu.cn/data/qdii/qdii_list/{cat}"
        params = {"rp": "25"} # 'rp' is rows per page, but API often returns all if set correctly or paginated
        
        # For ETF (E), usually want lof/etf specific flags if API requires, 
        # but the simple endpoint usually works.
        if cat == "E":
            params.update({"only_lof": "y", "only_etf": "y"})
            
        data = _fetch_jisilu_api(url, params)
        if data and isinstance(data, dict):
            for row in data.get("rows", []):
                cell = row.get("cell", {})
                results.append(cell)

    # 2. Fetch LOF Data (Index LOF)
    lof_url = "https://www.jisilu.cn/data/lof/index_lof_list/"
    lof_params = {"rp": "100", "page": "1"} # LOF list might be longer
    
    data = _fetch_jisilu_api(lof_url, lof_params)
    if data and isinstance(data, dict):
        for row in data.get("rows", []):
            cell = row.get("cell", {})
            results.append(cell)
            
    return results

def filter_funds(funds, threshold=2.0, all_status=False):
    """Filter funds based on premium rate and subscription status."""
    candidates = []
    seen_codes = set()
    
    for f in funds:
        code = str(f.get("fund_id", ""))
        name = str(f.get("fund_nm", ""))
        
        # Deduplicate
        if code in seen_codes:
            continue
        seen_codes.add(code)
        
        premium_str = str(f.get("discount_rt", ""))
        premium = _to_float_percent(premium_str)
        
        status = str(f.get("apply_status", ""))
        
        if (premium == premium) and (premium > threshold): # Check for NaN
            # Strict mode: similar to reference script (Arbitrage focus)
            if all_status or (status != "暂停申购" and status != "开放申购"):
                candidates.append({
                    "code": code,
                    "name": name,
                    "premium_rate": f"{premium:.2f}%",
                    "status": status,
                    "nav": f.get("fund_nav", ""), # Net Asset Value
                    "price": f.get("price", "")   # Market Price
                })

    # Sort by premium rate descending
    candidates.sort(key=lambda x: float(x["premium_rate"].strip("%")), reverse=True)
    return candidates

# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch Fund Premium Rates from Jisilu")
    parser.add_argument("--threshold", type=float, default=2.0, help="Minimum premium rate %% to display (default: 2.0)")
    parser.add_argument("--all-status", action="store_true", help="Show all funds regardless of status (ignore arbitrage filter)")
    args = parser.parse_args()
    
    try:
        raw_data = fetch_fund_data()
        results = filter_funds(raw_data, args.threshold, args.all_status)
        
        # Print JSON for Clawdbot to parse or display
        print(json.dumps(results, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
