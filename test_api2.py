"""测试 API — 先看原始响应结构"""
import requests, json

KEY = "1799e02bf2f14461b20df58f899d8c76"
r = requests.get("https://api.football-data.org/v4/competitions/PL/matches", headers={"X-Auth-Token": KEY}, timeout=10)
print(f"Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('content-type')}")
d = r.json()
print(f"Top-level keys: {list(d.keys())}")
if 'matches' in d:
    print(f"match count: {len(d['matches'])}")
    print(f"first match keys: {list(d['matches'][0].keys())}")
    print(f"first match: {json.dumps(d['matches'][0], indent=2, ensure_ascii=False)[:500]}")
else:
    print(f"Full response: {json.dumps(d, indent=2, ensure_ascii=False)[:1000]}")
