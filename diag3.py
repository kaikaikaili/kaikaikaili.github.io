"""直接调 detect_injury_risk 调试"""
import sqlite3
from squad import detect_injury_risk

conn = sqlite3.connect("epl.db")
conn.row_factory = sqlite3.Row

# 看 Hull City AFC (team_id=397?) 完整客场历史
row = conn.execute("SELECT team_id FROM teams WHERE name='Hull City AFC'").fetchone()
tid = row["team_id"]
print(f"Hull City AFC team_id = {tid}")

# 完整客场历史
print("\n完整客场历史：")
for r in conn.execute(
    "SELECT away_goals, home_goals AS opponent_home, match_date FROM matches "
    "WHERE away_team_id=? AND status='FINISHED' ORDER BY match_date DESC",
    (tid,)
):
    print(f"  away_g={r['away_goals']}  match_date={r['match_date'][:10]}")

# 直接调
risk = detect_injury_risk(tid, is_home=False)
print(f"\ndetect_injury_risk(tid={tid}, is_home=False) = {risk}")

# 看 detect_injury_risk 里的 long_avg 和 recent_avg
long = conn.execute(
    "SELECT AVG(away_goals) AS avg_gf FROM matches WHERE away_team_id=? AND status='FINISHED' ORDER BY match_date DESC LIMIT 10",
    (tid,)
).fetchone()
recent = conn.execute(
    "SELECT AVG(away_goals) AS avg_gf FROM matches WHERE away_team_id=? AND status='FINISHED' ORDER BY match_date DESC LIMIT 3",
    (tid,)
).fetchone()
print(f"long_avg={long['avg_gf']}  recent_avg={recent['avg_gf']}")

if long and long["avg_gf"]:
    ratio = (recent["avg_gf"] or 0) / long["avg_gf"]
    print(f"ratio={ratio}")
    print(f"long_avg < 0.3 ? {long['avg_gf'] < 0.3}")

conn.close()
