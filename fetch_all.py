"""全量扫描 + 拉取所有可用联赛/赛季"""
import requests, sqlite3, time, sys

KEY = "1799e02bf2f14461b20df58f899d8c76"
HEADERS = {"X-Auth-Token": KEY}
BASE = "https://api.football-data.org/v4"
DB = "epl.db"

# 先拿到完整 competition 列表
r = requests.get(f"{BASE}/competitions", headers=HEADERS, timeout=15)
all_comps = r.json()["competitions"]
print(f"免费 Key 可用赛事：{len(all_comps)} 个")
for c in all_comps:
    print(f"  {c['code']:6s}  {c['name']}")

# 扫每个 comp 哪些 season 可用
available = []
for comp in all_comps:
    code = comp["code"]
    name = comp["name"]
    for s_year in range(2020, 2027):
        r = requests.get(f"{BASE}/competitions/{code}/matches",
                         headers=HEADERS, params={"season": s_year}, timeout=10)
        time.sleep(0.12)  # 10次/分钟限流
        if r.status_code == 200:
            d = r.json()
            count = d.get("resultSet", {}).get("count", 0)
            if count and count > 0:
                available.append((code, name, s_year, count, d["matches"]))
                print(f"  ✅ {code:6s} {name:30s} season={s_year}  count={count}")
        elif r.status_code == 403:
            continue
        else:
            print(f"  ? {code} season={s_year} status={r.status_code}")

print(f"\n=== 共找到 {len(available)} 个 (联赛×赛季) 组合 ===")

# 先初始化 DB（建表）
from db import init_db
init_db()
conn = sqlite3.connect(DB)
conn.execute("DELETE FROM matches")
conn.execute("DELETE FROM teams")
conn.commit()
conn.close()

# 批量写入
conn = sqlite3.connect(DB)
total_matches = 0
total_teams = 0

for code, name, s_year, count, matches in available:
    print(f"  写入 {code} {s_year} ({count}场)...")
    for m in matches:
        mid = m["id"]
        home = m["homeTeam"]
        away = m["awayTeam"]
        score = m.get("score", {}).get("fullTime") or {}
        home_g = score.get("home")
        away_g = score.get("away")
        status = m.get("status", "")
        match_date = m.get("utcDate", "")

        # 球队
        for t in (home, away):
            conn.execute(
                "INSERT OR REPLACE INTO teams (team_id, name, short_name) VALUES (?, ?, ?)",
                (t.get("id", 0), t.get("name", ""), t.get("shortName", ""))
            )
            total_teams += 1

        # 比赛
        conn.execute(
            """INSERT OR REPLACE INTO matches
               (match_id, league, home_team_id, away_team_id, home_name, away_name,
                match_date, status, home_goals, away_goals)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (mid, code,
             home.get("id", 0), away.get("id", 0),
             home.get("name", ""), away.get("name", ""),
             match_date, status, home_g, away_g)
        )
        total_matches += 1

    conn.commit()

conn.close()
print(f"\n✅ 总写入：{total_matches} 场比赛，{total_teams} 条球队记录")

# 汇总
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
print(f"\n=== 最终数据汇总 ===")
for r in conn.execute("SELECT league, status, COUNT(*) AS c FROM matches GROUP BY league, status ORDER BY league, status"):
    print(f"  {r['league']:6s} {r['status']:10s} {r['c']:>5d} 场")
conn.close()
