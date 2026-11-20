"""测试 football-data.org API 能拉多少历史"""
import requests

KEY = "1799e02bf2f14461b20df58f899d8c76"
HEADERS = {"X-Auth-Token": KEY}
BASE = "https://api.football-data.org/v4"

# 1. 不带任何 filter（当前赛季）
print("=== 1. /PL/matches 默认 ===")
r = requests.get(f"{BASE}/competitions/PL/matches", headers=HEADERS)
d = r.json()
print(f"  总场次：{d['count']}")
print(f"  日期范围：{d['matches'][0]['utcDate'][:10]} → {d['matches'][-1]['utcDate'][:10]}")

# 2. 带 season 过滤器（试试 2024）
print("\n=== 2. /PL/matches?season=2024 ===")
r = requests.get(f"{BASE}/competitions/PL/matches", headers=HEADERS, params={"season": 2024})
d = r.json()
print(f"  总场次：{d['count']}")
if d["count"] > 0:
    print(f"  日期范围：{d['matches'][0]['utcDate'][:10]} → {d['matches'][-1]['utcDate'][:10]}")

# 3. 带 season=2023
print("\n=== 3. /PL/matches?season=2023 ===")
r = requests.get(f"{BASE}/competitions/PL/matches", headers=HEADERS, params={"season": 2023})
d = r.json()
print(f"  总场次：{d['count']}")
if d["count"] > 0:
    print(f"  日期范围：{d['matches'][0]['utcDate'][:10]} → {d['matches'][-1]['utcDate'][:10]}")

# 4. 带 season=2022
print("\n=== 4. /PL/matches?season=2022 ===")
r = requests.get(f"{BASE}/competitions/PL/matches", headers=HEADERS, params={"season": 2022})
d = r.json()
print(f"  总场次：{d['count']}")
if d["count"] > 0:
    print(f"  日期范围：{d['matches'][0]['utcDate'][:10]} → {d['matches'][-1]['utcDate'][:10]}")

# 5. competition 的 available seasons
print("\n=== 5. /PL/competitions 详情（available seasons）===")
r = requests.get(f"{BASE}/competitions/PL", headers=HEADERS)
d = r.json()
print(f"  name: {d.get('name')}")
seasons = d.get('seasons', [])
if seasons:
    for s in seasons[:8]:
        print(f"  season: {s.get('id')}  start={s.get('startDate')}  end={s.get('endDate')}  stages={s.get('stages')}")

# 6. 看一下 response headers（限流）
print(f"\n=== 6. Headers ===")
for k, v in r.headers.items():
    if 'ratelimit' in k.lower() or 'requests' in k.lower():
        print(f"  {k}: {v}")
