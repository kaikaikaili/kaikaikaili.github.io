"""查本赛季已结束比赛的时间分布"""
import sqlite3
c = sqlite3.connect("epl.db"); c.row_factory = sqlite3.Row
finished = c.execute("SELECT COUNT(*) AS c, MIN(match_date) AS min_d, MAX(match_date) AS max_d FROM matches WHERE status='FINISHED'").fetchone()
print(f"已结束：{finished['c']} 场")
print(f"范围：{finished['min_d'][:10]} → {finished['max_d'][:10]}")
print()
print("按月份分布：")
for r in c.execute("SELECT substr(match_date,1,7) AS ym, COUNT(*) AS c FROM matches WHERE status='FINISHED' GROUP BY ym ORDER BY ym"):
    print(f"  {r['ym']}  {r['c']} 场")
print()
print("前 5 场和后 5 场：")
first = c.execute("SELECT match_id, home_name, away_name, home_goals, away_goals, match_date FROM matches WHERE status='FINISHED' ORDER BY match_date ASC LIMIT 5").fetchall()
last = c.execute("SELECT match_id, home_name, away_name, home_goals, away_goals, match_date FROM matches WHERE status='FINISHED' ORDER BY match_date DESC LIMIT 5").fetchall()
for r in first:
    print(f"  FIRST  {r['match_date'][:10]}  {r['home_name']} {r['home_goals']}-{r['away_goals']} {r['away_name']}")
for r in reversed(last):
    print(f"  LAST   {r['match_date'][:10]}  {r['home_name']} {r['home_goals']}-{r['away_goals']} {r['away_name']}")
