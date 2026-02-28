---
name: fund-premium
description: Fetch and filter LOF/QDII fund premium rates from Jisilu (集思录). Helps identify arbitrage opportunities where market price is significantly higher than Net Asset Value (NAV).
---

# Fund Premium Rate Skill

Fetches real-time LOF and QDII fund data from Jisilu to identify funds with high premium rates (溢价率).

## Usage

### Basic Usage
Fetch funds with a premium rate > 2% (default) that are not fully paused or fully open (targeting "Limit Subscription" / 限购 for arbitrage).

```bash
python3 scripts/fetch_premium.py
```

### Custom Threshold
Fetch funds with premium rate > 5%.

```bash
python3 scripts/fetch_premium.py --threshold 5.0
```

## Logic
- **Source**: Jisilu.cn (QDII & LOF lists)
- **Filtering**:
    1. Premium Rate > Threshold
    2. Status is NOT "暂停申购" (Paused) AND NOT "开放申购" (Open)
    3. Targets funds with "限大额" (Limit Amount) status typically suitable for arbitrage.

## Output Example
```json
[
  {
    "code": "161129",
    "name": "易方达原油",
    "premium_rate": "15.32%",
    "status": "限制大额",
    "nav": "1.234",
    "price": "1.423"
  }
]
```
