"""方案 A 效果验证：同一场比赛，有/无惩罚对比"""
import sqlite3

from config import DB_PATH
from fetcher import load_mock_data
from db import init_db, get_conn

# 用 mock 数据先测（mock 数据均匀，不会触发惩罚）
# 我们人为造一个"弱队连续 3 场进球 0"的场景来强制触发
init_db()
load_mock_data()

conn = get_conn()
# 把 Chelsea 的最近 3 场客场进球改成 0
conn.execute("""UPDATE matches SET away_goals=0
                WHERE rowid IN (
                    SELECT rowid FROM matches
                    WHERE away_team_id=105 AND status='FINISHED'
                    ORDER BY match_date DESC LIMIT 3
                )""")
conn.commit()
conn.close()

# 重算强度（我们没调这个脚本，手动算一下就行——主要是看惩罚会不会触发）
from squad import adjust_lambda

# 验证：Chelsea (105) 客场，应该触发惩罚
adj = adjust_lambda(1.2, team_id=105, is_home=False)
print(f"Chelsea 客场：惩罚={adj.penalty_factor}  缺阵≈{adj.star_absent_count}  原因={adj.reason}")

# 用 poisson 跑一场预测看完整输出
from poisson import predict_match, print_prediction

# City vs Liverpool 那场
r = predict_match(2001)
print_prediction(r)

# 对比：有没有惩罚都×1.0 的
r2 = predict_match(2002)
print_prediction(r2)
