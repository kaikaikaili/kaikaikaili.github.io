"""FastAPI 后端 —— 英超/多联赛预测 MVP WebApp
路由：
  GET  /api/leagues        可用联赛列表
  GET  /api/matches        赛程列表 (?league=&status=&page=&limit=)
  GET  /api/matches/{id}   单场详情 + 预测
  GET  /api/backtest       穿越式回测统计
  GET  /api/health         健康检查
"""
from __future__ import annotations

import json
import sys
sys.path.insert(0, ".")

import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import poisson as poisson_mod
from squad import SquadAdjustment

# =================== 初始化 ===================
app = FastAPI(
    title="足球概率预测工具",
    description="基于加权泊松分布的足球比赛概率推演（12 联赛，1.1 万场回测）",
    version="0.1.0",
)

# CORS（开发期全开放）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "epl.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# =================== Helpers ===================
LEAGUE_NAMES = {
    "PL": "英超", "ELC": "英冠", "PD": "西甲", "SA": "意甲",
    "BL1": "德甲", "FL1": "法甲", "DED": "荷甲", "PPL": "葡超",
    "BSA": "巴甲", "CL": "欧冠", "CLI": "解放者杯", "WC": "世界杯",
}

STATUS_UPCOMING = ("TIMED", "SCHEDULED")
STATUS_FINISHED = ("FINISHED", "AWARDED")


def squad_to_dict(sa: SquadAdjustment | None) -> dict | None:
    if sa is None: return None
    return {
        "penalty_factor": sa.penalty_factor,
        "star_absent_count": sa.star_absent_count,
        "reason": getattr(sa, "reason", ""),
    }


# =================== 路由 ===================
@app.get("/api/health")
def health():
    return {"ok": True, "home_adv": config.HOME_ADVANTAGE}


