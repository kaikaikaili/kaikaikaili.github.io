"""网格搜索：HOME_ADV + DC_RHO 的最优组合
直接用 backtest_season 里的穿越回测逻辑扫参数
"""
import sys
sys.path.insert(0, ".")

from config import DB_PATH, FINISHED_STATUS
import config
import squad as squad_mod
import poisson as poisson_mod
import sqlite3

# 要扫的参数
HOME_ADV_CANDIDATES = [1.00, 1.03, 1.05, 1.08, 1.10]
DC_RHO_CANDIDATES = [0.0, 0.05, 0.10, 0.15, 0.20]


def backtest_fixed_params(min_history=5):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    all_finished = conn.execute(
        "SELECT * FROM matches WHERE status=? AND home_goals IS NOT NULL ORDER BY match_date ASC",
        (FINISHED_STATUS,)
    ).fetchall()
    conn.close()

    n = len(all_finished)
    hit = brier_sum = 0.0
    for i, m in enumerate(all_finished):
        if i + 1 <= min_history:
            continue
        cutoff = m["match_date"]
        try:
            pred = poisson_mod.predict_match(m["match_id"], cutoff_date=cutoff)
        except Exception:
            continue

        hg, ag = m["home_goals"], m["away_goals"]
        actual = 0 if hg > ag else (1 if hg == ag else 2)
        probs = [pred.home_win_prob, pred.draw_prob, pred.away_win_prob]
        pred_cat = probs.index(max(probs))
        hit += int(pred_cat == actual)
        one_hot = [0.0, 0.0, 0.0]
        one_hot[actual] = 1.0
        brier_sum += sum((p - o) ** 2 for p, o in zip(probs, one_hot))

    effective = n - min_history
    return hit / effective, brier_sum / effective


best = {"brier": 999.0, "hr": 0.0, "home_adv": None, "dc_rho": None}
results = []

for home_adv in HOME_ADV_CANDIDATES:
    for dc_rho in DC_RHO_CANDIDATES:
        # 临时切换 config
        old_adv = config.HOME_ADVANTAGE
        old_rho = config.DC_RHO
        config.HOME_ADVANTAGE = home_adv
        config.DC_RHO = dc_rho

        hr, brier = backtest_fixed_params()
        results.append((brier, hr, home_adv, dc_rho))

        if brier < best["brier"]:
            best = {"brier": brier, "hr": hr, "home_adv": home_adv, "dc_rho": dc_rho}

        config.HOME_ADVANTAGE = old_adv
        config.DC_RHO = old_rho

# 排序输出
results.sort()
print(f"{'Brier':>8s}  {'命中率':>8s}  HOME_ADV  DC_RHO")
print("-" * 45)
for brier, hr, ha, dr in results:
    marker = " ← 最优" if (ha == best["home_adv"] and dr == best["dc_rho"]) else ""
    print(f"{brier:>8.4f}  {hr*100:>7.1f}%  {ha:>7.2f}  {dr:>5.2f}{marker}")

print()
print(f"🏆 最优参数：HOME_ADVANTAGE={best['home_adv']}  DC_RHO={best['dc_rho']}")
print(f"   Brier={best['brier']:.4f}  命中率={best['hr']*100:.1f}%")
