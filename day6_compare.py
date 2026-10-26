"""
Day 6 Step 2：对比实验报告
==========================
对比改参数前后的两份门禁 JSON 报告，用数据判断改动是否有效。

解决的问题：改了 TopK / Prompt / 分块后，到底是变好还是变差？
光看主观感觉不行，必须前后跑同一套 Golden Set，对比数字。

运行方式：
    python day6_compare.py reports/baseline_topk3.json reports/experiment_topk5.json
"""

import sys
import json
import argparse
from datetime import datetime


def load_report(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def arrow(delta):
    """根据变化值返回箭头符号"""
    if delta > 0.0001:
        return "↑ 提升"
    if delta < -0.0001:
        return "↓ 下降"
    return "— 持平"


def compare(base, exp):
    """对比两份报告，返回文本报告和关键结论"""
    lines = []
    lines.append("=" * 64)
    lines.append("对比实验报告")
    lines.append("=" * 64)
    lines.append(f"基线（A）：{base['label']}  @ {base['timestamp']}")
    lines.append(f"实验（B）：{exp['label']}  @ {exp['timestamp']}")

    # ---- 1. 汇总指标对比 ----
    lines.append("\n【一、三个指标前后对比】")
    lines.append(f"{'指标':24s} {'A基线':>7s} → {'B实验':>7s}   {'变化':>8s}  结论")
    lines.append("-" * 64)

    improved, regressed = [], []
    for metric in base["summary"]:
        a = base["summary"][metric]
        b = exp["summary"][metric]
        delta = round(b - a, 3)
        mark = arrow(delta)
        if delta > 0.0001:
            improved.append(metric)
        elif delta < -0.0001:
            regressed.append(metric)
        lines.append(f"{metric:24s} {a:>7} → {b:>7}   {delta:>+8.3f}  {mark}")

    # ---- 2. 逐用例对比 ----
    lines.append("\n【二、逐用例对比】")
    base_cases = {c["id"]: c for c in base["cases"]}
    lines.append(f"{'用例':4s} {'类别':6s} {'召回 A→B':12s} {'答案 A→B':12s} {'拒答 A→B':12s} 变化")
    lines.append("-" * 64)

    def mark_bool(v):
        if v is None:
            return "—"
        return "✓" if v else "✗"

    fixed, broken = [], []
    for ec in exp["cases"]:
        cid = ec["id"]
        bc = base_cases[cid]
        cat = ec["category"]

        # 库内问题对比召回和答案
        if cat == "known":
            r_a, r_b = bc["retrieval_hit"], ec["retrieval_hit"]
            a_a, a_b = bc["answer_correct"], ec["answer_correct"]
            change = ""
            if not r_a and r_b:
                change = "★召回修复"
                fixed.append(cid)
            if r_a and not r_b:
                change = "⚠召回退化"
                broken.append(cid)
            if not a_a and a_b:
                change += " ★答案修复"
            if a_a and not a_b:
                change += " ⚠答案退化"
            lines.append(f"{cid:4s} {cat:6s} {mark_bool(r_a)}→{mark_bool(r_b):8s} "
                         f"{mark_bool(a_a)}→{mark_bool(a_b):8s} {'—':12s} {change}")
        # 库外问题对比拒答
        else:
            f_a, f_b = bc["refused"], ec["refused"]
            change = ""
            if not f_a and f_b:
                change = "★拒答修复"
                fixed.append(cid)
            if f_a and not f_b:
                change = "⚠拒答退化(可能编造)"
                broken.append(cid)
            lines.append(f"{cid:4s} {cat:6s} {'—':12s} {'—':12s} "
                         f"{mark_bool(f_a)}→{mark_bool(f_b):8s} {change}")

    # ---- 3. 门禁结论 ----
    lines.append("\n【三、门禁结论】")
    lines.append(f"基线 A 门禁：{'✅ PASS' if base['gate_passed'] else '❌ FAIL'}")
    lines.append(f"实验 B 门禁：{'✅ PASS' if exp['gate_passed'] else '❌ FAIL'}")

    # ---- 4. 决策建议 ----
    lines.append("\n【四、决策建议】")
    if broken:
        lines.append(f"❌ 存在退化用例 {broken}，本次改动有副作用，不建议采纳，需进一步排查。")
    elif improved or fixed:
        lines.append(f"✅ 修复/改善了 {fixed or improved}，且没有引入退化，建议采纳本次改动。")
    else:
        lines.append("— 没有明显变化，本次改动无实质收益（可不改，避免增加召回噪声/成本）。")

    return "\n".join(lines), fixed, broken


def main():
    parser = argparse.ArgumentParser(description="对比两份门禁报告")
    parser.add_argument("baseline", help="基线报告 JSON 路径")
    parser.add_argument("experiment", help="实验报告 JSON 路径")
    parser.add_argument("--md", default="reports/day6_对比分析.md", help="Markdown 对比报告输出路径")
    args = parser.parse_args()

    base = load_report(args.baseline)
    exp = load_report(args.experiment)
    text, fixed, broken = compare(base, exp)

    print(text)

    # 保存 Markdown 对比报告
    with open(args.md, "w", encoding="utf-8") as f:
        f.write(f"# Day 6 对比实验报告\n\n> 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n\n```\n")
        f.write(text)
        f.write("\n```\n")
    print(f"\nMarkdown 报告已保存：{args.md}")


if __name__ == "__main__":
    main()
