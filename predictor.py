"""预测记录入库 + 回测标记
每次预测完写入 predict_records，比赛结束后回填命中情况
"""
from __future__ import annotations

from typing import List, Optional

from poisson import predict_match, PredictionResult
from db import get_conn
from config import UPCOMING_STATUSES, FINISHED_STATUS


def save_prediction(r: PredictionResult) -> int:
    """把预测结果存入 predict_records，返回 record_id"""
    top = r.top_scores[0]   # 最高概率比分
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO predict_records
               (match_id, lambda_home, lambda_away,
                home_win_prob, draw_prob, away_win_prob,
                top_score, top_score_prob)
               VALUES (?,?,?,?,?,?,?,?)""",
            (r.match_id, r.lambda_home, r.lambda_away,
             r.home_win_prob, r.draw_prob, r.away_win_prob,
             top["score"], top["prob"])
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def predict_all_scheduled() -> List[PredictionResult]:
    """对所有未赛比赛跑一遍预测 + 入库"""
    conn = get_conn()
    try:
        placeholders = ",".join("?" * len(UPCOMING_STATUSES))
        rows = conn.execute(
            f"SELECT match_id FROM matches WHERE status IN ({placeholders}) "
            "ORDER BY match_date",
            tuple(sorted(UPCOMING_STATUSES))
        ).fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        r = predict_match(row["match_id"])
        save_prediction(r)
        results.append(r)
    return results


# ============================================================
# 回填：用已结束比赛更新历史预测记录的 hit/brier
# ============================================================
def backfill_outcomes() -> int:
    """扫描已结束比赛，把对应的 predict_records 标记是否命中"""
    conn = get_conn()
    try:
        # 所有已结束且有赛果的比赛
        finished = conn.execute(
            """SELECT match_id, home_goals, away_goals
               FROM matches
               WHERE status=?
                 AND home_goals IS NOT NULL
                 AND away_goals IS NOT NULL""",
            (FINISHED_STATUS,)
        ).fetchall()

        updated = 0
        for m in finished:
            records = conn.execute(
                "SELECT * FROM predict_records WHERE match_id=? AND hit_result IS NULL",
                (m["match_id"],)
            ).fetchall()
            actual_h, actual_a = m["home_goals"], m["away_goals"]
            actual_result = 0 if actual_h > actual_a else (1 if actual_h == actual_a else 2)
            actual_score = f"{actual_h}-{actual_a}"

            for rec in records:
                probs = [rec["home_win_prob"], rec["draw_prob"], rec["away_win_prob"]]
                pred_result = probs.index(max(probs))

                # Brier score: 三项概率 vs one-hot 真实结果
                one_hot = [0.0, 0.0, 0.0]
                one_hot[actual_result] = 1.0
                brier = sum((p - o) ** 2 for p, o in zip(probs, one_hot))

                hit_r = 1 if pred_result == actual_result else 0
                hit_s = 1 if rec["top_score"] == actual_score else 0

                conn.execute(
                    """UPDATE predict_records
                       SET actual_home=?, actual_away=?,
                           hit_result=?, hit_score=?, brier_score=?
                       WHERE record_id=?""",
                    (actual_h, actual_a, hit_r, hit_s, round(brier, 4),
                     rec["record_id"])
                )
                updated += 1
        conn.commit()
        return updated
    finally:
        conn.close()


if __name__ == "__main__":
    from db import init_db
    from fetcher import fetch_data
    init_db()
    fetch_data()
    saved = predict_all_scheduled()
    print(f"\n共预测并入库 {len(saved)} 场")
    # 模拟：用已结束比赛跑回填（如果有的话）
    n = backfill_outcomes()
    print(f"回填标记了 {n} 条历史预测")
