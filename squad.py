"""方案 A：关键球员惩罚系数 + 隐式伤病推断
MVP 阶段没有真实阵容/伤停数据源，所以用"近期进攻突然下滑"作为
"有核心球员缺阵"的信号，自动给 λ 打折。

以后接 API-Football 的 lineup/injuries 接口后，把 detect_injury_risk()
换成真实伤停查询就行，adjust_lambda() 接口不变。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config import (
    STAR_PLAYER_PENALTY, MAX_STAR_ABSENT,
    INJURY_DROP_THRESHOLD, INJURY_CHECK_WINDOW, FINISHED_STATUS
)
from db import get_conn


@dataclass
class SquadAdjustment:
    """某队在某场比赛中的阵容调整"""
    star_absent_count: int          # 缺阵关键球员数（推断的）
    penalty_factor: float           # 最终乘到 λ 上的系数
    reason: str                     # 为什么调整（给前端展示用）


def detect_injury_risk(team_id: int, is_home: bool,
                       cutoff_date: str | None = None) -> int:
    """
    隐式伤病推断：
    如果某队最近 3 场主场/客场进球均值比长期均值低 55%，
    认为有核心进攻球员缺阵，返回"推断缺阵人数"（1~3）。
    正常返回 0。
    """
    conn = get_conn()
    try:
        goal_col = "home_goals" if is_home else "away_goals"
        where_col = "home_team_id" if is_home else "away_team_id"
        date_filter = "AND match_date < ?" if cutoff_date else ""
        params = [team_id, FINISHED_STATUS]
        if cutoff_date:
            params.append(cutoff_date)

        # 长期均值（近 10 场）
        long_term = conn.execute(
            f"""SELECT AVG({goal_col}) AS avg_gf FROM (
                    SELECT {goal_col} FROM matches
                    WHERE {where_col} = ? AND status = ? {date_filter}
                    ORDER BY match_date DESC LIMIT 10
                )""",
            params
        ).fetchone()

        # 最近 INJURY_CHECK_WINDOW 场均值
        recent = conn.execute(
            f"""SELECT AVG({goal_col}) AS avg_gf FROM (
                    SELECT {goal_col} FROM matches
                    WHERE {where_col} = ? AND status = ? {date_filter}
                    ORDER BY match_date DESC LIMIT {INJURY_CHECK_WINDOW}
                )""",
            params
        ).fetchone()
    finally:
        conn.close()

    long_avg = long_term["avg_gf"] if long_term and long_term["avg_gf"] else 1.2
    recent_avg = recent["avg_gf"] if recent and recent["avg_gf"] else 1.2

    if long_avg < 0.3:
        return 0

    ratio = recent_avg / long_avg

    if ratio < INJURY_DROP_THRESHOLD:
        if ratio < INJURY_DROP_THRESHOLD * 0.6:
            return 3
        elif ratio < INJURY_DROP_THRESHOLD * 0.8:
            return 2
        else:
            return 1
    return 0


def adjust_lambda(
    lam: float,
    team_id: int,
    is_home: bool,
    explicit_absent: Optional[int] = None,
    cutoff_date: str | None = None,
) -> SquadAdjustment:
    """
    对某队的进攻 λ 应用阵容惩罚。
    cutoff_date 用于滚动回测（只用该日期前的数据做伤病推断）。
    """
    if explicit_absent is not None:
        absent = min(explicit_absent, MAX_STAR_ABSENT)
        reason = f"明确缺阵 {absent} 名关键球员（外部数据）"
    else:
        absent = detect_injury_risk(team_id, is_home, cutoff_date)
        if absent == 0:
            return SquadAdjustment(0, 1.0, "阵容完整或无明显下滑")
        reason = f"近 {INJURY_CHECK_WINDOW} 场进攻均值大幅下滑，推断 {absent} 名核心缺阵"

    absent = min(absent, MAX_STAR_ABSENT)
    factor = STAR_PLAYER_PENALTY ** absent
    factor = max(factor, 0.5)

    return SquadAdjustment(absent, round(factor, 4), reason)


if __name__ == "__main__":
    from db import init_db
    from fetcher import fetch_data
    init_db()
    fetch_data()

    conn = get_conn()
    teams = conn.execute("SELECT team_id, name FROM teams LIMIT 5").fetchall()
    conn.close()

    print("=== 隐式伤病推断测试（前 5 队）===")
    for t in teams:
        for home in [True, False]:
            adj = adjust_lambda(1.5, t["team_id"], is_home=home)
            label = "主场" if home else "客场"
            marker = "⚠ " if adj.star_absent_count > 0 else "  "
            print(f"  {marker}{t['name']:25s} {label}: "
                  f"缺阵≈{adj.star_absent_count}  惩罚×{adj.penalty_factor}  "
                  f"→ {adj.reason[:40]}")
