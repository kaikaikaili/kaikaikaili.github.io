"""数据拉取 + 球队攻防强度计算
- 有 FOOTBALL_DATA_API_KEY → 调官方 API
- 没有 → 用内置 mock 英超赛程/赛果，保证任何环境都能跑通 demo
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
import sys
from typing import List, Dict, Any

import requests

from config import (
    FOOTBALL_DATA_API_KEY, FOOTBALL_DATA_BASE, LEAGUE_CODE,
    RECENT_WINDOW, RECENT_DECAY, FINISHED_STATUS
)
from db import get_conn


# ============================================================
# 真实 API 拉取
# ============================================================
def _api_get(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """带 Key 的 GET 请求"""
    url = f"{FOOTBALL_DATA_BASE}{path}"
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_from_api(seasons: List[int] | None = None) -> None:
    """
    拉取英超多赛季比赛（含赛程+已结束）并写入 DB。
    默认拉 2023-2026 四个赛季（免费 Key 够用）。
    """
    if seasons is None:
        seasons = [2023, 2024, 2025, 2026]   # 免费 Key 可用范围

    print(f"[Fetcher] 正在从 football-data.org 拉取英超数据...")
    print(f"[Fetcher] 赛季：{seasons}")

    _wipe_all()
    total = 0
    for s in seasons:
        try:
            data = _api_get(f"/competitions/{LEAGUE_CODE}/matches", params={"season": s})
            matches = data.get("matches", [])
            _upsert_matches(matches)
            total += len(matches)
            # 避免触发限流（免费版 10次/分钟）
            import time; time.sleep(0.2)
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                print(f"[Fetcher]  season={s} 403 无权限，跳过")
            else:
                raise

    _recalc_team_strengths()
    print(f"[Fetcher] 已同步 {total} 场比赛（{len(seasons)} 个赛季）")


def _wipe_all() -> None:
    """清空 matches/teams —— predict_records 保留（match_id 是全局唯一的）"""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM matches")
        conn.execute("DELETE FROM teams")
        conn.commit()
    finally:
        conn.close()


def _upsert_matches(api_matches: List[Dict]) -> None:
    conn = get_conn()
    try:
        for m in api_matches:
            match_id = m["id"]
            home = m["homeTeam"]
            away = m["awayTeam"]
            score = m.get("score", {})
            full = score.get("fullTime") or {}
            status = m.get("status", "")

            # 球队：用 INSERT OR REPLACE，覆盖更新球队信息（防止旧 mock 残留）
            for t in (home, away):
                conn.execute(
                    """INSERT OR REPLACE INTO teams (team_id, name, short_name)
                       VALUES (?, ?, ?)""",
                    (t["id"], t["name"], t.get("shortName") or t["name"][:3].upper())
                )

            # 比赛
            conn.execute(
                """INSERT OR REPLACE INTO matches
                   (match_id, league, home_team_id, away_team_id,
                    home_name, away_name, match_date, status,
                    home_goals, away_goals)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (match_id, LEAGUE_CODE,
                 home["id"], away["id"],
                 home["name"], away["name"],
                 m["utcDate"], status,
                 full.get("home"), full.get("away"))
            )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# Mock 数据（没 Key 时自动启用）
# ============================================================
# 2024-25 赛季英超部分球队 + 若干历史赛果 + 未来赛程
_MOCK_TEAMS = [
    (101, "Manchester City",   "MCI"),
    (102, "Arsenal",           "ARS"),
    (103, "Liverpool",         "LIV"),
    (104, "Manchester United", "MUN"),
    (105, "Chelsea",           "CHE"),
    (106, "Tottenham",         "TOT"),
    (107, "Newcastle",         "NEW"),
    (108, "Aston Villa",       "AVL"),
    (109, "Brighton",          "BHA"),
    (110, "West Ham",          "WHU"),
]

# 历史赛果（已结束，用来算强度）
# 字段：match_id, 主队ID, 客队ID, 主队进球, 客队进球, days_ago, 状态
_MOCK_RESULTS = [
    (1,  101, 102, 2, 1,  2, "FINISHED"),
    (2,  103, 104, 3, 0,  3, "FINISHED"),
    (3,  105, 106, 1, 1,  4, "FINISHED"),
    (4,  107, 108, 2, 2,  5, "FINISHED"),
    (5,  101, 103, 1, 1,  7, "FINISHED"),
    (6,  104, 101, 0, 2,  8, "FINISHED"),
    (7,  102, 105, 3, 1,  9, "FINISHED"),
    (8,  106, 107, 0, 1, 10, "FINISHED"),
    (9,  108, 101, 1, 3, 11, "FINISHED"),
    (10, 103, 102, 2, 2, 12, "FINISHED"),
    (11, 109, 110, 2, 0, 13, "FINISHED"),
    (12, 101, 106, 4, 0, 14, "FINISHED"),
    (13, 104, 103, 1, 2, 15, "FINISHED"),
    (14, 105, 102, 0, 2, 16, "FINISHED"),
    (15, 107, 101, 1, 1, 17, "FINISHED"),
    (16, 108, 104, 2, 1, 18, "FINISHED"),
    (17, 110, 105, 0, 0, 19, "FINISHED"),
    (18, 102, 107, 2, 0, 20, "FINISHED"),
]

