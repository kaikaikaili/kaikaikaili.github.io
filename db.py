"""SQLite 建表与连接管理 - 只存 3 张核心表"""
import sqlite3
from pathlib import Path

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    team_id     INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    short_name  TEXT,
    crest       TEXT,
    -- 每次拉数据后重算
    avg_home_goals      REAL DEFAULT 0,
    avg_away_goals      REAL DEFAULT 0,
    avg_home_conceded   REAL DEFAULT 0,
    avg_away_conceded   REAL DEFAULT 0,
    updated_at          TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matches (
    match_id        INTEGER PRIMARY KEY,
    league          TEXT    NOT NULL,
    home_team_id    INTEGER NOT NULL,
    away_team_id    INTEGER NOT NULL,
    home_name       TEXT    NOT NULL,
    away_name       TEXT    NOT NULL,
    match_date      TEXT    NOT NULL,          -- ISO8601
    status          TEXT    NOT NULL,          -- SCHEDULED / LIVE / FINISHED
    home_goals      INTEGER,                  -- NULL = 未踢
    away_goals      INTEGER,
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS predict_records (
    record_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id        INTEGER NOT NULL,
    predicted_at    TEXT    DEFAULT CURRENT_TIMESTAMP,
    lambda_home     REAL    NOT NULL,
    lambda_away     REAL    NOT NULL,
    home_win_prob   REAL    NOT NULL,
    draw_prob       REAL    NOT NULL,
    away_win_prob   REAL    NOT NULL,
    top_score       TEXT    NOT NULL,          -- '2-1' 这种
    top_score_prob  REAL    NOT NULL,
    -- 比赛结束后回填
    actual_home     INTEGER,
    actual_away     INTEGER,
    hit_result      INTEGER,                   -- 主胜/平/客胜 预测是否命中 0/1
    hit_score       INTEGER,                   -- 比分是否命中 0/1
    brier_score     REAL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_predict_match ON predict_records(match_id);
"""


def get_conn() -> sqlite3.Connection:
    """返回连接 + 启用 WAL 模式（并发友好）"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    """首次运行建表"""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    print(f"[DB] 初始化完成 → {DB_PATH}")


if __name__ == "__main__":
    init_db()
