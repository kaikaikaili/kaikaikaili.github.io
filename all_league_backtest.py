"""全联赛穿越式回测：7314 场已结束，逐联赛输出表现"""
import sqlite3, sys, time
sys.path.insert(0, ".")
import config, poisson as poisson_mod, squad as squad_mod

# 临时关惩罚加速
orig = squad_mod.STAR_PLAYER_PENALTY
squad_mod.STAR_PLAYER_PENALTY = 1.0

conn = sqlite3.connect("epl.db")
conn.row_factory = sqlite3.Row

all_matches = conn.execute(
    "SELECT * FROM matches WHERE home_goals IS NOT NULL ORDER BY match_date ASC"
).fetchall()
total = len(all_matches)
conn.close()

print(f"共 {total} 场已结束比赛，开始穿越式回测...")
t0 = time.time()

# 逐联赛统计
by_league = {}
hit_total = brier_total = 0
err = 0

for i, m in enumerate(all_matches):
    if i + 1 <= 5:
        continue
    try:
        pred = poisson_mod.predict_match(m["match_id"], cutoff_date=m["match_date"])
    except Exception as e:
        err += 1; continue

    hg, ag = m["home_goals"], m["away_goals"]
    actual = 0 if hg > ag else (1 if hg == ag else 2)
    probs = [pred.home_win_prob, pred.draw_prob, pred.away_win_prob]
    pred_cat = probs.index(max(probs))

    one_hot = [0.0, 0.0, 0.0]
    one_hot[actual] = 1.0
    brier = sum((p - o) ** 2 for p, o in zip(probs, one_hot))

    league = m["league"]
    s = by_league.setdefault(league, {"n": 0, "hit": 0, "brier_sum": 0.0, "n_draw": 0, "hit_draw": 0})
    s["n"] += 1
    s["hit"] += int(pred_cat == actual)
    s["brier_sum"] += brier
    hit_total += int(pred_cat == actual)
    brier_total += brier
    if actual == 1:
        s["n_draw"] += 1
        s["hit_draw"] += int(pred_cat == 1)

    if (i + 1) % 1000 == 0:
        elapsed = time.time() - t0
        eta = elapsed / (i+1) * (total - i - 1)
        print(f"  {i+1}/{total}  已跑 {elapsed:.0f}s  剩余约 {eta/60:.1f}min")

squad_mod.STAR_PLAYER_PENALTY = orig
eff = total - 5 - err
elapsed = time.time() - t0

# 联赛名映射
LEAGUE_NAMES = {
    "PL": "英超", "ELC": "英冠", "PD": "西甲", "SA": "意甲",
    "BL1": "德甲", "FL1": "法甲", "PPL": "葡超", "BSA": "巴甲",
    "CL": "欧冠", "CLI": "解放者杯", "WC": "世界杯", "DED": "荷甲",
}

print(f"\n{'='*75}")
print(f"  🏆 全联赛穿越式回测（HOME_ADV={config.HOME_ADVANTAGE}）")
print(f"  总样本 {eff} 场  总耗时 {elapsed:.0f}s  错误 {err} 场")
print(f"{'='*75}")
print(f"\n  {'联赛':>10s}  {'场次':>6s}  {'命中率':>8s}  {'Brier':>8s}  {'平局命中':>10s}")
print(f"  {'-'*55}")

for lg, s in sorted(by_league.items()):
    hr = s["hit"] / s["n"]
    bd = s["brier_sum"] / s["n"]
    dhr = (s["hit_draw"] / s["n_draw"] * 100) if s["n_draw"] > 0 else 0
    ln = LEAGUE_NAMES.get(lg, lg)
    print(f"  {ln:>10s}  {s['n']:>6d}  {hr*100:>7.1f}%  {bd:>8.4f}  {dhr:>7.1f}% ({s['hit_draw']}/{s['n_draw']})")

# 总览
total_hr = hit_total / eff
total_bd = brier_total / eff
print(f"\n  {'─'*55}")
print(f"  {'总计':>10s}  {eff:>6d}  {total_hr*100:>7.1f}%  {total_bd:>8.4f}")

print(f"\n{'='*75}")
print(f"  英超优秀模型参考：命中率 45-55%  Brier 0.55-0.65")
print(f"{'='*75}\n")
