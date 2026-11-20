"""快速穿越式回测（4 赛季版，只跑无惩罚，约 1240 场）
每场预测 2-3 次 SQL，总 SQL 数可控。
"""
import sqlite3
import sys
sys.path.insert(0, ".")

import config
import poisson as poisson_mod
import squad as squad_mod

# 先关惩罚加速
orig_penalty = squad_mod.STAR_PLAYER_PENALTY
squad_mod.STAR_PLAYER_PENALTY = 1.0   # 临时关闭，对比过几乎没差异

DB_PATH = "epl.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# 拉所有已结束比赛（1240 场）
all_matches = conn.execute(
    "SELECT * FROM matches WHERE home_goals IS NOT NULL ORDER BY match_date ASC"
).fetchall()
conn.close()

print(f"共 {len(all_matches)} 场已结束比赛")

hit = hit_score = n_draw = hit_draw = 0
brier_sum = 0.0
err = 0

# 统计各赛季独立表现
by_season = {}

for i, m in enumerate(all_matches):
    if i + 1 <= 5:
        continue   # 前 5 场冷启动跳过

    cutoff = m["match_date"]
    try:
        pred = poisson_mod.predict_match(m["match_id"], cutoff_date=cutoff)
    except Exception as e:
        err += 1
        if err <= 3:
            print(f"  err match={m['match_id']}: {e}")
        continue

    hg, ag = m["home_goals"], m["away_goals"]
    actual = 0 if hg > ag else (1 if hg == ag else 2)
    probs = [pred.home_win_prob, pred.draw_prob, pred.away_win_prob]
    pred_cat = probs.index(max(probs))
    pred_top = pred.top_scores[0]["score"]

    hit += int(pred_cat == actual)
    hit_score += int(pred_top == f"{hg}-{ag}")

    if actual == 1:
        n_draw += 1
        hit_draw += int(pred_cat == 1)

    one_hot = [0.0, 0.0, 0.0]
    one_hot[actual] = 1.0
    brier_sum += sum((p - o) ** 2 for p, o in zip(probs, one_hot))

    # 按赛季分组（用 match_date 前 4 位）
    season = m["match_date"][:4]
    s = by_season.setdefault(season, {"n": 0, "hit": 0, "brier": 0.0})
    s["n"] += 1
    s["hit"] += int(pred_cat == actual)
    s["brier"] += sum((p - o) ** 2 for p, o in zip(probs, one_hot))

    if (i + 1) % 200 == 0:
        print(f"  进度：{i+1}/{len(all_matches)}...")

squad_mod.STAR_PLAYER_PENALTY = orig_penalty

eff = len(all_matches) - 5 - err
hr = hit / eff
hpr = hit_score / eff
bd = brier_sum / eff
hdr = hit_draw / n_draw if n_draw > 0 else 0

# 平局概率统计：模型给的平局概率分布
print(f"\n{'='*60}")
print(f"  🏆 4 赛季穿越式回测（HOME_ADV={config.HOME_ADVANTAGE}）")
print(f"{'='*60}")
print(f"  有效样本：{eff} 场  错误：{err} 场")
print(f"  胜平负命中率：{hit}/{eff} = {hr*100:.1f}%")
print(f"  比分命中率：  {hit_score}/{eff} = {hpr*100:.1f}%")
print(f"  平均 Brier Score：{bd:.4f}")
print(f"  平局命中率：  {hit_draw}/{n_draw} = {hdr*100:.1f}%")
print()
print(f"  📅 分赛季表现：")
print(f"  {'赛季':>8s}  {'场次':>6s}  {'命中率':>8s}  {'Brier':>8s}")
print(f"  {'-'*34}")
for season, s in sorted(by_season.items()):
    sh = s["hit"] / s["n"]
    sb = s["brier"] / s["n"]
    print(f"  {season:>8s}  {s['n']:>6d}  {sh*100:>7.1f}%  {sb:>8.4f}")

print(f"\n{'='*60}")
print(f"  英超优秀模型参考：命中率 45-55%  Brier 0.55-0.65")
print(f"{'='*60}")
