"""
把 SQLite DB + 泊松预测 导出为静态 JSON 文件，供 GitHub Pages 纯前端使用。
输出目录 frontend/public/data/，Vite build 时自动带进 dist。
"""
from __future__ import annotations
import json, math, os, sys, sqlite3
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

import config
import poisson as poisson_mod
from squad import SquadAdjustment

DB_PATH = os.path.join(os.path.dirname(__file__), "epl.db")
OUT_DIR = os.path.join(os.path.dirname(__file__), "frontend", "public", "data")
os.makedirs(OUT_DIR, exist_ok=True)

LEAGUE_NAMES = {
    "PL": "英超", "ELC": "英冠", "PD": "西甲", "SA": "意甲",
    "BL1": "德甲", "FL1": "法甲", "DED": "荷甲", "PPL": "葡超",
    "BSA": "巴甲", "CL": "欧冠", "CLI": "解放者杯", "WC": "世界杯",
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============ 1. leagues.json ============
def export_leagues():
    with get_db() as conn:
        rows = conn.execute(
            """SELECT league, COUNT(*) AS total,
                      SUM(CASE WHEN status IN ('FINISHED','AWARDED') THEN 1 ELSE 0 END) AS finished,
                      SUM(CASE WHEN status IN ('TIMED','SCHEDULED') THEN 1 ELSE 0 END) AS upcoming
               FROM matches GROUP BY league ORDER BY league"""
        ).fetchall()
    data = [
        {"code": r["league"], "name": LEAGUE_NAMES.get(r["league"], r["league"]),
         "total": r["total"], "finished": r["finished"], "upcoming": r["upcoming"]}
        for r in rows
    ]
    _save("leagues.json", data)
    print(f"  ✅ leagues.json ({len(data)} leagues)")

# ============ 2. matches.json (all, with pagination baked into keys) ============
def export_matches():
    with get_db() as conn:
        rows = conn.execute(
            """SELECT match_id, league, home_team_id, away_team_id,
                      home_name, away_name, match_date, status,
                      home_goals, away_goals
               FROM matches ORDER BY match_date ASC"""
        ).fetchall()
    all_matches = [dict(r) for r in rows]

    # 按联赛分组
    by_league = {}
    for m in all_matches:
        lg = m["league"]
        m["league_name"] = LEAGUE_NAMES.get(lg, lg)
        by_league.setdefault(lg, []).append(m)

    _save("matches_all.json", all_matches)
    _save("matches_by_league.json", by_league)
    print(f"  ✅ matches_all.json ({len(all_matches)} matches)")
    print(f"  ✅ matches_by_league.json ({len(by_league)} leagues)")

# ============ 3. predictions.json (所有未赛比赛的预测) ============
def export_predictions():
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM matches WHERE status IN ('TIMED','SCHEDULED')
               ORDER BY match_date ASC"""
        ).fetchall()

    predictions = {}
    for m in rows:
        try:
            pred = poisson_mod.predict_match(m["match_id"])
            pred_dict = {
                "match_id": m["match_id"],
                "league": m["league"],
                "league_name": LEAGUE_NAMES.get(m["league"], m["league"]),
                "home_name": m["home_name"],
                "away_name": m["away_name"],
                "match_date": m["match_date"],
                "lambda_home": pred.lambda_home,
                "lambda_away": pred.lambda_away,
                "home_win_prob": pred.home_win_prob,
                "draw_prob": pred.draw_prob,
                "away_win_prob": pred.away_win_prob,
                "top_scores": pred.top_scores,
                "league_avg_goals": pred.league_avg_goals,
                "penalty_home": _squad_dict(pred.penalty_home),
                "penalty_away": _squad_dict(pred.penalty_away),
            }
            predictions[m["match_id"]] = pred_dict
        except Exception as e:
            print(f"    ⚠ match {m['match_id']} 预测失败: {e}")

    _save("predictions.json", predictions)
    print(f"  ✅ predictions.json ({len(predictions)} upcoming matches)")

def _squad_dict(sa):
    if sa is None: return None
    return {"penalty_factor": sa.penalty_factor,
            "star_absent_count": sa.star_absent_count,
            "reason": getattr(sa, "reason", "")}

# ============ 4. match_detail.json (单场详情 + 近期战绩 + 预测) ============
def export_match_details():
    """每场比赛的完整详情：预测 + 双方近期 5 场"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM matches ORDER BY match_date ASC"
        ).fetchall()

    details = {}
    for m in rows:
        mid = m["match_id"]
        # 近期战绩（带主客场标识）
        def recent(tid):
            rs = conn.execute(
                """SELECT home_team_id, away_team_id, home_name, away_name,
                          home_goals, away_goals, match_date
                   FROM matches
                   WHERE (home_team_id=? OR away_team_id=?) AND status IN ('FINISHED','AWARDED')
                   ORDER BY match_date DESC LIMIT 5""",
                (tid, tid)
            ).fetchall()
            out = []
            for r in rs:
                is_home = tid == r["home_team_id"]
                out.append({
                    "home": r["home_name"], "away": r["away_name"],
                    "home_goals": r["home_goals"], "away_goals": r["away_goals"],
                    "date": r["match_date"], "is_home": is_home,
                })
            return out

        # 预测（只对未赛的算，已结束的用已有的 predictions 里的数据也可以重算）
        pred_data = None
        try:
            pred = poisson_mod.predict_match(mid)
            pred_data = {
                "lambda_home": pred.lambda_home,
                "lambda_away": pred.lambda_away,
                "home_win_prob": pred.home_win_prob,
                "draw_prob": pred.draw_prob,
                "away_win_prob": pred.away_win_prob,
                "top_scores": pred.top_scores,
                "league_avg_goals": pred.league_avg_goals,
                "penalty_home": _squad_dict(pred.penalty_home),
                "penalty_away": _squad_dict(pred.penalty_away),
            }
        except Exception:
            pass

        details[mid] = {
            "match_id": mid,
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
            "home_recent": recent(m["home_team_id"]),
            "away_recent": recent(m["away_team_id"]),
            "prediction": pred_data,
            "disclaimer": "本工具仅基于历史数据做统计概率推演，不构成任何投注建议，足球存在大量偶然性",
        }

    _save("match_details.json", details)
    print(f"  ✅ match_details.json ({len(details)} matches)")

# ============ 5. backtest.json (穿越式回测) ============
def export_backtest():
    from collections import defaultdict

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM matches WHERE home_goals IS NOT NULL ORDER BY league, match_date ASC"
        ).fetchall()

    leagues = defaultdict(list)
    for r in rows: leagues[r["league"]].append(r)

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

    data = {
        "home_advantage": HOME_ADV,
        "total_matches": sum(r["matches"] for r in result),
        "leagues": result,
        "generated_at": datetime.now().isoformat(),
    }
    _save("backtest.json", data)
    print(f"  ✅ backtest.json ({len(result)} leagues, {data['total_matches']} matches)")

# ============ 工具 ============
def _save(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============ main ============
if __name__ == "__main__":
    print("📤 导出静态 JSON 数据...")
    export_leagues()
    export_matches()
    export_predictions()
    export_match_details()
    export_backtest()
    print(f"\n✅ 全部完成 → {OUT_DIR}")
