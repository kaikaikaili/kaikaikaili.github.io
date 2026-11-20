"""全量拉取（带限流重试）—— 免费 Key 可用的全部联赛+赛季"""
import requests, sqlite3, time, sys
sys.path.insert(0, ".")

from db import init_db

KEY = "1799e02bf2f14461b20df58f899d8c76"
HEADERS = {"X-Auth-Token": KEY}
BASE = "https://api.football-data.org/v4"
DB = "epl.db"

def safe_get(path, params=None, max_retries=5):
    """带 429 重试 + 指数退避"""
    for attempt in range(max_retries):
        r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=15)
        if r.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"    429 限流，sleep {wait}s 后重试 ({attempt+1}/{max_retries})...")
            time.sleep(wait)
            continue
        return r
    return r  # 返回最后一次结果

# ============ 阶段 1：探测（带重试）============
print("阶段 1：探测可用联赛×赛季...")

r = safe_get("/competitions")
all_comps = r.json()["competitions"]
print(f"免费 Key 可用赛事：{len(all_comps)} 个")

# 每个联赛扫描可用 season
available = []
for comp in all_comps:
    code = comp["code"]
    name = comp["name"]
    comp_available = []
    for s_year in range(2020, 2027):
        r = safe_get(f"/competitions/{code}/matches", params={"season": s_year})
        time.sleep(0.12)  # 基础限速
        if r.status_code == 200:
            d = r.json()
            count = d.get("resultSet", {}).get("count", 0)
            if count and count > 0:
                matches = d["matches"]
                comp_available.append((code, name, s_year, count, matches))
                print(f"  ✅ {code:6s} {s_year}  {count}场")
        elif r.status_code == 403:
            pass  # 无权限
    available.extend(comp_available)

print(f"\n共 {len(available)} 个 联赛×赛季 组合")

# ============ 阶段 2：写入 DB ============
init_db()
conn = sqlite3.connect(DB)
conn.execute("DELETE FROM matches")
conn.execute("DELETE FROM teams")
conn.commit()
conn.close()

total_matches = 0
total_teams = 0

conn = sqlite3.connect(DB)
for code, name, s_year, count, matches in available:
    for m in matches:
        mid = m["id"]
        home = m["homeTeam"]
        away = m["awayTeam"]
        score = m.get("score", {}).get("fullTime") or {}
        home_g = score.get("home")
        away_g = score.get("away")
        status = m.get("status", "")
        match_date = m.get("utcDate", "")

        for t in (home, away):
            conn.execute(
                "INSERT OR REPLACE INTO teams (team_id, name, short_name) VALUES (?, ?, ?)",
                (t.get("id", 0), t.get("name", ""), t.get("shortName", ""))
            )
            total_teams += 1

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
    print(f"  已写入 {code} {s_year}  ({count}场)")

conn.close()
print(f"\n✅ 总写入：{total_matches} 场比赛，{total_teams} 条球队记录")

# ============ 汇总 ============
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
print(f"\n{'='*60}")
print(f"  最终数据汇总")
print(f"{'='*60}")
for r in conn.execute("SELECT league, status, COUNT(*) AS c FROM matches GROUP BY league, status ORDER BY league, status"):
    print(f"  {r['league']:6s} {r['status']:10s} {r['c']:>5d} 场")
conn.close()
