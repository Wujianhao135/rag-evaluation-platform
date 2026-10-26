"""
Day 5：DeepEval 框架上手
=========================
用 DeepEval 自动评测 Dify 知识库问答，跑 3 个核心指标：

1. FaithfulnessMetric（忠实度）：回答有没有编造（对照召回分段）
2. AnswerRelevancyMetric（答案相关性）：回答有没有切题
3. ContextualRecallMetric（上下文召回率）：该召回的分段有没有召回

- Dify 调用：dify_client.py（streaming 模式，同时拿答案和召回分段）
- 测试数据：golden_set.py
- 评委模型：qwen-plus，通过 DashScope 的 OpenAI 兼容接口接入

运行前准备：
    pip install deepeval openai requests
    （DashScope Key 从环境变量 DASHSCOPE_API_KEY 读取）

运行方式：
    python day5_deepeval.py
注意：10 个用例 × 3 个指标，约 3-5 分钟。
"""

import time
from openai import OpenAI
from deepeval import evaluate
from deepeval.evaluate import AsyncConfig, DisplayConfig
from deepeval.test_case import LLMTestCase
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualRecallMetric,
)

import config
from dify_client import ask_dify_streaming
from golden_set import ALL_CASES


# ============================================================
# 第一部分：DashScope 评委模型（自定义 DeepEval 模型）
# ============================================================
class QwenJudgeModel(DeepEvalBaseLLM):
    """
    用通义千问作为 DeepEval 的评委。
    DeepEval 默认用 OpenAI，这里通过 OpenAI 兼容接口接入 DashScope。
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=config.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    def load_model(self):
        return self.client

    def generate(self, prompt: str, schema=None, **kwargs) -> str:
        """DeepEval 把评分问题发给评委，评委返回判断结果"""
        response = self.client.chat.completions.create(
            model=config.JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,  # 评委要确定性，温度设 0
        )
        return response.choices[0].message.content

    async def a_generate(self, prompt: str, schema=None, **kwargs) -> str:
        return self.generate(prompt, schema)

    def get_model_name(self):
        return config.JUDGE_MODEL


# ============================================================
# 第二部分：调用 Dify 构造测试用例
# ============================================================
def build_test_cases():
    """逐个调用 Dify，把 10 个问题的回答和召回结果构造成 DeepEval 用例"""
    test_cases = []

    for i, case in enumerate(ALL_CASES):
        print(f"[{i+1}/{len(ALL_CASES)}] 调用 Dify: {case['question']}")
        answer, contexts = ask_dify_streaming(case["question"], user="day5")

        print(f"    召回分段: {len(contexts)} 个")
        print(f"    回答: {answer[:80]}...\n")

        test_cases.append(
            LLMTestCase(
                input=case["question"],
                actual_output=answer,
                retrieval_context=contexts if contexts else ["（未召回任何相关内容）"],
                expected_output=case["expected_output"],
            )
        )

        if i < len(ALL_CASES) - 1:
            time.sleep(config.SLEEP_BETWEEN_CASES)

    return test_cases


# ============================================================
# 第三部分：运行评测
# ============================================================
def main():
    if not config.DASHSCOPE_API_KEY:
        print("=" * 60)
        print("未找到环境变量 DASHSCOPE_API_KEY！")
        print("PowerShell 临时设置: $env:DASHSCOPE_API_KEY='你的sk-xxx'")
        print("或在系统环境变量中永久配置")
        print("=" * 60)
        return

    print("=" * 60)
    print(f"DeepEval 评测开始（评委模型：{config.JUDGE_MODEL}）")
    print("=" * 60)

    # 1. 构造测试用例
    test_cases = build_test_cases()

    # 2. 评委模型
    judge = QwenJudgeModel()

    # 3. 三个指标（阈值 0.7，低于 0.7 判失败）
    metrics = [
        FaithfulnessMetric(threshold=0.7, model=judge),
        AnswerRelevancyMetric(threshold=0.7, model=judge),
        ContextualRecallMetric(threshold=0.7, model=judge),
    ]

    # 4. 运行评测（同步、单并发、加间隔，避免限流）
    print("=" * 60)
    print("评委模型开始打分（需要几分钟，请耐心等待）...")
    print("=" * 60)
    evaluate(
        test_cases,
        metrics,
        async_config=AsyncConfig(run_async=False, max_concurrent=1, throttle_value=2),
        display_config=DisplayConfig(show_indicator=True, print_results=True),
    )


if __name__ == "__main__":
    main()
