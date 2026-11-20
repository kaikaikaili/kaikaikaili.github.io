# 足球概率推演工具 — MVP

基于加权泊松分布的足球比赛胜平负概率推演 + 比分预测 + 穿越式回测仪表盘。

**⚠ 定位：纯统计分析工具，不构成任何投注建议。**

## 功能

- 12 个联赛，1.3 万场历史数据
- 加权泊松模型 + 阵容惩罚（隐式伤病推断）
- 穿越式回测：五大联赛命中率 48.6%，Brier 0.633（英超优秀模型区间 0.55-0.65）
- Vue3 + ECharts 可视化

## 本地开发

```bash
# 后端（可选，纯前端不需要）
pip install fastapi uvicorn
python main_api.py         # → http://localhost:8000

# 前端开发
cd frontend
npm install
npm run dev                # → http://localhost:5173
```

## 静态导出（GitHub Pages 用）

```bash
# 1. 从 SQLite 导出 JSON 数据
python export_static.py

# 2. 前端 build
cd frontend
npm run build

# 3. 产物在 frontend/dist/，全部复制到仓库根或 gh-pages 分支
```

## 数据

数据源：[football-data.org](https://www.football-data.org/)（免费 API）

| 联赛 | 代码 |
|---|---|
| 英超 | PL | 西甲 PD | 意甲 SA | 德甲 BL1 | 法甲 FL1 |
| 荷甲 | DED | 葡超 PPL | 巴甲 BSA | 英冠 ELC |
| 欧冠 | CL | 解放者杯 CLI | 世界杯 WC |

## 参数调优

模型超参在 `config.py`：

| 参数 | 默认值 | 说明 |
|---|---|---|
| HOME_ADVANTAGE | 0.95 | 主场加成系数 |
| RECENT_WINDOW | 10 | 近 N 场算攻防强度 |
| RECENT_DECAY | 0.85 | 时间衰减因子 |
| STAR_PLAYER_PENALTY | 0.88 | 缺一名核心的 λ 折扣 |
