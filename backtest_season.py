"""穿越式回测：对每场已结束比赛，假装在它比赛前一天，
只用之前的数据算攻防强度+预测，对比有/无阵容惩罚的效果。
"""
import sqlite3
from typing import List, Dict

from poisson import predict_match
from config import DB_PATH, FINISHED_STATUS
import squad as squad_mod


def run_backtest(min_history: int = 5) -> Dict:
    """
    min_history: 至少需要多少场历史才开始回测（前几场冷启动不准）
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 所有已结束比赛，按日期升序
    all_finished = conn.execute(
        "SELECT * FROM matches WHERE status=? AND home_goals IS NOT NULL "
        "ORDER BY match_date ASC",
        (FINISHED_STATUS,)
    ).fetchall()
    conn.close()

    print(f"共 {len(all_finished)} 场已结束比赛")
    print(f"前 {min_history} 场冷启动跳过")

    # === 有惩罚回测 ===
    records_yes = _backtest_loop(all_finished, min_history, use_penalty=True)
    # === 无惩罚回测 ===
    records_no = _backtest_loop(all_finished, min_history, use_penalty=False)

    return {
        "total": len(records_yes),
        "yes": _summarize(records_yes, "有阵容惩罚"),
        "no":  _summarize(records_no,  "无阵容惩罚"),
        "records_yes": records_yes,
        "records_no": records_no,
    }


def _backtest_loop(all_finished, min_history: int, use_penalty: bool) -> List[Dict]:
    """遍历每场比赛，模拟当时场景做预测"""
    # 临时切换惩罚开关
    orig = squad_mod.STAR_PLAYER_PENALTY
    if not use_penalty:
        squad_mod.STAR_PLAYER_PENALTY = 1.0

    records = []
    total = len(all_finished)

    for i, m in enumerate(all_finished):
        if i + 1 <= min_history:
            continue   # 跳过冷启动

        cutoff = m["match_date"]  # 这场比赛的时间点
        try:
            pred = predict_match(m["match_id"], cutoff_date=cutoff)
        except Exception as e:
            print(f"  ⚠ match {m['match_id']} 预测失败：{e}")
            continue

        # 真实赛果
        hg, ag = m["home_goals"], m["away_goals"]
        actual_result = 0 if hg > ag else (1 if hg == ag else 2)  # 0=主胜 1=平 2=客胜
        actual_score = f"{hg}-{ag}"

        # 预测结果
        probs = [pred.home_win_prob, pred.draw_prob, pred.away_win_prob]
        pred_result = probs.index(max(probs))
        pred_score = pred.top_scores[0]["score"]

        # Brier
        one_hot = [0.0, 0.0, 0.0]
        one_hot[actual_result] = 1.0
        brier = sum((p - o) ** 2 for p, o in zip(probs, one_hot))

        records.append({
            "match_id": m["match_id"],
            "home": m["home_name"],
            "away": m["away_name"],
            "date": m["match_date"][:10],
            "actual_hg": hg, "actual_ag": ag,
            "actual_result": actual_result,
            "actual_score": actual_score,
            "pred_hw": pred.home_win_prob,
            "pred_draw": pred.draw_prob,
            "pred_aw": pred.away_win_prob,
            "pred_result": pred_result,
            "pred_top_score": pred_score,
            "hit_result": int(pred_result == actual_result),
            "hit_score": int(pred_score == actual_score),
            "brier": brier,
            "penalty_home": pred.penalty_home.penalty_factor if pred.penalty_home else 1.0,
            "penalty_away": pred.penalty_away.penalty_factor if pred.penalty_away else 1.0,
        })

        if len(records) % 20 == 0:
            print(f"  进度：{len(records)}/{total - min_history}")

    squad_mod.STAR_PLAYER_PENALTY = orig
    return records


def _summarize(records: List[Dict], label: str) -> Dict:
    if not records:
        return {"label": label}
    n = len(records)
    hit_r = sum(r["hit_result"] for r in records)
    hit_s = sum(r["hit_score"] for r in records)
    avg_brier = sum(r["brier"] for r in records) / n

    # 主胜/平/客胜分项命中率
    by_actual = {}
    for r in records:
        cat = r["actual_result"]
        by_actual.setdefault(cat, []).append(r)
    cat_names = {0: "主胜", 1: "平局", 2: "客胜"}

    cat_stats = {}
    for cat, recs in by_actual.items():
        nr = len(recs)
        h = sum(r["hit_result"] for r in recs)
        cat_stats[cat_names[cat]] = f"{h}/{nr} ({h/nr*100:.0f}%)"

    return {
        "label": label,
        "n": n,
        "hit_result": hit_r,
        "hit_score": hit_s,
        "hr_rate": hit_r / n,
        "hs_rate": hit_s / n,
        "avg_brier": avg_brier,
        "cat_stats": cat_stats,
    }


def print_report(res: Dict) -> None:
    W = 65
    print("\n" + "=" * W)
    print("  🏆 穿越式回测报告（只看当时已有数据）")
    print("=" * W)

    for key in ("yes", "no"):
        s = res[key]
        if "n" not in s:
            continue
        print(f"\n【{s['label']}】  共 {s['n']} 场")
        print(f"  胜平负命中率：{s['hit_result']}/{s['n']} = {s['hr_rate']*100:.1f}%")
        print(f"  比分命中率：  {s['hit_score']}/{s['n']} = {s['hs_rate']*100:.1f}%")
        print(f"  平均 Brier Score：{s['avg_brier']:.4f}")
        print(f"  分项命中：", end="")
        for cat, v in s["cat_stats"].items():
            print(f"  {cat}:{v}", end="")
        print()

    # === 对比 ===
    y, n = res["yes"], res["no"]
    if "n" in y and "n" in n:
        print(f"\n{'─' * W}")
        print(f"  📊 有 vs 无 阵容惩罚 对比")
        print(f"{'─' * W}")
        hr_diff = (y["hr_rate"] - n["hr_rate"]) * 100
        brier_diff = y["avg_brier"] - n["avg_brier"]
        print(f"  命中率变动：  {y['hr_rate']*100:.1f}%  vs {n['hr_rate']*100:.1f}%  "
              f"→ {'↑' if hr_diff > 0 else '↓'} {abs(hr_diff):.1f}pp")
        print(f"  Brier 变动：  {y['avg_brier']:.4f}  vs {n['avg_brier']:.4f}  "
              f"→ {'↓更好' if brier_diff < 0 else '↑更差'} {abs(brier_diff):.4f}")

        # 找差异较大的场次
        print(f"\n{'─' * W}")
        print(f"  命中变动场次（有惩罚把原来错的变对，或对的变错）：")
        print(f"{'─' * W}")
        y_map = {r["match_id"]: r for r in res["records_yes"]}
        n_map = {r["match_id"]: r for r in res["records_no"]}
        changes = []
        for mid in y_map:
            yr, nr = y_map[mid], n_map[mid]
            if yr["hit_result"] != nr["hit_result"]:
                changes.append((yr, nr))
        if changes:
            for yr, nr in changes[:15]:
                diff_mark = "🟢惩罚救命" if yr["hit_result"] and not nr["hit_result"] else "🔴惩罚添乱"
                penalty_note = ""
                if yr["penalty_home"] < 1.0:
                    penalty_note += f" {yr['home']}×{yr['penalty_home']}"
                if yr["penalty_away"] < 1.0:
                    penalty_note += f" {yr['away']}×{yr['penalty_away']}"
                print(f"  {diff_mark}  {yr['date']}  {yr['home']} vs {yr['away']}  "
                      f"真实 {yr['actual_score']}  "
                      f"无罚预测={nr['pred_top_score']}(命中={nr['hit_result']})  "
                      f"有罚预测={yr['pred_top_score']}(命中={yr['hit_result']})"
                      f"{penalty_note}")
        else:
            print("  命中率完全一致，惩罚没造成翻案（可能还没覆盖到关键场次）")

    print(f"\n{'=' * W}")
    print(f"  Brier 越低越好，一般英超模型 0.55~0.65 合理")
    print(f"{'=' * W}\n")


if __name__ == "__main__":
    result = run_backtest(min_history=5)
    print_report(result)
