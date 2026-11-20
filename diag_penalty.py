"""诊断：为什么隐式惩罚完全不触发"""
import sqlite3
from config import INJURY_DROP_THRESHOLD, INJURY_CHECK_WINDOW, FINISHED_STATUS

conn = sqlite3.connect("epl.db")
conn.row_factory = sqlite3.Row

# 抽样看每队的主场/客场进球分布
teams = conn.execute("SELECT team_id, name FROM teams ORDER BY team_id").fetchall()

print(f"阈值配置：INJURY_DROP_THRESHOLD={INJURY_DROP_THRESHOLD}  INJURY_CHECK_WINDOW={INJURY_CHECK_WINDOW}")
print()
print(f"{'球队':25s} {'场地':4s} {'近3场':>6s} {'长期':>6s} {'ratio':>7s} {'触发?':>6s}")
print("-" * 65)

for t in teams[:20]:   # 前20队
    for home in [True, False]:
        col = "home_goals" if home else "away_goals"
        where_col = "home_team_id" if home else "away_team_id"
        label = "主" if home else "客"

        long_rows = conn.execute(
            f"SELECT {col} AS g FROM matches WHERE {where_col}=? AND status=? ORDER BY match_date DESC LIMIT 10",
            (t["team_id"], FINISHED_STATUS)
        ).fetchall()
        recent_rows = conn.execute(
            f"SELECT {col} AS g FROM matches WHERE {where_col}=? AND status=? ORDER BY match_date DESC LIMIT 3",
            (t["team_id"], FINISHED_STATUS)
        ).fetchall()

        if not long_rows or len(long_rows) < 3:
            continue

        long_avg = sum(r["g"] for r in long_rows) / len(long_rows)
        recent_avg = sum(r["g"] for r in recent_rows) / len(recent_rows)
        ratio = recent_avg / long_avg if long_avg > 0.1 else 99.0
        trigger = "⚠ 是" if ratio < INJURY_DROP_THRESHOLD else "否"

        print(f"{t['name']:25s} {label}场  {recent_avg:>6.2f}  {long_avg:>6.2f}  {ratio:>7.2f}  {trigger:>6s}")
    print()

conn.close()
