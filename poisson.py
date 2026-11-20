"""加权泊松分布足球预测模型
核心公式（Dixon-Coles 简化版，MVP 够用）：
  1. λ_home = home_att × away_def × league_avg × HOME_ADVANTAGE
  2. λ_away = away_att × home_def × league_avg
  3. P(home_g=k) = Poisson(k, λ_home)
  4. 遍历 (0..MAX_GOALS, 0..MAX_GOALS) 所有比分组合
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List

from config import HOME_ADVANTAGE, MAX_GOALS, FINISHED_STATUS, DC_RHO
from db import get_conn
from squad import adjust_lambda, SquadAdjustment


@dataclass
class TeamStrength:
    team_id: int
    name: str
    home_att: float       # 主场进攻强度
    home_def: float       # 主场防守强度
    away_att: float       # 客场进攻强度
    away_def: float       # 客场防守强度


@dataclass
class PredictionResult:
    match_id: int
    home_name: str
    away_name: str
    lambda_home: float
    lambda_away: float
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    top_scores: List[Dict]   # [{"score": "2-1", "prob": 0.135}, ...]
    league_avg_goals: float
    # 方案 A：阵容惩罚信息
    penalty_home: SquadAdjustment | None = None
    penalty_away: SquadAdjustment | None = None


# ============================================================
# 泊松 PMF
# ============================================================
def poisson_pmf(k: int, lam: float) -> float:
    """P(X = k) 服从 Poisson(λ)"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    # log 空间计算防下溢
    log_p = -lam + k * math.log(lam) - math.lgamma(k + 1)
    return math.exp(log_p)


