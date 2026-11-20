"""诊断脚本 - 看 DB 里球队真实攻防强度"""
import sqlite3

conn = sqlite3.connect("epl.db")
conn.row_factory = sqlite3.Row

print("=== 待预测比赛 ===")
for r in conn.execute("SELECT match_id, home_name, away_name, match_date FROM matches WHERE status='SCHEDULED' LIMIT 10"):
    print(f"  {r['match_id']}  {r['home_name']} vs {r['away_name']}  {r['match_date']}")

print()
print("=== 球队攻防强度（按客场进球排序，最低在前）===")
for r in conn.execute("SELECT team_id, name, avg_home_goals, avg_home_conceded, avg_away_goals, avg_away_conceded FROM teams ORDER BY avg_away_goals"):
    print(f"  {r['team_id']:>3} {r['name']:<25}  H_goals={r['avg_home_goals']:.2f} H_conc={r['avg_home_conceded']:.2f}  |  A_goals={r['avg_away_goals']:.2f} A_conc={r['avg_away_conceded']:.2f}")

print()
print("=== 每队已完成比赛数 ===")
for r in conn.execute("""
    SELECT t.team_id, t.name,
        (SELECT COUNT(*) FROM matches m WHERE m.home_team_id = t.team_id AND m.status='FINISHED') AS home_n,
        (SELECT COUNT(*) FROM matches m WHERE m.away_team_id = t.team_id AND m.status='FINISHED') AS away_n
    FROM teams t
"""):
    print(f"  {r['team_id']:>3} {r['name']:<25} home_done={r['home_n']} away_done={r['away_n']}")

print()
print("=== Man Utd 客场表现详情 ===")
uid = [r for r in conn.execute("SELECT team_id FROM teams WHERE name LIKE '%Manchester United%'")][0]["team_id"]
print(f"  Man Utd team_id = {uid}")
for r in conn.execute("SELECT home_name, away_name, home_goals, away_goals, match_date FROM matches WHERE away_team_id=? AND status='FINISHED' ORDER BY match_date DESC", (uid,)):
    print(f"    vs {r['home_name']}  {r['home_goals']}-{r['away_goals']}  {r['match_date']}")

conn.close()
