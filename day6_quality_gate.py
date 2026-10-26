"""
Day 6 Step 1：质量门禁（Quality Gate）
======================================
把评测从"人眼看分数"变成"脚本自动判断能不能发布"。

工作流程（这就是 CI/CD 里质量门禁的原理）：
    1. 自动跑一遍 Golden Set（调 Dify 拿答案 + 召回分段）
    2. 计算 3 个【确定性】指标（不调评委模型，几秒跑完，免费且稳定）：
       - 召回命中率 retrieval_hit_rate：该召回的证据有没有召回（Q1-Q5）
       - 答案正确率 answer_correct_rate：答案是否含正确关键信息（Q1-Q5）
       - 拒答正确率 refusal_rate：       知识库外问题是否正确说"不知道"（Q6-Q10）
    3. 对照阈值判断：任何指标低于阈值 → 门禁不通过
    4. 生成机器可读的 JSON 报告（CI 可以解析）
    5. 退出码：通过 exit 0（绿灯放行）；不通过 exit 1（红灯阻断）

为什么不用 DeepEval 当门禁？
    DeepEval 要调评委模型（慢、花钱、评委本身有波动），适合"发布前深度评测"；
    门禁要快、稳、可重复，适合"每次提交都跑"，所以用确定性的规则指标。

运行方式：
    python day6_quality_gate.py                         # 输出到 reports/gate_report.json
    python day6_quality_gate.py --label topk5          # 打标签，用于对比实验
    python day6_quality_gate.py --output reports/x.json
"""

import re
import sys
import json
import argparse
from datetime import datetime

from dify_client import ask_dify_streaming
from golden_set import KNOWN_CASES, UNKNOWN_CASES, REFUSAL_KEYWORDS


# ============================================================
# 门禁阈值（发布红线）
# ============================================================
THRESHOLDS = {
    "retrieval_hit_rate": 0.8,   # 5 个库内问题，至少 4 个召回成功
    "answer_correct_rate": 0.8,  # 5 个库内问题，至少 4 个答案正确
    "refusal_rate": 1.0,         # 库外问题必须 100% 拒答（编造是红线）
}


# ============================================================
# 判定函数
# ============================================================
def normalize(text: str) -> str:
    """归一化：去所有空白 + 转小写，让 '300mAh'/'300 mAh' 能匹配"""
    return re.sub(r"\s+", "", text).lower()


def check_retrieval(case, contexts):
    """召回是否成功：evidence 证据词必须全部出现在召回分段里"""
    blob = normalize("".join(contexts))
    missing = [e for e in case["evidence"] if normalize(e) not in blob]
    return len(missing) == 0, missing


def check_answer(case, answer):
    """答案是否正确：keywords 全部命中，或 patterns 全部匹配"""
    if case["keywords"]:
        blob = normalize(answer)
        missing = [k for k in case["keywords"] if normalize(k) not in blob]
        return len(missing) == 0, missing
    if case["patterns"]:
        # 正则用原始答案（pattern 里用 \\s* 已兼容空格）
        missing = [p for p in case["patterns"] if not re.search(p, answer, re.IGNORECASE)]
        return len(missing) == 0, missing
    return True, []


def check_refusal(answer):
    """库外问题是否正确拒答：命中任意一个拒答词"""
    return any(kw in answer for kw in REFUSAL_KEYWORDS)


# ============================================================
# 跑一遍评测，返回结构化结果
# ============================================================
def run_evaluation(label=""):
    cases_detail = []
    retrieval_hits = 0
    answer_correct = 0
    refusals = 0

    # ---- 知识库内问题：评召回 + 答案 ----
    for case in KNOWN_CASES:
        print(f"[库内] {case['id']}: {case['question']}")
        answer, contexts = ask_dify_streaming(case["question"], user="day6-gate")

        ret_hit, ret_missing = check_retrieval(case, contexts)
        ans_ok, ans_missing = check_answer(case, answer)
        retrieval_hits += int(ret_hit)
        answer_correct += int(ans_ok)

        print(f"    召回{'✓' if ret_hit else '✗ 缺:' + str(ret_missing)}"
              f"  答案{'✓' if ans_ok else '✗ 缺:' + str(ans_missing)}")

        cases_detail.append({
            "id": case["id"], "category": "known", "question": case["question"],
            "answer": answer, "retrieval_contexts": contexts,
            "retrieval_hit": ret_hit, "retrieval_missing": ret_missing,
            "answer_correct": ans_ok, "answer_missing": ans_missing,
            "refused": None,
        })

    # ---- 知识库外问题：评拒答 ----
    for case in UNKNOWN_CASES:
        print(f"[库外] {case['id']}: {case['question']}")
        answer, contexts = ask_dify_streaming(case["question"], user="day6-gate")

        refused = check_refusal(answer)
        refusals += int(refused)
        print(f"    拒答{'✓' if refused else '✗ 可能编造！'}")

        cases_detail.append({
            "id": case["id"], "category": "unknown", "question": case["question"],
            "answer": answer, "retrieval_contexts": contexts,
            "retrieval_hit": None, "retrieval_missing": None,
            "answer_correct": None, "answer_missing": None,
            "refused": refused,
        })

    n_known = len(KNOWN_CASES)
    n_unknown = len(UNKNOWN_CASES)
    summary = {
        "retrieval_hit_rate": round(retrieval_hits / n_known, 3),
        "answer_correct_rate": round(answer_correct / n_known, 3),
        "refusal_rate": round(refusals / n_unknown, 3),
    }

    # 门禁判断
    gate_passed = all(
        summary[metric] >= threshold for metric, threshold in THRESHOLDS.items()
    )

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "label": label,
        "summary": summary,
        "thresholds": THRESHOLDS,
        "gate_passed": gate_passed,
        "cases": cases_detail,
    }


# ============================================================
# 打印门禁结论
# ============================================================
def print_gate_result(report):
    print("\n" + "=" * 60)
    print("质量门禁结果" + (f"（标签：{report['label']}）" if report["label"] else ""))
    print("=" * 60)
    for metric, value in report["summary"].items():
        threshold = report["thresholds"][metric]
        ok = value >= threshold
        print(f"  {'✓' if ok else '✗'} {metric:24s} = {value:<5} 阈值 {threshold}")

    print("-" * 60)
    if report["gate_passed"]:
        print("  ✅ 门禁通过（PASS，exit 0）：可以发布")
    else:
        print("  ❌ 门禁不通过（FAIL，exit 1）：阻断发布，请修复失败项")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Day 6 质量门禁")
    parser.add_argument("--label", default="", help="本次运行标签（如 baseline / topk5）")
    parser.add_argument("--output", default="reports/gate_report.json", help="JSON 报告输出路径")
    args = parser.parse_args()

    print("=" * 60)
    print("开始运行质量门禁（确定性指标，约 1-2 分钟）")
    print("=" * 60)

    report = run_evaluation(label=args.label)
    print_gate_result(report)

    # 保存 JSON 报告
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nJSON 报告已保存：{args.output}")

    # 退出码：CI 靠它判断是否阻断
    sys.exit(0 if report["gate_passed"] else 1)


if __name__ == "__main__":
    main()
