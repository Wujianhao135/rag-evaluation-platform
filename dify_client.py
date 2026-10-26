"""
Dify 客户端封装
================
所有脚本共用的 Dify 调用逻辑，提供三种模式：

1. ask_dify_blocking()：阻塞模式，只拿最终答案
   - Day 4 手写断言用这个（只需要答案文本）

2. ask_dify_streaming()：流式模式，同时拿答案 + 知识检索召回的分段
   - Day 5 DeepEval / Day 6 门禁用这个（评测召回率需要知道召回了哪些分段）
   - 注意：Chatflow 用 blocking 模式时 retriever_resources 是空的，
     必须用 streaming 从 node_finished 事件里提取召回结果

3. ask_dify_full()：流式模式，额外返回 token usage（含价格、延迟）
   - Day 7 成本与性能评测用这个
"""

import re
import json
import requests

import config


def clean_answer(text: str) -> str:
    """
    过滤掉模型的 <think> 思维链内容，只保留最终答案。
    有些模型会先输出 <think>...</think> 推理过程，再给正式回答。
    """
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def ask_dify_blocking(query: str, user: str = "test-user") -> str:
    """
    阻塞模式调用 Dify，返回最终答案文本。

    适用于：只关心答案、不关心召回分段的场景（如 Day 4 断言）。
    """
    url = f"{config.DIFY_BASE_URL}/v1/chat-messages"
    headers = {
        "Authorization": f"Bearer {config.DIFY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": {},
        "query": query,
        "response_mode": "blocking",
        "user": user,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return clean_answer(resp.json()["answer"])


def ask_dify_full(query: str, user: str = "test-user"):
    """
    流式模式调用 Dify，返回 (答案, 召回分段列表, token usage)。

    返回:
        (answer, retrieval_context, usage)
        - answer: 最终答案文本（已过滤思维链）
        - retrieval_context: 知识检索节点召回的分段内容列表
        - usage: message_end 事件里的计费/延迟信息，字段包括
            prompt_tokens / completion_tokens / total_tokens
            total_price（元，RMB）/ latency / time_to_first_token 等
    """
    url = f"{config.DIFY_BASE_URL}/v1/chat-messages"
    headers = {
        "Authorization": f"Bearer {config.DIFY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": {},
        "query": query,
        "response_mode": "streaming",
        "user": user,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
    resp.raise_for_status()

    answer = ""
    retrieval_context = []
    usage = None

    for line in resp.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8")
        if line.startswith("data: "):
            data = json.loads(line[6:])
            event = data.get("event")

            # 拼接最终答案
            if event in ("agent_message", "message"):
                answer += data.get("answer", "")

            # 从「知识检索节点完成」事件里提取召回分段
            if event == "node_finished":
                node_data = data.get("data", {})
                if node_data.get("node_type") == "knowledge-retrieval":
                    result = node_data.get("outputs", {}).get("result", [])
                    if isinstance(result, list):
                        for seg in result:
                            if isinstance(seg, dict) and seg.get("content"):
                                retrieval_context.append(seg["content"])

            # 消息结束：提取计费与延迟信息
            if event == "message_end":
                usage = data.get("metadata", {}).get("usage")

    return clean_answer(answer), retrieval_context, usage


def ask_dify_streaming(query: str, user: str = "test-user"):
    """
    流式模式调用 Dify，返回 (答案, 召回分段列表)。

    适用于：需要召回分段的评测（如 Day 5 上下文召回率、Day 6 门禁）。
    """
    answer, retrieval_context, _ = ask_dify_full(query, user=user)
    return answer, retrieval_context