# 未来赛程（3 场预测目标）
_MOCK_FIXTURES = [
    (2001, 101, 103,  1, "SCHEDULED"),   # City vs Liverpool 明天
    (2002, 102, 104,  2, "SCHEDULED"),   # Arsenal vs Utd 后天
    (2003, 105, 107,  3, "SCHEDULED"),   # Chelsea vs Newcastle 大后天
]


def _team_name(tid: int) -> str:
    for t in _MOCK_TEAMS:
        if t[0] == tid:
            return t[1]
    return f"Team-{tid}"


def load_mock_data() -> None:
    """写入 mock 数据，保证无 Key 环境也能跑"""
    print("[Fetcher] 无 API Key，加载内置 mock 英超数据...")
    now = dt.datetime.now(dt.timezone.utc)
    conn = get_conn()
    try:
        # 清空重灌，避免重复
        conn.execute("DELETE FROM matches")
        conn.execute("DELETE FROM teams")

        # 球队
        for tid, name, short in _MOCK_TEAMS:
            conn.execute(
                "INSERT INTO teams (team_id, name, short_name) VALUES (?,?,?)",
                (tid, name, short)
            )

        # 历史赛果
        for mid, h, a, hg, ag, days_ago, status in _MOCK_RESULTS:
            date = (now - dt.timedelta(days=days_ago)).isoformat()
            conn.execute(
                """INSERT OR REPLACE INTO matches
                   (match_id, league, home_team_id, away_team_id,
                    home_name, away_name, match_date, status,
                    home_goals, away_goals)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (mid, LEAGUE_CODE, h, a,
                 _team_name(h), _team_name(a),
                 date, status, hg, ag)
            )

        # 未来赛程
        for mid, h, a, days_ahead, status in _MOCK_FIXTURES:
            date = (now + dt.timedelta(days=days_ahead)).isoformat()
            conn.execute(
                """INSERT OR REPLACE INTO matches
                   (match_id, league, home_team_id, away_team_id,
                    home_name, away_name, match_date, status,
                    home_goals, away_goals)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (mid, LEAGUE_CODE, h, a,
                 _team_name(h), _team_name(a),
                 date, status, None, None)
            )

        conn.commit()
    finally:
        conn.close()

    _recalc_team_strengths()
    print(f"[Fetcher] mock 数据已加载：{len(_MOCK_TEAMS)} 队, "
          f"{len(_MOCK_RESULTS)} 场历史, {len(_MOCK_FIXTURES)} 场未来")


# ============================================================
# 统一入口
# ============================================================
def fetch_data() -> None:
    """优先真实 API，无 Key 则走 mock"""
    if FOOTBALL_DATA_API_KEY:
        try:
            fetch_from_api()
            return
        except Exception as e:
            print(f"[Fetcher] API 拉取失败({e})，fallback 到 mock 数据")
    load_mock_data()


# ============================================================
# 球队攻防强度计算（加权近 N 场，主客场分开算）
# ============================================================
def _recalc_team_strengths() -> None:
    conn = get_conn()
    try:
        teams = conn.execute("SELECT team_id FROM teams").fetchall()
        for t in teams:
            tid = t["team_id"]

            # 主场表现：作为主队的已结束比赛（近 RECENT_WINDOW 场）
            home_rows = conn.execute(
                """SELECT home_goals AS gf, away_goals AS ga
                   FROM matches
                   WHERE home_team_id = ? AND status = ?
                   ORDER BY match_date DESC LIMIT ?""",
                (tid, FINISHED_STATUS, RECENT_WINDOW)
            ).fetchall()

            # 客场表现：作为客队
            away_rows = conn.execute(
                """SELECT away_goals AS gf, home_goals AS ga
                   FROM matches
                   WHERE away_team_id = ? AND status = ?
                   ORDER BY match_date DESC LIMIT ?""",
                (tid, FINISHED_STATUS, RECENT_WINDOW)
            ).fetchall()

            avg_hg, avg_hc = _weighted_avg(home_rows)   # 主场进/失
            avg_ag, avg_ac = _weighted_avg(away_rows)   # 客场进/失

            conn.execute(
                """UPDATE teams
                   SET avg_home_goals=?, avg_home_conceded=?,
                       avg_away_goals=?, avg_away_conceded=?,
                       updated_at=CURRENT_TIMESTAMP
                   WHERE team_id=?""",
                (avg_hg, avg_hc, avg_ag, avg_ac, tid)
            )
        conn.commit()
    finally:
        conn.close()


def _weighted_avg(rows: List[sqlite3.Row]) -> tuple:
    """近期衰减加权平均：场次数越多、越近权重越高"""
    if not rows:
        return (1.2, 1.2)   # 新队给个联赛均值默认值，避免除零

    w_sum = 0.0
    gf_sum = 0.0
    ga_sum = 0.0
    # rows 已按日期倒序，越靠前越近
    for i, r in enumerate(rows):
        w = RECENT_DECAY ** i     # 第 0 场 weight=1，后面依次衰减
        gf_sum += r["gf"] * w
        ga_sum += r["ga"] * w
        w_sum += w

    return (gf_sum / w_sum, ga_sum / w_sum)


if __name__ == "__main__":
    fetch_data()
