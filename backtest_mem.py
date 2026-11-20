"""全联赛穿越式回测（内存优化版）
一次加载全部比赛，逐联赛在内存里做滚动强度计算，避免逐场 SQL。
"""
import sqlite3, sys, time, math
from collections import defaultdict

sys.path.insert(0, ".")
import config

conn = sqlite3.connect("epl.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT * FROM matches WHERE home_goals IS NOT NULL ORDER BY league, match_date ASC"
).fetchall()
conn.close()

print(f"加载 {len(rows)} 场已结束比赛...")

# 按联赛分组
leagues = defaultdict(list)
for r in rows:
    leagues[r["league"]].append(r)

LEAGUE_NAMES = {
    "PL": "英超", "ELC": "英冠", "PD": "西甲", "SA": "意甲",
    "BL1": "德甲", "FL1": "法甲", "PPL": "葡超", "BSA": "巴甲",
    "CL": "欧冠", "CLI": "解放者杯", "WC": "世界杯",
}

HOME_ADV = config.HOME_ADVANTAGE
MAX_GOALS = config.MAX_GOALS
DECAY = config.RECENT_DECAY

def poisson_pmf(k, lam):
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)

def calc_league_avg(league_matches, up_to_idx):
    """截止 up_to_idx（不含）的联赛平均"""
    if up_to_idx < 5: return {"home": 1.4, "away": 1.1, "total": 2.5}
    hg = sum(league_matches[i]["home_goals"] for i in range(up_to_idx))
    ag = sum(league_matches[i]["away_goals"] for i in range(up_to_idx))
    n = up_to_idx
    return {"home": hg/n, "away": ag/n, "total": (hg+ag)/n}

def calc_team_strength_mem(team_id, league_matches, up_to_idx, league_avg):
    """在内存里算某队截止 up_to_idx 的攻防强度"""
    home_gf = []
    away_gf = []
    home_ga = []
    away_ga = []
    for i in range(up_to_idx):
        m = league_matches[i]
        if m["home_team_id"] == team_id:
            home_gf.append(m["home_goals"])
            home_ga.append(m["away_goals"])
        if m["away_team_id"] == team_id:
            away_gf.append(m["away_goals"])
            away_ga.append(m["home_goals"])

    def wavg(arr):
        if not arr: return 1.2
        ws = wsum = 0.0
        for i, v in enumerate(arr[:10]):
            w = DECAY ** i
            wsum += v * w; ws += w
        return wsum / ws if ws > 0 else 1.2

    hg, hc = wavg(home_gf), wavg(home_ga)
    ag, ac = wavg(away_gf), wavg(away_ga)
    la_home = max(league_avg["home"], 0.1)
    la_away = max(league_avg["away"], 0.1)
    return {
        "home_att": max(hg, 0.1) / la_home,
        "home_def": max(hc, 0.1) / la_away,
        "away_att": max(ag, 0.1) / la_away,
        "away_def": max(ac, 0.1) / la_home,
    }

def predict_one_mem(home_team_id, away_team_id, league_matches, up_to_idx):
    league_avg = calc_league_avg(league_matches, up_to_idx)
    home = calc_team_strength_mem(home_team_id, league_matches, up_to_idx, league_avg)
    away = calc_team_strength_mem(away_team_id, league_matches, up_to_idx, league_avg)

    lam_h = home["home_att"] * away["away_def"] * league_avg["home"] * HOME_ADV
    lam_a = away["away_att"] * home["home_def"] * league_avg["away"]

    home_win = draw = away_win = 0.0
    score_probs = {}
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            p = poisson_pmf(h, lam_h) * poisson_pmf(a, lam_a)
            score_probs[f"{h}-{a}"] = score_probs.get(f"{h}-{a}", 0.0) + p
            if h > a: home_win += p
            elif h == a: draw += p
            else: away_win += p

    total = home_win + draw + away_win
    return home_win/total, draw/total, away_win/total, score_probs

t0 = time.time()
print(f"\n{'='*75}")
print(f"  🏆 全联赛穿越式回测（内存优化版，HOME_ADV={HOME_ADV}）")
print(f"{'='*75}")
print(f"\n  {'联赛':>10s}  {'场次':>6s}  {'命中率':>8s}  {'Brier':>8s}  {'平局命中':>10s}  {'耗时':>7s}")
print(f"  {'-'*66}")

total_eff = total_hit = total_brier = 0

for lg in sorted(leagues.keys()):
    lm = leagues[lg]
    n = len(lm)
    hit = brier_sum = 0
    n_draw = hit_draw = 0
    t1 = time.time()

    for i in range(5, n):
        m = lm[i]
        hg, ag = m["home_goals"], m["away_goals"]
        actual = 0 if hg > ag else (1 if hg == ag else 2)

        hw, dw, aw, sp = predict_one_mem(
            m["home_team_id"], m["away_team_id"], lm, i
        )
        probs = [hw, dw, aw]
        pred_cat = probs.index(max(probs))

        one_hot = [0.0, 0.0, 0.0]
        one_hot[actual] = 1.0
        brier = sum((p - o) ** 2 for p, o in zip(probs, one_hot))

        hit += int(pred_cat == actual)
        brier_sum += brier
        if actual == 1:
            n_draw += 1
            hit_draw += int(pred_cat == 1)

    elapsed = time.time() - t1
    hr = hit / (n - 5)
    bd = brier_sum / (n - 5)
    dhr = (hit_draw / n_draw * 100) if n_draw > 0 else 0
    ln = LEAGUE_NAMES.get(lg, lg)

    print(f"  {ln:>10s}  {n-5:>6d}  {hr*100:>7.1f}%  {bd:>8.4f}  {dhr:>7.1f}%({hit_draw}/{n_draw})  {elapsed:>6.1f}s")

    total_eff += n - 5
    total_hit += hit
    total_brier += brier_sum

total_hr = total_hit / total_eff
total_bd = total_brier / total_eff
total_elapsed = time.time() - t0

print(f"  {'-'*66}")
print(f"  {'总计':>10s}  {total_eff:>6d}  {total_hr*100:>7.1f}%  {total_bd:>8.4f}  总耗时 {total_elapsed:.0f}s")
print(f"\n{'='*75}")
print(f"  英超优秀模型参考：命中率 45-55%  Brier 0.55-0.65")
print(f"{'='*75}\n")
