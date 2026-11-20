"""直接拉：已知 26 个可用 (联赛×赛季) 组合，跳过探测加速
免费 Key 可用的全部，带 429 重试
"""
import requests, sqlite3, time, sys
sys.path.insert(0, ".")
from db import init_db

KEY = "1799e02bf2f14461b20df58f899d8c76"
HEADERS = {"X-Auth-Token": KEY}
BASE = "https://api.football-data.org/v4"
DB = "epl.db"

# 已确认可用的 26 个组合（从探测结果来）
TO_FETCH = [
    # 已完成的注释掉，只补剩余的
    # ("BSA", "Campeonato Brasileiro Série A", [2023, 2024, 2025, 2026]),
    # ("ELC", "Championship",                [2023, 2024, 2025, 2026]),
    # ("PL",  "Premier League",              [2023, 2024, 2025, 2026]),
    # ("CL",  "UEFA Champions League",       [2023, 2024, 2025]),
    # ("PPL", "Primeira Liga",               [2025, 2026]),
    # ("CLI", "Copa Libertadores",           [2023, 2024, 2025, 2026]),
    ("PD",  "Primera Division",            [2023, 2024, 2025, 2026]),
    ("WC",  "FIFA World Cup",              [2026]),
]

def safe_get(path, params=None, max_retries=5):
    for attempt in range(max_retries):
        r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=20)
        if r.status_code == 429:
            wait = 20 * (attempt + 1)
            print(f"      429 限流，sleep {wait}s ({attempt+1}/{max_retries})...")
            time.sleep(wait)
            continue
        return r
    return r

# 保留已有数据，增量追加
init_db()

total_matches = 0
total_teams = 0

for code, name, seasons in TO_FETCH:
    for s_year in seasons:
        r = safe_get(f"/competitions/{code}/matches", params={"season": s_year})
        time.sleep(0.15)  # 基础限速
        if r.status_code != 200:
            print(f"  ❌ {code} {s_year} status={r.status_code} 跳过")
            continue
        d = r.json()
        matches = d.get("matches", [])
        print(f"  📥 {code:6s} {s_year}  {len(matches)} 场")

        conn = sqlite3.connect(DB)
        for m in matches:
            mid = m["id"]
            home = m["homeTeam"]
            away = m["awayTeam"]
            score = (m.get("score", {}).get("fullTime") or {})
            home_g = score.get("home")
            away_g = score.get("away")

            for t in (home, away):
                tid = t.get("id") or 0
                tname = t.get("name") or t.get("shortName") or f"Team-{tid}"
                short = t.get("shortName") or ""
                conn.execute(
                    "INSERT OR REPLACE INTO teams (team_id, name, short_name) VALUES (?, ?, ?)",
                    (tid, tname, short)
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
                 m.get("utcDate", ""), m.get("status", ""),
                 home_g, away_g)
            )
            total_matches += 1
        conn.commit()
        conn.close()

print(f"\n✅ 共写入 {total_matches} 场比赛")

# 汇总
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
print(f"\n{'='*60}")
print(f"  最终数据汇总（免费 Key 全部可用数据）")
print(f"{'='*60}")
for r in conn.execute("SELECT league, status, COUNT(*) AS c FROM matches GROUP BY league, status ORDER BY league, status"):
    print(f"  {r['league']:6s} {r['status']:10s} {r['c']:>5d} 场")
total = conn.execute("SELECT COUNT(*) AS c FROM matches").fetchone()["c"]
finished = conn.execute("SELECT COUNT(*) AS c FROM matches WHERE home_goals IS NOT NULL").fetchone()["c"]
print(f"\n  总计：{total} 场（已结束 {finished} 场）")
conn.close()
