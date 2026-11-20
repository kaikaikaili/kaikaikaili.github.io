"""找出触发惩罚的球队，看看未来赛程里会不会被用到"""
import sqlite3
from squad import adjust_lambda
from poisson import predict_match

conn = sqlite3.connect("epl.db")
conn.row_factory = sqlite3.Row

triggers = [
    ("Hull City AFC", False),
    ("Leeds United FC", True),
    ("Brighton & Hove Albion FC", False),
    ("Crystal Palace FC", False),
]

# 先找这些队的 team_id
for team_name, is_home in triggers:
    tid_row = conn.execute("SELECT team_id FROM teams WHERE name=?", (team_name,)).fetchone()
    if not tid_row:
        print(f"⚠ 没找到球队：{team_name}")
        continue
    tid = tid_row["team_id"]
    label = "主场" if is_home else "客场"

    # 看 adjust_lambda 对这个队这个场地的判断
    adj = adjust_lambda(1.5, tid, is_home=is_home)
    print(f"[{team_name} {label}] 惩罚×{adj.penalty_factor}  缺阵≈{adj.star_absent_count}")

    # 找未来 TIMED 里该队以该场地出战的比赛
    where_col = "home_team_id" if is_home else "away_team_id"
    rows = conn.execute(
        f"SELECT match_id, home_name, away_name FROM matches "
        f"WHERE status='TIMED' AND {where_col}=? LIMIT 3",
        (tid,)
    ).fetchall()

    if not rows:
        print(f"  → 未来赛程里没有{label}比赛，惩罚不会被用到！")
    else:
        for r in rows:
            # 直接跑预测看惩罚是否触发
            pred = predict_match(r["match_id"])
            pen = pred.penalty_home if is_home else pred.penalty_away
            print(f"  → match {r['match_id']}: {r['home_name']} vs {r['away_name']}  "
                  f"{'⚠ 惩罚触发' if pen and pen.star_absent_count > 0 else '无惩罚'}")
    print()

conn.close()
