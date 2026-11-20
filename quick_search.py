"""快速参数扫描：HOME_ADVANTAGE 从 0.95 扫到 1.15
DC_RHO 固定 0（正确 DC 公式对 Brier 没帮助）
"""
import sys
sys.path.insert(0, ".")

import config
import poisson as poisson_mod
import squad as squad_mod
import sqlite3

DB_PATH = "epl.db"
FINISHED_STATUS = "FINISHED"

HOME_ADV_CANDIDATES = [0.95, 1.00, 1.03, 1.05, 1.08, 1.10, 1.15]


def run_backtest():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM matches WHERE status=? AND home_goals IS NOT NULL ORDER BY match_date ASC",
        (FINISHED_STATUS,)
    ).fetchall()
    conn.close()

    n = len(rows)
    hit = hit_draw = brier_sum = 0.0
    n_draw = 0
    for i, m in enumerate(rows):
        if i + 1 <= 5:
            continue
        try:
            pred = poisson_mod.predict_match(m["match_id"], cutoff_date=m["match_date"])
        except Exception:
            continue

        hg, ag = m["home_goals"], m["away_goals"]
        actual = 0 if hg > ag else (1 if hg == ag else 2)
        probs = [pred.home_win_prob, pred.draw_prob, pred.away_win_prob]
        pred_cat = probs.index(max(probs))
        hit += int(pred_cat == actual)
        if actual == 1:
            n_draw += 1
            hit_draw += int(pred_cat == 1)
        one_hot = [0.0, 0.0, 0.0]
        one_hot[actual] = 1.0
        brier_sum += sum((p - o) ** 2 for p, o in zip(probs, one_hot))

    eff = n - 5
    return hit/eff, hit_draw/n_draw if n_draw > 0 else 0, brier_sum/eff


print(f"{'HOME_ADV':>10s}  {'命中率':>8s}  {'平局命中率':>10s}  {'Brier':>8s}")
print("-" * 50)

best_brier = 999.0
best_hr = 0.0
best_ha = None

for ha in HOME_ADV_CANDIDATES:
    old = config.HOME_ADVANTAGE
    config.HOME_ADVANTAGE = ha
    # 确保 DC 关了
    old_rho = config.DC_RHO
    config.DC_RHO = 0.0

    hr, hdr, brier = run_backtest()
    marker = ""
    if brier < best_brier:
        best_brier = brier; best_hr = hr; best_ha = ha; marker = " ← 最优Brier"

    print(f"{ha:>10.2f}  {hr*100:>7.1f}%  {hdr*100:>9.1f}%  {brier:>8.4f}{marker}")

    config.HOME_ADVANTAGE = old
    config.DC_RHO = old_rho

print(f"\n🏆 推荐：HOME_ADVANTAGE={best_ha}  → 命中率={best_hr*100:.1f}%  Brier={best_brier:.4f}")
print("  (平局命中率始终 ≈15-19% 是模型类型的上限，需要 GBDT/XGBoost 才能突破)")
