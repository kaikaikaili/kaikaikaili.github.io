"""回测统计面板：命中率、Brier 分数"""
from __future__ import annotations


def print_backtest_summary() -> None:
    from db import get_conn
    conn = get_conn()
    try:
        # 总记录数 & 已回填数
        total = conn.execute("SELECT COUNT(*) AS c FROM predict_records").fetchone()["c"]
        done = conn.execute(
            "SELECT COUNT(*) AS c FROM predict_records WHERE hit_result IS NOT NULL"
        ).fetchone()["c"]

        # 胜平负命中率
        r = conn.execute(
            """SELECT
                 COUNT(*) AS n,
                 SUM(hit_result) AS hit_r,
                 SUM(hit_score)  AS hit_s,
                 AVG(brier_score) AS avg_brier
               FROM predict_records WHERE hit_result IS NOT NULL"""
        ).fetchone()

        print("\n" + "=" * 56)
        print("  📊 预测回测统计面板")
        print("=" * 56)
        print(f"  总预测记录：{total}")
        print(f"  已回填赛果：{done}")
        print("-" * 56)
        if done == 0:
            print("  还没有可回测的记录 —— 多预测几场、等比赛结束再跑")
        else:
            print(f"  胜平负命中率：{r['hit_r']}/{r['n']} = "
                  f"{r['hit_r']/r['n']*100:.1f}%")
            print(f"  比分命中率：  {r['hit_s']}/{r['n']} = "
                  f"{r['hit_s']/r['n']*100:.1f}%")
            print(f"  平均 Brier Score：{r['avg_brier']:.3f}  (越低越好)")

            # 最近 5 条预测明细
            print("-" * 56)
            print("  最近 5 条预测明细：")
            rows = conn.execute(
                """SELECT pr.*, m.home_name, m.away_name
                   FROM predict_records pr
                   JOIN matches m ON pr.match_id = m.match_id
                   ORDER BY pr.record_id DESC LIMIT 5"""
            ).fetchall()
            for row in rows:
                if row["hit_result"] is None:
                    status = "待开奖"
                else:
                    status = ("✅" if row["hit_result"] else "❌") + \
                             f" 比分命中={'✅' if row['hit_score'] else '❌'}"
                print(f"    {row['home_name']} vs {row['away_name']}  "
                      f"预测 {row['top_score']}  "
                      f"R={row['home_win_prob']:.0%}/{row['draw_prob']:.0%}/{row['away_win_prob']:.0%}  "
                      f"{status}")
        print("=" * 56)
        print("  ⚠ Brier Score 范围 [0, 2]，0=完美，2=最差")
        print("    一般英超模型 Brier ≈ 0.55~0.65 算合理")
        print("=" * 56 + "\n")
    finally:
        conn.close()


if __name__ == "__main__":
    print_backtest_summary()