# ============================================================
# 球队攻防强度计算（从 DB 读，可选 cutoff_date 做时间切片）
# ============================================================
def _get_league_avg(cutoff_date: str | None = None) -> Dict[str, float]:
    """联赛整体平均进球（主场/客场/总平均）"""
    conn = get_conn()
    try:
        if cutoff_date:
            row = conn.execute(
                """SELECT
                     AVG(home_goals) AS avg_home,
                     AVG(away_goals) AS avg_away,
                     AVG(home_goals + away_goals) AS avg_total
                   FROM matches WHERE status=? AND match_date < ?""",
                (FINISHED_STATUS, cutoff_date)
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT
                     AVG(home_goals) AS avg_home,
                     AVG(away_goals) AS avg_away,
                     AVG(home_goals + away_goals) AS avg_total
                   FROM matches WHERE status=?""",
                (FINISHED_STATUS,)
            ).fetchone()
        return {
            "home":  row["avg_home"] or 1.4,
            "away":  row["avg_away"] or 1.1,
            "total": row["avg_total"] or 2.5,
        }
    finally:
        conn.close()


def _get_team_strength(team_id: int, league: Dict[str, float],
                       cutoff_date: str | None = None) -> TeamStrength:
    """
    读某队的加权攻防强度，除以联赛均值归一化。
    有 cutoff_date 时动态从 matches 表算（只看截止日前）；
    没 cutoff_date 时直接读 teams 表（全量最新值）。
    """
    conn = get_conn()
    try:
        if cutoff_date:
            # === 动态查询：截止日前的主场/客场表现 ===
            home_rows = conn.execute(
                """SELECT home_goals AS gf, away_goals AS ga
                   FROM matches
                   WHERE home_team_id = ? AND status = ? AND match_date < ?
                   ORDER BY match_date DESC LIMIT 10""",
                (team_id, FINISHED_STATUS, cutoff_date)
            ).fetchall()
            away_rows = conn.execute(
                """SELECT away_goals AS gf, home_goals AS ga
                   FROM matches
                   WHERE away_team_id = ? AND status = ? AND match_date < ?
                   ORDER BY match_date DESC LIMIT 10""",
                (team_id, FINISHED_STATUS, cutoff_date)
            ).fetchall()

            def wavg(rows):
                if not rows: return (1.2, 1.2)
                ws = wg = wga = 0.0
                for i, r in enumerate(rows):
                    w = 0.85 ** i
                    wg += r["gf"] * w; wga += r["ga"] * w; ws += w
                return (wg/ws, wga/ws)

            avg_hg, avg_hc = wavg(home_rows)
            avg_ag, avg_ac = wavg(away_rows)
            name_row = conn.execute("SELECT name FROM teams WHERE team_id=?", (team_id,)).fetchone()
            name = name_row["name"] if name_row else f"Team-{team_id}"
        else:
            row = conn.execute("SELECT * FROM teams WHERE team_id=?", (team_id,)).fetchone()
            if row is None:
                return TeamStrength(team_id, f"Team-{team_id}", 1.0, 1.0, 1.0, 1.0)
            avg_hg, avg_hc = row["avg_home_goals"], row["avg_home_conceded"]
            avg_ag, avg_ac = row["avg_away_goals"], row["avg_away_conceded"]
            name = row["name"]
    finally:
        conn.close()

    home_att = max(avg_hg, 0.1) / max(league["home"], 0.1)
    home_def = max(avg_hc, 0.1) / max(league["away"], 0.1)
    away_att = max(avg_ag, 0.1) / max(league["away"], 0.1)
    away_def = max(avg_ac, 0.1) / max(league["home"], 0.1)

    return TeamStrength(
        team_id=team_id, name=name,
        home_att=home_att, home_def=home_def,
        away_att=away_att, away_def=away_def,
    )


# ============================================================
# 单场预测
# ============================================================
def predict_match(match_id: int, cutoff_date: str | None = None) -> PredictionResult:
    """对指定比赛跑泊松预测。cutoff_date 用于滚动回测（只用该日期前的数据）。"""
    conn = get_conn()
    try:
        m = conn.execute(
            "SELECT * FROM matches WHERE match_id=?", (match_id,)
        ).fetchone()
    finally:
        conn.close()

    if m is None:
        raise ValueError(f"match_id={match_id} 不在 DB 里")

    league = _get_league_avg(cutoff_date)
    home = _get_team_strength(m["home_team_id"], league, cutoff_date)
    away = _get_team_strength(m["away_team_id"], league, cutoff_date)

    # === 核心公式 ===
    # 主队预期进球 = 主队主场进攻 × 客队客场防守 × 联赛均值 × 主场加成
    lam_h = home.home_att * away.away_def * league["home"] * HOME_ADVANTAGE
    # 客队预期进球 = 客队客场进攻 × 主队主场防守 × 联赛均值
    lam_a = away.away_att * home.home_def * league["away"]

    # === 方案 A：关键球员惩罚（cutoff 也传给 adjust_lambda）===
    pen_h = adjust_lambda(lam_h, m["home_team_id"], is_home=True, cutoff_date=cutoff_date)
    pen_a = adjust_lambda(lam_a, m["away_team_id"], is_home=False, cutoff_date=cutoff_date)
    lam_h *= pen_h.penalty_factor
    lam_a *= pen_a.penalty_factor

    # === 遍历所有比分组合 + Dixon-Coles 低比分修正 ===
    score_probs: Dict[str, float] = {}
    home_win = draw = away_win = 0.0
    # Dixon-Coles (1997) 修正：针对独立泊松假设下"低比分概率偏低"的问题
    # 只对 0-0 / 0-1 / 1-0 / 1-1 四种组合分别加权
    # ρ 是进球相关性系数（英超典型 0.05~0.20，0 就是独立泊松）
    # 公式（来自 Dixon-Coles 1997 原始论文）：
    #   τ(0,0) = 1 - ρ * λ_h * λ_a
    #   τ(0,1) = 1 + ρ * λ_h
    #   τ(1,0) = 1 + ρ * λ_a
    #   τ(1,1) = 1 - ρ
    #   其它情况 τ = 1
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            p = poisson_pmf(h, lam_h) * poisson_pmf(a, lam_a)
            # Dixon-Coles 修正
            if h == 0 and a == 0:
                p *= (1 - DC_RHO * lam_h * lam_a)
            elif h == 0 and a == 1:
                p *= (1 + DC_RHO * lam_h)
            elif h == 1 and a == 0:
                p *= (1 + DC_RHO * lam_a)
            elif h == 1 and a == 1:
                p *= (1 - DC_RHO)
            # 其它 h,a 保持原概率
            key = f"{h}-{a}"
            score_probs[key] = score_probs.get(key, 0.0) + p

            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p

    # 归一化（浮点误差校正）
    total = home_win + draw + away_win
    home_win /= total
    draw /= total
    away_win /= total

    # Top 5 比分
    top = sorted(score_probs.items(), key=lambda x: -x[1])[:5]
    top_scores = [{"score": s, "prob": round(p, 4)} for s, p in top]

    return PredictionResult(
        match_id=match_id,
        home_name=m["home_name"],
        away_name=m["away_name"],
        lambda_home=round(lam_h, 3),
        lambda_away=round(lam_a, 3),
        home_win_prob=round(home_win, 4),
        draw_prob=round(draw, 4),
        away_win_prob=round(away_win, 4),
        top_scores=top_scores,
        league_avg_goals=round(league["total"], 2),
        penalty_home=pen_h,
        penalty_away=pen_a,
    )


# ============================================================
# 打印漂亮的预测面板
# ============================================================
def print_prediction(r: PredictionResult) -> None:
    print("\n" + "=" * 56)
    print(f"  预测：{r.home_name}  VS  {r.away_name}")
    print("=" * 56)
    print(f"  联赛场均进球：{r.league_avg_goals}")
    print(f"  预期进球 λ_home={r.lambda_home}   λ_away={r.lambda_away}")
    # 方案 A：阵容调整提示
    if r.penalty_home and r.penalty_home.star_absent_count > 0:
        print(f"  ⚠ {r.home_name} 阵容惩罚 ×{r.penalty_home.penalty_factor}  "
              f"(推断缺 {r.penalty_home.star_absent_count} 名核心)")
    if r.penalty_away and r.penalty_away.star_absent_count > 0:
        print(f"  ⚠ {r.away_name} 阵容惩罚 ×{r.penalty_away.penalty_factor}  "
              f"(推断缺 {r.penalty_away.star_absent_count} 名核心)")
    print("-" * 56)
    # 胜平负条形
    hw, dw, aw = r.home_win_prob, r.draw_prob, r.away_win_prob
    bar_w = 30
    def bar(p):
        return "█" * int(p * bar_w) + "░" * (bar_w - int(p * bar_w))

    print(f"  主胜  {bar(hw)} {hw*100:5.1f}%")
    print(f"  平局  {bar(dw)} {dw*100:5.1f}%")
    print(f"  客胜  {bar(aw)} {aw*100:5.1f}%")
    print("-" * 56)
    print("  Top 5 比分：")
    for s in r.top_scores:
        print(f"    {s['score']:>4s}  概率 {s['prob']*100:5.1f}%  "
              f"{'█' * int(s['prob']*40)}")
    print("=" * 56)
    print("  ⚠ 本工具仅基于历史数据做统计概率推演，")
    print("    不构成任何投注建议，足球存在大量偶然性")
    print("=" * 56 + "\n")


if __name__ == "__main__":
    # 临时跑：预测 DB 里第一场未赛比赛
    from db import init_db
    from fetcher import fetch_data
    init_db()
    fetch_data()

    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT match_id FROM matches WHERE status='SCHEDULED' LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    if row:
        r = predict_match(row["match_id"])
        print_prediction(r)
    else:
        print("[Poisson] 没有待预测比赛")
