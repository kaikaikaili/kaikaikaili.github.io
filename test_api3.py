"""拉多个赛季历史数据"""
import requests, json

KEY = "1799e02bf2f14461b20df58f899d8c76"
HEADERS = {"X-Auth-Token": KEY}

def fetch(season=None):
    params = {}
    if season:
        params["season"] = season
    r = requests.get(f"https://api.football-data.org/v4/competitions/PL/matches",
                     headers=HEADERS, params=params, timeout=15)
    print(f"\nseason={season}  status={r.status_code}")
    d = r.json()
    rs = d.get("resultSet", {})
    season_info = d.get("matches", [{}])[0].get("season", {}) if d.get("matches") else {}
    print(f"  count={rs.get('count')}  dates={rs.get('first')} → {rs.get('last')}")
    print(f"  season meta: {season_info}")
    return d

# 不带 season（当前）
fetch(None)

for s in [2025, 2024, 2023, 2022, 2021]:
    fetch(s)
