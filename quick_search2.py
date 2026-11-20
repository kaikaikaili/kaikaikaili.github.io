"""快速参数扫描（修复版：直接设 poisson 模块变量）"""
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


print(f"{'HOME_ADV':>10s}  {'命中率':>8s}  {'平局命中率':>10s}  {'Brier':>8s}  {'λ_h/λ_a样例':>12s}")
print("-" * 62)

best_brier = 999.0
best_hr = 0.0
best_ha = None

for ha in HOME_ADV_CANDIDATES:
    # 直接设 poisson 模块里的值（因为 from config import HOME_ADVANTAGE 是值拷贝）
    poisson_mod.HOME_ADVANTAGE = ha
    poisson_mod.DC_RHO = 0.0  # 关闭 DC 修正

    hr, hdr, brier = run_backtest()

    # 拿一场的 λ 比例作参考
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    sample_mid = conn.execute(
        "SELECT match_id FROM matches WHERE status='FINISHED' ORDER BY match_date ASC LIMIT 6,1"
    ).fetchone()["match_id"]
    conn.close()
    sample_pred = poisson_mod.predict_match(sample_mid, cutoff_date="2026-09-01T00:00:00Z")
    lam_ratio = f"{sample_pred.lambda_home}/{sample_pred.lambda_away}"

    marker = ""
    if brier < best_brier:
        best_brier = brier; best_hr = hr; best_ha = ha; marker = " ← 最优"

    print(f"{ha:>10.2f}  {hr*100:>7.1f}%  {hdr*100:>9.1f}%  {brier:>8.4f}  {lam_ratio:>12s}{marker}")

print(f"\n🏆 推荐 HOME_ADVANTAGE={best_ha}")
