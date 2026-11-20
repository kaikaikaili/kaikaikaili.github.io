"""全面探测 football-data.org 免费 Key 的可用数据"""
import requests, json

KEY = "1799e02bf2f14461b20df58f899d8c76"
HEADERS = {"X-Auth-Token": KEY}
BASE = "https://api.football-data.org/v4"

def test_get(path, params=None):
    try:
        r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=15)
        status = r.status_code
        d = r.json() if r.text.strip() else {}
        return status, d
    except Exception as e:
        return "ERR", str(e)

print("=" * 70)
print("  免费 Key 能力探测")
print("=" * 70)

# 1. 所有 competitions
print("\n【1】Competitions 列表（免费可用）:")
s, d = test_get("/competitions")
if s == 200:
    comps = d.get("competitions", [])
    print(f"  共 {len(comps)} 个赛事")
    for c in comps:
        print(f"    {c.get('code', '?'):6s}  {c.get('name', '?'):35s}  type={c.get('type','?')}")
else:
    print(f"  status={s}  {d}")

# 2. 英超可用 seasons
print("\n【2】英超可用赛季:")
for s_year in [2020, 2021, 2022, 2023, 2024, 2025, 2026]:
    s, d = test_get("/competitions/PL/matches", params={"season": s_year})
    count = d.get("resultSet", {}).get("count", "?") if isinstance(d, dict) else "?"
    first = d.get("resultSet", {}).get("first", "") if isinstance(d, dict) else ""
    last = d.get("resultSet", {}).get("last", "") if isinstance(d, dict) else ""
    print(f"  season={s_year}  status={s}  count={count}  {first} → {last}")

# 3. 每个联赛的可用 season 数
print("\n【3】各联赛可拉赛季数:")
target_comps = ["PL", "BL1", "FL1", "EL1", "ELC", "ECL", "PPL", "SA", "DEN"]
for code in target_comps:
    available = []
    for s_year in range(2020, 2027):
        s, d = test_get(f"/competitions/{code}/matches", params={"season": s_year})
        if s == 200 and isinstance(d, dict):
            count = d.get("resultSet", {}).get("count", 0)
            if count and count > 0:
                available.append(f"{s_year}({count})")
        elif s == 403:
            available.append(f"{s_year}(403)")
    # 拿联赛名
    s2, d2 = test_get(f"/competitions/{code}")
    name = d2.get("name", "?") if s2 == 200 else "?"
    print(f"  {code:6s} {name:25s}  seasons: {', '.join(available[:7])}")
