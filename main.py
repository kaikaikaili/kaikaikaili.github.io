"""CLI 入口 —— 一条命令跑通全流程
用法：
    python main.py sync          # 拉数据 + 算攻防强度
    python main.py predict       # 对所有未赛比赛跑预测
    python main.py backfill      # 回填历史赛果命中情况
    python main.py backtest      # 打印回测统计面板
    python main.py all           # sync → predict → backfill → backtest 一条龙
    python main.py one 2001     # 只预测某一场（match_id）
"""
import sys

from db import init_db
from fetcher import fetch_data
from poisson import predict_match, print_prediction
from predictor import predict_all_scheduled, save_prediction, backfill_outcomes
from backtest import print_backtest_summary


def cmd_sync():
    init_db()
    fetch_data()


def cmd_predict():
    results = predict_all_scheduled()
    print(f"\n✅ 已对 {len(results)} 场未赛比赛生成预测并存入 DB\n")
    for r in results:
        print_prediction(r)


def cmd_backfill():
    n = backfill_outcomes()
    print(f"\n✅ 回填了 {n} 条历史预测记录")


def cmd_backtest():
    print_backtest_summary()


def cmd_one(match_id: int):
    r = predict_match(match_id)
    save_prediction(r)
    print_prediction(r)


def cmd_all():
    print(">>> [1/4] 拉取数据")
    init_db()
    fetch_data()
    print(">>> [2/4] 生成预测")
    cmd_predict()
    print(">>> [3/4] 回填赛果")
    cmd_backfill()
    print(">>> [4/4] 回测统计")
    cmd_backtest()


HELP = """\
用法：python main.py <command>

  sync       拉取数据 + 更新球队攻防强度
  predict    对所有未赛比赛跑泊松预测并入库
  backfill   用已结束比赛回填历史预测的命中情况
  backtest   打印回测统计面板
  one <mid>  只预测某一场（match_id）
  all        sync → predict → backfill → backtest 一条龙

没有 API Key 也能跑 —— 会自动使用内置 mock 英超数据。
拿 Key：https://www.football-data.org/ （免费）
设置：$env:FOOTBALL_DATA_API_KEY="你的key"
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(HELP)
        return

    cmd = sys.argv[1]
    if cmd == "sync":
        cmd_sync()
    elif cmd == "predict":
        cmd_predict()
    elif cmd == "backfill":
        cmd_backfill()
    elif cmd == "backtest":
        cmd_backtest()
    elif cmd == "all":
        cmd_all()
    elif cmd == "one":
        if len(sys.argv) < 3:
            print("❌ 请给出 match_id，例如 python main.py one 2001")
            return
        cmd_one(int(sys.argv[2]))
    else:
        print(f"❌ 未知命令：{cmd}\n")
        print(HELP)


if __name__ == "__main__":
    main()
