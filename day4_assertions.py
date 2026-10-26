"""
Day 4：非确定性断言策略（手写断言）
====================================
演示 3 种面向 AI 输出的断言方式：
1. 关键词包含断言（Keyword）：答案必须出现预期关键词
2. 正则表达式断言（Regex）：数字/格式用正则匹配
3. 拒答检测断言（Refusal）：知识库外问题必须回答"不知道"，不能编造

测试数据来自 golden_set.py，Dify 调用来自 dify_client.py。

运行方式：
    pip install requests pytest
    pytest day4_assertions.py -v
"""

import time
import pytest

from dify_client import ask_dify_blocking
from golden_set import KNOWN_CASES, UNKNOWN_CASES, REFUSAL_KEYWORDS


# ============================================================
# 断言 1：关键词包含
# 适用：答案有明确关键词的事实型问题
# ============================================================
class TestKeywordAssertion:
    @pytest.mark.parametrize("case", KNOWN_CASES, ids=[c["id"] for c in KNOWN_CASES])
    def test_answer_contains_keywords(self, case):
        """答案中必须包含预期关键词"""
        if not case["keywords"]:
            pytest.skip("该用例使用正则断言，见 TestRegexAssertion")

        answer = ask_dify_blocking(case["question"], user="day4")
        print(f"\n问题 [{case['id']}]: {case['question']}")
        print(f"模型回答: {answer}")
        print(f"预期关键词: {case['keywords']}")

        missing = [kw for kw in case["keywords"] if kw not in answer]
        assert not missing, f"答案缺少关键词: {missing}，实际回答: {answer}"


# ============================================================
# 断言 2：正则表达式
# 适用：验证数字、日期、格式等有固定模式的内容
# ============================================================
class TestRegexAssertion:
    @pytest.mark.parametrize("case", KNOWN_CASES, ids=[c["id"] for c in KNOWN_CASES])
    def test_answer_matches_pattern(self, case):
        """答案必须匹配预期正则模式"""
        if not case["patterns"]:
            pytest.skip("该用例使用关键词断言")

        answer = ask_dify_blocking(case["question"], user="day4")
        print(f"\n问题 [{case['id']}]: {case['question']}")
        print(f"模型回答: {answer}")
        print(f"预期正则: {case['patterns']}")

        for pattern in case["patterns"]:
            assert __import__("re").search(pattern, answer) is not None, (
                f"答案未匹配模式 '{pattern}'，实际回答: {answer}"
            )


# ============================================================
# 断言 3：拒答检测
# 适用：知识库外问题，模型应明确表示无法回答，不能编造
# ============================================================
class TestRefusalAssertion:
    @pytest.mark.parametrize("case", UNKNOWN_CASES, ids=[c["id"] for c in UNKNOWN_CASES])
    def test_unknown_question_refuses(self, case):
        """知识库外问题，模型应回答'不知道'，不能编造"""
        answer = ask_dify_blocking(case["question"], user="day4")
        print(f"\n问题 [{case['id']}]: {case['question']}")
        print(f"模型回答: {answer}")

        refused = any(kw in answer for kw in REFUSAL_KEYWORDS)
        assert refused, (
            f"知识库外问题未拒答，可能存在编造！\n"
            f"问题: {case['question']}\n回答: {answer}"
        )


if __name__ == "__main__":
    # 直接运行：快速验证一个问题
    print("快速测试:", ask_dify_blocking("智能手表Pro的型号是什么？", user="day4"))
