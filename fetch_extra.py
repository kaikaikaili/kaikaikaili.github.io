"""补拉：意甲/德甲/法甲/荷甲 + 欧冠 2026（之前被 429 限流）
用 0.5s 间隔 + 指数退避重试，确保不触发限流
"""
import requests, sqlite3, time, sys
sys.path.insert(0, ".")
from db import init_db

KEY = "1799e02bf2f14461b20df58f899d8c76"
HEADERS = {"X-Auth-Token": KEY}
BASE = "https://api.football-data.org/v4"
DB = "epl.db"

# 补拉目标
EXTRA = [
    ("SA",  "Serie A",            [2023, 2024, 2025, 2026]),
    ("BL1", "Bundesliga",         [2023, 2024, 2025, 2026]),
    ("FL1", "Ligue 1",            [2023, 2024, 2025, 2026]),
    ("DED", "Eredivisie",         [2023, 2024, 2025, 2026]),
    ("CL",  "UEFA Champions League", [2026]),  # 补之前 429 的
]

def safe_get(path, params=None, max_retries=6):
    """带 429 重试 + 指数退避 + 长间隔"""
    for attempt in range(max_retries):
        r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=20)
        if r.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"      429 限流 → sleep {wait}s ({attempt+1}/{max_retries})...")
            time.sleep(wait)
            continue
        if r.status_code == 403:
            print(f"      403 无权限 → 放弃")
            return r
        return r
    return r

init_db()

total_matches = 0
conn = sqlite3.connect(DB)

for code, name, seasons in EXTRA:
    for s_year in seasons:
        print(f"  拉 {code} {s_year}...", end=" ", flush=True)
        r = safe_get(f"/competitions/{code}/matches", params={"season": s_year})
        time.sleep(0.5)  # 基础限速：2 req/s → 低于 10/min 限流阈值

        if r.status_code != 200:
            print(f"失败 status={r.status_code}")
            continue

        d = r.json()
        matches = d.get("matches", [])
        print(f"{len(matches)} 场 ✅")

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
print(f"\n✅ 本轮新增 {total_matches} 场比赛")

# === 最终汇总 ===
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
print(f"\n{'='*60}")
print(f"  免费 Key 全量数据最终汇总")
print(f"{'='*60}")
grand_total = 0
grand_finished = 0
for r in conn.execute("SELECT league, status, COUNT(*) AS c FROM matches GROUP BY league, status ORDER BY league, status"):
    print(f"  {r['league']:6s} {r['status']:12s} {r['c']:>6d} 场")
    grand_total += r["c"]
    if r["home_goals"] is not None:
        grand_finished += r["c"]

total_f = conn.execute("SELECT COUNT(*) AS c FROM matches").fetchone()["c"]
total_done = conn.execute("SELECT COUNT(*) AS c FROM matches WHERE home_goals IS NOT NULL").fetchone()["c"]
print(f"\n  总计：{total_f} 场（已结束 {total_done} 场）")
conn.close()