@app.get("/api/leagues")
def list_leagues():
    """可用联赛列表 + 各联赛比赛数"""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT league, COUNT(*) AS total,
                      SUM(CASE WHEN status IN ('FINISHED','AWARDED') THEN 1 ELSE 0 END) AS finished,
                      SUM(CASE WHEN status IN ('TIMED','SCHEDULED') THEN 1 ELSE 0 END) AS upcoming
               FROM matches GROUP BY league ORDER BY league"""
        ).fetchall()
    return [
        {
            "code": r["league"],
            "name": LEAGUE_NAMES.get(r["league"], r["league"]),
            "total": r["total"],
            "finished": r["finished"],
            "upcoming": r["upcoming"],
        }
        for r in rows
    ]


@app.get("/api/matches")
def list_matches(
    league: Optional[str] = Query(None, description="联赛代码，如 PL/PD/SA"),
    status: Optional[str] = Query(None, description="upcoming/finished/all"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    """赛程列表"""
    clauses: List[str] = []
    params: List[Any] = []

    if league:
        clauses.append("league = ?")
        params.append(league)
    if status == "upcoming":
        clauses.append("status IN ('TIMED','SCHEDULED')")
    elif status == "finished":
        clauses.append("status IN ('FINISHED','AWARDED')")
    if date_from:
        clauses.append("match_date >= ?")
        params.append(date_from + "T00:00:00Z")
    if date_to:
        clauses.append("match_date <= ?")
        params.append(date_to + "T23:59:59Z")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM matches {where}", params
        ).fetchone()["c"]

        rows = conn.execute(
            f"""SELECT match_id, league, home_name, away_name, match_date, status,
                       home_goals, away_goals
                FROM matches {where}
                ORDER BY match_date ASC
                LIMIT ? OFFSET ?""",
            params + [limit, (page - 1) * limit]
        ).fetchall()

    items = []
    for r in rows:
        items.append({
            "match_id": r["match_id"],
            "league": r["league"],
            "league_name": LEAGUE_NAMES.get(r["league"], r["league"]),
            "home_name": r["home_name"],
            "away_name": r["away_name"],
            "match_date": r["match_date"],
            "status": r["status"],
            "home_goals": r["home_goals"],
            "away_goals": r["away_goals"],
        })
    return {"total": total, "page": page, "limit": limit, "items": items}


@app.get("/api/matches/{match_id}")
def get_match(match_id: int):
    """单场详情 + 泊松预测 + 对阵双方近期战绩"""
    with get_db() as conn:
        m = conn.execute(
            "SELECT * FROM matches WHERE match_id=?", (match_id,)
        ).fetchone()
        if m is None:
            raise HTTPException(status_code=404, detail="比赛不存在")

        # 双方近期 5 场（带主客场标识，前端才能正确判断胜负）
        home_recent = conn.execute(
            """SELECT m.home_team_id, m.away_team_id, m.home_name, m.away_name,
                      m.home_goals, m.away_goals, m.match_date
               FROM matches m
               WHERE (m.home_team_id=? OR m.away_team_id=?) AND m.status IN ('FINISHED','AWARDED')
               ORDER BY m.match_date DESC LIMIT 5""",
            (m["home_team_id"], m["home_team_id"])
        ).fetchall()
        away_recent = conn.execute(
            """SELECT m.home_team_id, m.away_team_id, m.home_name, m.away_name,
                      m.home_goals, m.away_goals, m.match_date
               FROM matches m
               WHERE (m.home_team_id=? OR m.away_team_id=?) AND m.status IN ('FINISHED','AWARDED')
               ORDER BY m.match_date DESC LIMIT 5""",
            (m["away_team_id"], m["away_team_id"])
        ).fetchall()

    # 预测
    try:
        pred = poisson_mod.predict_match(match_id)
        pred_dict = {
            "lambda_home": pred.lambda_home,
            "lambda_away": pred.lambda_away,
            "home_win_prob": pred.home_win_prob,
            "draw_prob": pred.draw_prob,
            "away_win_prob": pred.away_win_prob,
            "top_scores": pred.top_scores,
            "league_avg_goals": pred.league_avg_goals,
            "penalty_home": squad_to_dict(pred.penalty_home),
            "penalty_away": squad_to_dict(pred.penalty_away),
        }
    except Exception as e:
        pred_dict = {"error": str(e)}

    def fmt_recent(rows, team_id):
        out = []
        for r in rows:
            is_home = team_id == r["home_team_id"]
            out.append({
                "date": r["match_date"],
                "home": r["home_name"],
                "away": r["away_name"],
                "home_goals": r["home_goals"],
                "away_goals": r["away_goals"],
                "is_home": is_home,
                "team_id": team_id,
            })
        return out

    return {
        "match": {
            "match_id": m["match_id"],
            "league": m["league"],
            "league_name": LEAGUE_NAMES.get(m["league"], m["league"]),
            "home_name": m["home_name"],
            "away_name": m["away_name"],
            "home_team_id": m["home_team_id"],
            "away_team_id": m["away_team_id"],
            "match_date": m["match_date"],
            "status": m["status"],
            "home_goals": m["home_goals"],
            "away_goals": m["away_goals"],
        },
        "prediction": pred_dict,
        "home_recent": fmt_recent(home_recent, m["home_team_id"]),
        "away_recent": fmt_recent(away_recent, m["away_team_id"]),
        "disclaimer": "本工具仅基于历史数据做统计概率推演，不构成任何投注建议，足球存在大量偶然性",
    }


@app.get("/api/backtest")
def backtest(league: Optional[str] = Query(None)):
    """穿越式回测统计（1.1 万场内存版，约 10 秒跑完）"""
    import math
    from collections import defaultdict

    # 复用内存版回测逻辑
    with get_db() as conn:
        sql = "SELECT * FROM matches WHERE home_goals IS NOT NULL ORDER BY league, match_date ASC"
        if league:
            sql = f"SELECT * FROM matches WHERE home_goals IS NOT NULL AND league='{league}' ORDER BY match_date ASC"
        rows = conn.execute(sql).fetchall()

    leagues = defaultdict(list)
    for r in rows:
        leagues[r["league"]].append(r)

    HOME_ADV = config.HOME_ADVANTAGE
    MAX_GOALS = config.MAX_GOALS
    DECAY = config.RECENT_DECAY

    def pmf(k, lam):
        if lam <= 0: return 1.0 if k == 0 else 0.0
        return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))

    def league_avg(lm, idx):
        if idx < 5: return {"home": 1.4, "away": 1.1}
        hg = sum(lm[i]["home_goals"] for i in range(idx))
        ag = sum(lm[i]["away_goals"] for i in range(idx))
        return {"home": hg/idx, "away": ag/idx}

    def strength(tid, lm, idx, la):
        hgf = []; agf = []; hga = []; aga = []
        for i in range(idx):
            m = lm[i]
            if m["home_team_id"] == tid:
                hgf.append(m["home_goals"]); hga.append(m["away_goals"])
            if m["away_team_id"] == tid:
                agf.append(m["away_goals"]); aga.append(m["home_goals"])
        def wavg(arr):
            if not arr: return 1.2
            ws = wsum = 0.0
            for i, v in enumerate(arr[:10]):
                w = DECAY ** i; wsum += v * w; ws += w
            return wsum / ws if ws > 0 else 1.2
        hg, hc = wavg(hgf), wavg(hga)
        ag, ac = wavg(agf), wavg(aga)
        return {
            "home_att": max(hg, 0.1) / max(la["home"], 0.1),
            "home_def": max(hc, 0.1) / max(la["away"], 0.1),
            "away_att": max(ag, 0.1) / max(la["away"], 0.1),
            "away_def": max(ac, 0.1) / max(la["home"], 0.1),
        }

    result = []
    for lg in sorted(leagues.keys()):
        lm = leagues[lg]
        n = len(lm)
        hit = brier_sum = 0
        n_draw = hit_draw = 0

        for i in range(5, n):
            m = lm[i]
            hg, ag = m["home_goals"], m["away_goals"]
            actual = 0 if hg > ag else (1 if hg == ag else 2)
            la = league_avg(lm, i)
            s_h = strength(m["home_team_id"], lm, i, la)
            s_a = strength(m["away_team_id"], lm, i, la)
            lam_h = s_h["home_att"] * s_a["away_def"] * la["home"] * HOME_ADV
            lam_a = s_a["away_att"] * s_h["home_def"] * la["away"]
            hw = dw = aw = 0.0
            for h in range(MAX_GOALS + 1):
                for a in range(MAX_GOALS + 1):
                    p = pmf(h, lam_h) * pmf(a, lam_a)
                    if h > a: hw += p
                    elif h == a: dw += p
                    else: aw += p
            total = hw + dw + aw
            probs = [hw/total, dw/total, aw/total]
            pred_cat = probs.index(max(probs))
            one_hot = [0.0, 0.0, 0.0]; one_hot[actual] = 1.0
            brier = sum((p - o) ** 2 for p, o in zip(probs, one_hot))
            hit += int(pred_cat == actual)
            brier_sum += brier
            if actual == 1:
                n_draw += 1; hit_draw += int(pred_cat == 1)

        eff = n - 5
        result.append({
            "league": lg,
            "league_name": LEAGUE_NAMES.get(lg, lg),
            "matches": eff,
            "hit_rate": round(hit / eff * 100, 1),
            "brier": round(brier_sum / eff, 4),
            "draw_hit_rate": round(hit_draw / n_draw * 100, 1) if n_draw > 0 else 0,
            "draw_hit": hit_draw,
            "draw_total": n_draw,
        })

    return {
        "home_advantage": HOME_ADV,
        "total_matches": sum(r["matches"] for r in result),
        "leagues": result,
        "disclaimer": "Brier Score 范围 [0,2]，0=完美。英超优秀模型参考 Brier 0.55-0.65",
    }


# =================== 静态文件（前端 build） ===================
import os
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    print("启动 FastAPI 后端... http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
