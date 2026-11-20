"""查最终 DB 汇总"""
import sqlite3
conn = sqlite3.connect("epl.db")
print(f"{'联赛':>6s}  {'状态':>12s}  {'场次':>6s}")
print("-" * 30)
grand_total = 0
grand_f = 0
for r in conn.execute("SELECT league, status, COUNT(*) AS c FROM matches GROUP BY league, status ORDER BY league, status"):
    print(f"{r[0]:>6s}  {r[1]:>12s}  {r[2]:>6d}")
    grand_total += r[2]
    if r[0] != "SCHEDULED":
        pass

total = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
finished = conn.execute("SELECT COUNT(*) FROM matches WHERE status='FINISHED'").fetchone()[0]
non_sched = conn.execute("SELECT COUNT(*) FROM matches WHERE status NOT IN ('SCHEDULED', 'TIMED', 'AWARDED', 'CANCELLED', 'POSTPONED') OR home_goals IS NOT NULL").fetchone()[0]
teams = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]

print(f"\n总比赛：{total} 场")
print(f"已结束(FINISHED)：{finished} 场")
print(f"球队数：{teams}")
conn.close()
