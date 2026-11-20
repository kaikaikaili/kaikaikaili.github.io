"""导出所有预测结果为 txt 报告"""
import datetime as dt
import sqlite3

from config import DB_PATH


def export_txt(out_path: str = None) -> str:
    if out_path is None:
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M")
        out_path = DB_PATH.parent / f"predictions_{ts}.txt"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 所有有预测的比赛（从 predict_records JOIN matches）
    rows = conn.execute(
        """SELECT pr.*, m.home_name, m.away_name, m.match_date
           FROM predict_records pr
           JOIN matches m ON pr.match_id = m.match_id
           ORDER BY m.match_date"""
    ).fetchall()

    # 回测统计
    stats = conn.execute(
        """SELECT
             COUNT(*) AS total,
             SUM(CASE WHEN hit_result IS NOT NULL THEN 1 ELSE 0 END) AS done,
             SUM(CASE WHEN hit_result = 1 THEN 1 ELSE 0 END) AS hit_r,
             SUM(CASE WHEN hit_score = 1 THEN 1 ELSE 0 END) AS hit_s,
             AVG(brier_score) AS avg_brier
           FROM predict_records"""
    ).fetchone()

    conn.close()

    lines = []
    W = 70
    def line(s=""):
        lines.append(s)

    line("=" * W)
    line("  英超泊松概率预测 · 完整报告")
    line("  生成时间：" + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    line("=" * W)
    line()

    # 回测概览
    line("【回测统计概览】")
    line(f"  总预测场次：{stats['total']}")
    line(f"  已回填赛果：{stats['done']}")
    if stats["done"] and stats["done"] > 0:
        line(f"  胜平负命中率：{stats['hit_r']}/{stats['done']} = "
             f"{stats['hit_r']/stats['done']*100:.1f}%")
        line(f"  比分命中率：  {stats['hit_s']}/{stats['done']} = "
             f"{stats['hit_s']/stats['done']*100:.1f}%")
        line(f"  平均 Brier Score：{stats['avg_brier']:.3f}")
    else:
        line("  （暂无已结束赛果，等比赛结束后跑 python main.py backfill）")
    line()
    line("-" * W)
    line()

    # 按日期分组
    from collections import OrderedDict
    grouped = OrderedDict()
    for r in rows:
        d = r["match_date"][:10]
        grouped.setdefault(d, []).append(r)

    line("【全部预测结果 · 按日期排序】")
    line()
    for date, match_list in grouped.items():
        line(f"── {date}  ({len(match_list)} 场) ──")
        line()
        for r in match_list:
            # 概率条形（终端风格）
            hw, dw, aw = r["home_win_prob"], r["draw_prob"], r["away_win_prob"]
            B = 16
            def bar(p):
                return "█" * int(p * B) + "░" * (B - int(p * B))

            line(f"  {r['home_name']}  VS  {r['away_name']}")
            line(f"    λ_home={r['lambda_home']}   λ_away={r['lambda_away']}")
            line(f"    主胜 {bar(hw)} {hw*100:5.1f}%")
            line(f"    平局 {bar(dw)} {dw*100:5.1f}%")
            line(f"    客胜 {bar(aw)} {aw*100:5.1f}%")
            top5 = ""  # top score
            top_score_info = ""
            line(f"    Top比分：{r['top_score']}  (概率 {r['top_score_prob']*100:.1f}%)")
            line()

    line("=" * W)
    line("  ⚠ 免责声明：")
    line("  本工具仅基于历史数据做统计概率推演，不构成任何投注建议。")
    line("  足球存在大量偶然性，过往数据不代表未来表现。")
    line("=" * W)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ 报告已导出：{out_path}")
    print(f"   共 {len(rows)} 场预测")
    return str(out_path)


if __name__ == "__main__":
    export_txt()
