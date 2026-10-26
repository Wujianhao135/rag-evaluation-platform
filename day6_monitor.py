"""
Day 6 Step 4：漂移监控（Drift Monitoring）
===========================================
质量门禁是"发布时检查一次"，漂移监控是"长期记录分数趋势，发现质量悄悄下降"。

漂移（Drift）：知识库改了、Prompt 被人动了、模型供应商更新、embedding 失效……
都可能让已经正常的系统逐渐变差。靠人每天点是看不住的，要：
  1. 定时（如每天/每周）跑一次评测
  2. 把每次的分数追加记录到 score_history.csv
  3. 本次分数和历史基线对比，下降超过阈值就告警（exit 1）

三种用法：
    # 1. 把已有的门禁 JSON 报告导入历史（补建趋势）
    python day6_monitor.py --import reports/baseline_topk3.json

    # 2. 实时跑一次评测并记录（可挂到定时任务/CI 周期执行）
    python day6_monitor.py --run

    # 3. 只查看当前趋势和漂移状态
    python day6_monitor.py --trend
"""

import csv
import sys
import json
import argparse
from pathlib import Path

# 复用门禁的评测逻辑
from day6_quality_gate import run_evaluation

CSV_PATH = Path("reports/score_history.csv")
FIELDS = ["timestamp", "label", "retrieval_hit_rate",
          "answer_correct_rate", "refusal_rate", "gate_passed"]

# 漂移阈值：任一指标比"历史平均"下降超过 0.1，判定为漂移
DRIFT_THRESHOLD = 0.1


# ============================================================
# 历史记录读写
# ============================================================
def append_record(report):
    """把一次评测结果追加到 CSV"""
    CSV_PATH.parent.mkdir(exist_ok=True)
    is_new = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "timestamp": report["timestamp"],
            "label": report["label"],
            "retrieval_hit_rate": report["summary"]["retrieval_hit_rate"],
            "answer_correct_rate": report["summary"]["answer_correct_rate"],
            "refusal_rate": report["summary"]["refusal_rate"],
            "gate_passed": report["gate_passed"],
        })


def load_history():
    """读取历史记录"""
    if not CSV_PATH.exists():
        return []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ============================================================
# 趋势展示 + 漂移检测
# ============================================================
def show_trend(history):
    print("\n" + "=" * 78)
    print("质量分数趋势（score_history.csv）")
    print("=" * 78)
    print(f"{'时间':19s} {'标签':20s} {'召回':>5s} {'答案':>5s} {'拒答':>5s}  门禁")
    print("-" * 78)
    for row in history:
        gate = "✅" if row["gate_passed"] == "True" else "❌"
        print(f"{row['timestamp']:19s} {row['label']:20s} "
              f"{row['retrieval_hit_rate']:>5s} {row['answer_correct_rate']:>5s} "
              f"{row['refusal_rate']:>5s}  {gate}")


def detect_drift(history):
    """
    对比最后一次与之前所有记录的平均值，下降超过阈值即告警。
    返回 (是否漂移, 告警明细)。
    """
    if len(history) < 2:
        print("\n（历史记录不足 2 条，暂无法做漂移对比，多跑几次即可）")
        return False, []

    latest = history[-1]
    previous = history[:-1]
    metrics = ["retrieval_hit_rate", "answer_correct_rate", "refusal_rate"]

    alerts = []
    for m in metrics:
        cur = float(latest[m])
        base = sum(float(r[m]) for r in previous) / len(previous)
        drop = round(base - cur, 3)
        if drop > DRIFT_THRESHOLD:
            alerts.append(f"{m}: 历史平均 {base:.2f} → 本次 {cur:.2f}（下降 {drop:.2f}）")

    print("\n" + "=" * 78)
    print("漂移检测")
    print("=" * 78)
    if alerts:
        print("⚠️ 检测到质量漂移（下降超过 %.1f）：" % DRIFT_THRESHOLD)
        for a in alerts:
            print("  - " + a)
        print("建议：暂停发布，按 badcase_回流登记册.md 排查，可先跑一次门禁定位。")
        return True, alerts
    else:
        print("✅ 无明显漂移，最新分数在历史正常波动范围内。")
        return False, alerts


# ============================================================
# 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Day 6 漂移监控")
    parser.add_argument("--import", dest="import_path", help="导入已有门禁 JSON 报告")
    parser.add_argument("--run", action="store_true", help="实时跑一次评测并记录")
    parser.add_argument("--trend", action="store_true", help="只查看趋势和漂移")
    parser.add_argument("--label", default="scheduled", help="--run 时的标签")
    args = parser.parse_args()

    # 1. 导入历史 JSON
    if args.import_path:
        with open(args.import_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        append_record(report)
        print(f"已导入：{args.import_path}（{report['label']}）")

    # 2. 实时跑一次评测
    if args.run:
        print("实时跑一次评测 ...")
        report = run_evaluation(label=args.label)
        append_record(report)
        print("已追加到历史记录。")

    # 3. 展示趋势 + 漂移
    history = load_history()
    if not history:
        print("还没有任何历史记录，先用 --import 或 --run 产生数据。")
        return
    show_trend(history)
    drifted, _ = detect_drift(history)

    # 漂移时返回非零退出码（同样可被定时任务/CI 捕获）
    sys.exit(1 if drifted else 0)


if __name__ == "__main__":
    main()
