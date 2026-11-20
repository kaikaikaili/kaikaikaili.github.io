"""全局配置 - API Key、联赛参数、模型超参"""
import os
from pathlib import Path

# ===== 数据源 =====
# football-data.org API Key（免费注册：https://www.football-data.org/）
# 没拿到 Key 也能跑 —— 会自动用内置 mock 数据
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"

# 联赛 code：英超=PL
LEAGUE_CODE = "PL"
LEAGUE_NAME = "英超"

# ===== 本地存储 =====
BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "epl.db"

# ===== API 状态映射（football-data.org 用的是 TIMED，不是 SCHEDULED）=====
# 已排期未开赛：TIMED / SCHEDULED / LIVE（任意一个都算"待预测"）
UPCOMING_STATUSES = {"TIMED", "SCHEDULED", "LIVE", "PAUSED"}
FINISHED_STATUS = "FINISHED"

# ===== 模型超参（MVP 版，全部硬编码方便回测调参）=====
RECENT_WINDOW = 10          # 近 N 场计算攻防强度
HOME_ADVANTAGE = 0.95       # 主场加成（回测最优：Brier=0.815 命中率=38.9%）
RECENT_DECAY = 0.85         # 近场衰减因子（近5场权重=1，5-10场权重=0.85）
MAX_GOALS = 5               # 泊松遍历的最大进球数

# ===== Dixon-Coles 低比分修正 =====
# 足球里真实 0-0/1-1 概率比独立泊松假设更高
# Dixon-Coles (1997) 公式：
#   τ(λ_h, λ_a) = exp(-ρ |λ_h λ_a|)
#   对 0-0 / 1-0 / 0-1 / 1-1 这四种低比分乘 τ
DC_RHO = 0.0               # Dixon-Coles（关闭：对英超 MVP 回测反而有害）

# ===== 方案 A：关键球员惩罚系数 =====
# 每缺 1 个关键球员，进攻 λ 打这个折
STAR_PLAYER_PENALTY = 0.88     # 0.88 = 每缺1人进攻降12%（可回测调）
MAX_STAR_ABSENT = 3            # 最多连续惩罚 3 人（避免过度修正）
# 隐式伤病推断：如果最近 N 场主场/客场进球均值比长期均值低这个比例
# 就认为有"进攻核心缺阵"，触发自动惩罚
INJURY_DROP_THRESHOLD = 0.55   # 近 3 场均值 < 长期均值 × 55% 时触发
INJURY_CHECK_WINDOW = 3        # 用最近 3 场检测"进攻突然下滑"
