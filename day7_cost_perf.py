"""
Day 7 Step 2：成本与性能评测
============================
真实多次调用 Dify，测量延迟、Token、成本和吞吐。

两部分：
  A. 串行基准：对 Golden Set 10 个问题各调用一次，统计
     - 总延迟 / TTFT 的 平均、P50、P95、最大
     - input/output/total token 均值
     - 单次成本、千次/万次成本估算
  B. 并发吞吐：3 并发请求，测总耗时与 QPS，对比串行

输出：
  - reports/day7_cost_perf.json
  - reports/day7_成本性能报告.md

运行：
  python day7_cost_perf.py
"""

import time
import json
import statistics
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from dify_client import ask_dify_full
from golden_set import ALL_CASES


def percentile(data, p):
    """计算 P 分位数（data 为已排序列表）"""
    if not data:
        return 0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (k - f) * (s[c] - s[f])


def one_call(question, user):
    """单次调用，返回（本地端到端耗时, usage）"""
    t0 = time.time()
    _, _, usage = ask_dify_full(question, user=user)
    wall = time.time() - t0
    return wall, usage


# ============================================================
# A. 串行基准
# ============================================================
def run_serial():
    print("A. 串行基准测试（10 个问题，约 40-60 秒）")
    records = []
    for i, case in enumerate(ALL_CASES):
        wall, usage = one_call(case["question"], user="day7-perf")
        usage = usage or {}
        rec = {
            "id": case["id"],
            "wall_latency": round(wall, 3),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "price": float(usage.get("total_price", 0)),
            "ttft": usage.get("time_to_first_token", 0),
        }
        records.append(rec)
        print(f"  {case['id']}: 延迟 {rec['wall_latency']:5.2f}s "
              f"token {rec['total_tokens']:5d} 成本 ¥{rec['price']:.4f}")
        time.sleep(1)
    return records


def analyze_serial(records):
    lat = [r["wall_latency"] for r in records]
    ttft = [r["ttft"] for r in records if r["ttft"]]
    prompt_t = [r["prompt_tokens"] for r in records]
    completion_t = [r["completion_tokens"] for r in records]
    total_t = [r["total_tokens"] for r in records]
    prices = [r["price"] for r in records]

    return {
        "latency": {
            "mean": round(statistics.mean(lat), 2),
            "p50": round(percentile(lat, 50), 2),
            "p95": round(percentile(lat, 95), 2),
            "max": round(max(lat), 2),
            "min": round(min(lat), 2),
        },
        "ttft": {
            "mean": round(statistics.mean(ttft), 2) if ttft else 0,
            "p95": round(percentile(ttft, 95), 2) if ttft else 0,
        },
        "tokens": {
            "prompt_mean": round(statistics.mean(prompt_t)),
            "completion_mean": round(statistics.mean(completion_t)),
            "total_mean": round(statistics.mean(total_t)),
        },
        "cost": {
            "per_call_mean": round(statistics.mean(prices), 4),
            "per_1000": round(statistics.mean(prices) * 1000, 2),
            "per_10000": round(statistics.mean(prices) * 10000, 2),
        },
    }


# ============================================================
# B. 并发吞吐
# ============================================================
def run_concurrent(n_workers=3):
    print(f"\nB. 并发吞吐测试（{n_workers} 并发，3 个问题）")
    questions = [ALL_CASES[i]["question"] for i in range(3)]

    # 串行参照
    t0 = time.time()
    for q in questions:
        one_call(q, user="day7-perf-serial")
    serial_elapsed = time.time() - t0

    # 并发
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        list(ex.map(lambda q: one_call(q, "day7-perf-concurrent"), questions))
    concurrent_elapsed = time.time() - t0

    return {
        "n_requests": len(questions),
        "workers": n_workers,
        "serial_elapsed": round(serial_elapsed, 2),
        "concurrent_elapsed": round(concurrent_elapsed, 2),
        "qps_serial": round(len(questions) / serial_elapsed, 3),
        "qps_concurrent": round(len(questions) / concurrent_elapsed, 3),
        "speedup": round(serial_elapsed / concurrent_elapsed, 2),
    }


def write_report(records, serial_stats, conc_stats):
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "serial_records": records,
        "serial_stats": serial_stats,
        "concurrent": conc_stats,
    }
    Path("reports").mkdir(exist_ok=True)
    with open("reports/day7_cost_perf.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    L, T, C = serial_stats["latency"], serial_stats["ttft"], serial_stats["tokens"]
    CO = serial_stats["cost"]
    md = [
        "# Day 7 成本与性能报告", "",
        f"> 时间：{report['timestamp']}（10 次串行 + 3 并发）", "",
        "## 一、延迟（端到端，含网络）", "",
        "| 指标 | 秒 |", "|---|---|",
        f"| 平均延迟 | {L['mean']} |",
        f"| P50 | {L['p50']} |",
        f"| P95 | {L['p95']} |",
        f"| 最大 | {L['max']} |",
        f"| 最小 | {L['min']} |",
        f"| 平均 TTFT（首 token） | {T['mean']} |",
        f"| TTFT P95 | {T['p95']} |", "",
        "## 二、Token 消耗（每次平均）", "",
        "| 类型 | 平均 Token |", "|---|---|",
        f"| input（提示词+检索） | {C['prompt_mean']} |",
        f"| output（回答） | {C['completion_mean']} |",
        f"| total | {C['total_mean']} |", "",
        "## 三、成本（RMB，Dify 计费）", "",
        "| 口径 | 金额 |", "|---|---|",
        f"| 单次平均 | ¥{CO['per_call_mean']} |",
        f"| 1000 次 | ¥{CO['per_1000']} |",
        f"| 10000 次 | ¥{CO['per_10000']} |", "",
        "## 四、并发吞吐", "",
        "| 口径 | 数值 |", "|---|---|",
        f"| 请求数 | {conc_stats['n_requests']} |",
        f"| 串行耗时 | {conc_stats['serial_elapsed']}s |",
        f"| {conc_stats['workers']} 并发耗时 | {conc_stats['concurrent_elapsed']}s |",
        f"| 串行 QPS | {conc_stats['qps_serial']} |",
        f"| 并发 QPS | {conc_stats['qps_concurrent']} |",
        f"| 加速比 | {conc_stats['speedup']}x |", "",
        "## 五、解读要点", "",
        "- TTFT 较高通常与模型先输出思维链(think)有关；关闭思维链可显著降低首 token 延迟。",
        "- RAG 的 input token 占大头（检索分段），优化召回段数/精简 Prompt 可降本。",
        "- 成本随调用量线性增长，上线前要按预期 DAU 估算月度账单。",
        "- 并发加速受模型 API 限流(RPM/TPM)制约，超出会 429，需要限流与降级。",
    ]
    with open("reports/day7_成本性能报告.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))


def main():
    print("=" * 60)
    print("成本与性能评测开始")
    print("=" * 60)
    records = run_serial()
    stats = analyze_serial(records)
    print("\n串行统计：")
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    conc = run_concurrent(3)
    print("\n并发统计：")
    print(json.dumps(conc, ensure_ascii=False, indent=2))

    write_report(records, stats, conc)
    print("\n报告已保存：reports/day7_成本性能报告.md")


if __name__ == "__main__":
    main()
