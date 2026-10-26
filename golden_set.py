"""
Golden Set（黄金测试集）
========================
10 个标准测试问题，是所有评测的「唯一数据源」。
Day 4 的手写断言、Day 5 的 DeepEval 都从这里导入，避免重复维护。

数据结构说明：
- id:              用例编号
- question:        用户问题
- category:        "known"=知识库内有答案；"unknown"=知识库外应拒答
- expected_output: 参考答案（DeepEval 上下文召回率用）
- evidence:        召回成功判据：召回分段里必须出现的高区分度证据词
                   （Day 6 召回命中率用，全部出现才算这条问题召回成功）
- keywords:        答案里必须出现的关键词（Day 4 关键词断言用）
- patterns:        答案必须匹配的正则模式（Day 4 正则断言用）
                   （keywords / patterns 二选一，都没有表示该用例走拒答检测）
"""

# ============================================================
# 第一类：知识库内有答案的 5 个问题（known）
# ============================================================
KNOWN_CASES = [
    {
        "id": "Q1",
        "question": "智能手表Pro的型号是什么？",
        "category": "known",
        "expected_output": "智能手表Pro的产品型号是SW-2024，是一款面向运动健康场景的可穿戴设备。",
        "evidence": ["SW-2024"],
        "keywords": ["SW-2024"],
        "patterns": [],
    },
    {
        "id": "Q2",
        "question": "这款手表的电池容量是多少？典型续航多久？",
        "category": "known",
        "expected_output": "电池容量300mAh，典型使用场景续航7天，重度使用约3天。",
        "evidence": ["300mAh", "7天"],
        "keywords": [],
        "patterns": [r"300\s*mAh", r"7\s*天"],
    },
    {
        "id": "Q3",
        "question": "血氧测量一次需要多长时间？",
        "category": "known",
        "expected_output": "血氧测量每次约需15秒，为手动测量，测量范围70%-100%。",
        "evidence": ["15秒"],
        "keywords": ["15"],
        "patterns": [],
    },
    {
        "id": "Q4",
        "question": "手表死机了怎么强制重启？",
        "category": "known",
        "expected_output": "若手表出现死机，可长按电源键15秒强制重启。",
        "evidence": ["重启"],  # 用高区分度词，不能用"15"（蓝牙5.0/电量30%也有数字）
        "keywords": ["15"],
        "patterns": [],
    },
    {
        "id": "Q5",
        "question": "客服热线是什么？工作时间是？",
        "category": "known",
        "expected_output": "客服热线400-888-9999，工作时间周一至周日9:00-21:00。",
        "evidence": ["400-888-9999"],
        "keywords": ["400-888-9999", "9:00", "21:00"],
        "patterns": [],
    },
]

# ============================================================
# 第二类：知识库外没有答案的 5 个问题（unknown，应回答"不知道"）
# ============================================================
UNKNOWN_CASES = [
    {
        "id": "Q6",
        "question": "这款手表的价格是多少钱？",
        "category": "unknown",
        "expected_output": "知识库中没有相关信息，应回答不知道。",
        "keywords": [],
        "patterns": [],
    },
    {
        "id": "Q7",
        "question": "手表支持NFC支付功能吗？",
        "category": "unknown",
        "expected_output": "知识库中没有相关信息，应回答不知道。",
        "keywords": [],
        "patterns": [],
    },
    {
        "id": "Q8",
        "question": "生产厂家的地址在哪里？",
        "category": "unknown",
        "expected_output": "知识库中没有相关信息，应回答不知道。",
        "keywords": [],
        "patterns": [],
    },
    {
        "id": "Q9",
        "question": "手表有几种颜色可选？",
        "category": "unknown",
        "expected_output": "知识库中没有相关信息，应回答不知道。",
        "keywords": [],
        "patterns": [],
    },
    {
        "id": "Q10",
        "question": "怎么更换手表的表盘壁纸？",
        "category": "unknown",
        "expected_output": "知识库中没有相关信息，应回答不知道。",
        "keywords": [],
        "patterns": [],
    },
]

# 全部 10 个用例（按 Q1-Q10 顺序）
ALL_CASES = KNOWN_CASES + UNKNOWN_CASES

# 拒答关键词：模型表示"不知道"的常见说法（Day 4 拒答检测用）
REFUSAL_KEYWORDS = ["不知道", "无法回答", "没有相关", "未提及", "没有提到", "无法提供"]
