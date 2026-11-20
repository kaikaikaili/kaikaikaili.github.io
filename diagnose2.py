"""查真实 API 数据的比赛状态分布"""
import sqlite3

conn = sqlite3.connect("epl.db")
conn.row_factory = sqlite3.Row

print("=== 比赛状态分布 ===")
for r in conn.execute("SELECT status, COUNT(*) AS c FROM matches GROUP BY status ORDER BY c DESC"):
    print(f"  {r['status']:12s}  {r['c']}")

print()
print("=== 比赛日期范围 ===")
for r in conn.execute("SELECT MIN(match_date) AS min_d, MAX(match_date) AS max_d FROM matches"):
    print(f"  最早: {r['min_d']}")
    print(f"  最晚: {r['max_d']}")

print()
print("=== 最近 10 场已结束比赛 ===")
for r in conn.execute("SELECT match_id, home_name, away_name, home_goals, away_goals, match_date FROM matches WHERE status='FINISHED' ORDER BY match_date DESC LIMIT 10"):
    print(f"  {r['match_id']:>4}  {r['home_name']} {r['home_goals']}-{r['away_goals']} {r['away_name']}  {r['match_date'][:10]}")

print()
print("=== 状态=SCHEDULED/SCHEDULE/UPCOMING 等，模糊搜 ===")
for r in conn.execute("SELECT DISTINCT status FROM matches"):
    print(f"  [{r['status']}]")

conn.close()
