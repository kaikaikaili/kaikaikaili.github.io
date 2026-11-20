"""对比：有阵容惩罚 vs 无阵容惩罚的预测差异"""
import datetime as dt
import sqlite3
from copy import deepcopy

# ===== 先跑"无惩罚"版本：临时把惩罚系数设为 1.0 =====
import squad as squad_no_penalty
_orig = squad_no_penalty.STAR_PLAYER_PENALTY
squad_no_penalty.STAR_PLAYER_PENALTY = 1.0   # 禁用

from poisson import predict_match
from predictor import predict_all_scheduled
from db import init_db, get_conn

# 清空旧预测，重跑
conn = get_conn()
conn.execute("DELETE FROM predict_records")
conn.commit()
conn.close()

print(">>> 第 1 轮：无阵容惩罚...")
results_no = predict_all_scheduled()

# ===== 恢复正常惩罚 =====
squad_no_penalty.STAR_PLAYER_PENALTY = _orig

conn = get_conn()
conn.execute("DELETE FROM predict_records")
conn.commit()
conn.close()

print(">>> 第 2 轮：有阵容惩罚...")
results_yes = predict_all_scheduled()

# ===== 对比 =====
from dataclasses import asdict

print()
print("=" * 80)
print("  有阵容惩罚  VS  无阵容惩罚 —— 差异对比")
print("=" * 80)
print(f"  比赛总数：{len(results_yes)}")

# 逐场对比
diffs = []
for r_yes, r_no in zip(results_yes, results_no):
    d_home = r_yes.lambda_home - r_no.lambda_home
    d_away = r_yes.lambda_away - r_no.lambda_away
    d_hw   = r_yes.home_win_prob - r_no.home_win_prob
    d_draw = r_yes.draw_prob - r_no.draw_prob
    d_aw   = r_yes.away_win_prob - r_no.away_win_prob

    # 综合差异（概率差的绝对值之和）
    total_prob_shift = abs(d_hw) + abs(d_draw) + abs(d_aw)
    diffs.append((total_prob_shift, r_yes, r_no, d_home, d_away, d_hw, d_draw, d_aw))

diffs.sort(key=lambda x: -x[0])   # 按综合差异倒序

# 汇总统计
changed = sum(1 for d in diffs if d[0] > 0.01)   # 概率变动 > 1% 的场数
avg_shift = sum(d[0] for d in diffs) / len(diffs)
max_shift = diffs[0][0] if diffs else 0

print(f"  有差异的比赛（概率变化 > 1%）：{changed}/{len(results_yes)}")
print(f"  平均综合概率偏移：{avg_shift*100:.2f}%")
print(f"  最大单场综合偏移：{max_shift*100:.2f}%")
print()

# Top 10 差异最大的
print("-" * 80)
print(f"  Top 10 差异最大的比赛：")
print("-" * 80)

for i, (total_shift, r_yes, r_no, dh, da, dhw, dd, daw) in enumerate(diffs[:10]):
    print(f"\n  #{i+1}  {r_yes.home_name} VS {r_yes.away_name}")
    print(f"  综合概率变动：±{total_shift*100:.1f}%")
    print(f"  {'':10s}  {'无惩罚':>10s}  {'有惩罚':>10s}  {'变动':>10s}")
    print(f"  {'λ_home':10s}  {r_no.lambda_home:>10.3f}  {r_yes.lambda_home:>10.3f}  {dh:>+10.3f}")
    print(f"  {'λ_away':10s}  {r_no.lambda_away:>10.3f}  {r_yes.lambda_away:>10.3f}  {da:>+10.3f}")
    print(f"  {'主胜概率':10s}  {r_no.home_win_prob*100:>9.1f}%  {r_yes.home_win_prob*100:>9.1f}%  {dhw*100:>+9.1f}%")
    print(f"  {'平局概率':10s}  {r_no.draw_prob*100:>9.1f}%  {r_yes.draw_prob*100:>9.1f}%  {dd*100:>+9.1f}%")
    print(f"  {'客胜概率':10s}  {r_no.away_win_prob*100:>9.1f}%  {r_yes.away_win_prob*100:>9.1f}%  {daw*100:>+9.1f}%")
    # 哪队被惩罚了
    penalized = []
    if r_yes.penalty_home and r_yes.penalty_home.star_absent_count > 0:
        penalized.append(f"{r_yes.home_name} ×{r_yes.penalty_home.penalty_factor}")
    if r_yes.penalty_away and r_yes.penalty_away.star_absent_count > 0:
        penalized.append(f"{r_yes.away_name} ×{r_yes.penalty_away.penalty_factor}")
    if penalized:
        print(f"  惩罚触发：{'  '.join(penalized)}")

print()
print("=" * 80)
print("  说明：正值=惩罚后概率上升，负值=下降")
print("  λ 下降 = 该队进攻被抑制（推断有核心缺阵）")
print("=" * 80)
