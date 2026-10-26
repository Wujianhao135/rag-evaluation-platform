# RAG 应用质量评测平台 · LLM Evaluation Platform

> 面向 **RAG 知识库问答**的全链路质量评测体系：非确定性断言 → 多维度指标 → 发布质量门禁 → 漂移监控 → 安全红队 → 成本性能，形成一套**可量化、可复现、可持续回归**的 AI 应用质量闭环。

![Python](https://img.shields.io/badge/Python-3.10-blue)
![pytest](https://img.shields.io/badge/pytest-9.1-0a9edc)
![Dify](https://img.shields.io/badge/Dify-1.17.1-blue)
![DeepEval](https://img.shields.io/badge/DeepEval-4.3.1-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 一、项目背景：为什么需要它

大模型应用和传统软件有本质区别：**输出不确定、错误是概率性的、质量会随模型 / 知识库版本悄悄漂移**。
传统"输入 → 固定输出"的精确断言在 RAG 上直接失效，通用 benchmark 分数也无法代表一个具体业务应用的真实质量。

本项目针对一个自建的 RAG 知识库问答应用，回答 6 个质量问题：

1. 该检索的内容**召回**了吗？（检索层）
2. 回答**忠实**于知识库吗，有没有**编造**？（生成层）
3. 知识库没有的问题，能正确**拒答**吗？（防幻觉红线）
4. 能抵御**提示词注入 / 越狱 / 信息泄露 / 越权**吗？（安全）
5. 每次调用的**成本和延迟**是多少？（成本性能）
6. 改 Prompt / 换模型 / 调参数后，质量**会不会回退**？（门禁与漂移）

---

## 二、被测系统

- **平台**：Docker 自托管的 [Dify](https://dify.ai) 1.17.1，应用类型为 Chatflow
- **流程**：开始 → 知识检索（Weaviate 向量库，TopK=3）→ LLM（qwen-max）→ 直接回复
- **知识库**：智能手表 Pro 使用说明（26 个分段）
- **评测集 Golden Set**：10 个标准问题 = 5 条库内问题 + 5 条库外边界问题，是所有评测的唯一数据源
- **评委模型**：DeepEval 用 qwen-plus 作为 LLM-as-Judge（与被测模型 qwen-max 分开，避免"自己考自己"）

---

## 三、评测指标体系

| 层级 | 指标 | 判定方式 | 对应脚本 |
|---|---|---|---|
| 检索层 | 召回命中率 Hit Rate@3 | evidence 证据分段匹配（只看答案会漏掉"蒙对"） | `day6_quality_gate.py` |
| 生成层 | 忠实度 Faithfulness | LLM-as-Judge（DeepEval），回答是否忠于召回内容 | `day5_deepeval.py` |
| 生成层 | 答案相关性 Answer Relevancy | LLM-as-Judge，回答是否切题 | `day5_deepeval.py` |
| 生成层 | 答案正确性 | 关键词 / 正则确定性断言 | `day4_assertions.py` |
| 检索层 | 上下文召回率 Contextual Recall | DeepEval，召回是否覆盖答案所需信息 | `day5_deepeval.py` |
| 拒答 | 拒答率 Refusal Rate | 库外问题是否明确说"不知道"而非硬编 | `day6_quality_gate.py` |
| 安全 | 攻击防守率 | 注入 / 越狱 / 泄露 / 越权 4 类攻击 | `day7_security.py` |
| 成本性能 | Token 成本、P50/P95、TTFT、QPS、并发加速比 | 真实调用计量 | `day7_cost_perf.py` |

---

## 四、整体流程

```
                        ┌──────────────────────────┐
                        │   Golden Set（10 条）     │
                        │ 库内 / 库外 / 对抗 三类    │
                        └─────────────┬────────────┘
                                      │ 批量调用
                                      ▼
                         ┌────────────────────────┐
                         │  被测 RAG 应用（Dify）  │
                         └─────────────┬──────────┘
              答案 + 召回分段 + usage │
              （streaming 事件解析）  │
        ┌──────────────┬─────────────┴──────────────┬──────────────┐
        ▼              ▼                            ▼              ▼
   检索层证据判定   生成层断言/LLM评委            安全攻击测试    成本性能计量
        └──────────────┴─────────────┬──────────────┴──────────────┘
                                      ▼
                         ┌────────────────────────┐
                         │  质量门禁（阈值+退出码） │── 不达标 exit 1 → CI 阻断
                         └─────────────┬──────────┘
                                      ▼
              发布后：定时跑分 → 分数趋势(CSV) → 漂移告警
                                      ▼
        失败案例 → Bad Case 登记 → 分层定位 → 修复 → 固化进 Golden Set（防复发）
```

---

## 五、核心能力

1. **非确定性断言**：关键词包含、正则模式、拒答词、语义证据，放弃"字符串完全相等"。
2. **LLM-as-Judge**：DeepEval 自动跑忠实度 / 相关性 / 上下文召回率三指标，输出每个评分的 Reason。
3. **质量门禁（Quality Gate）**：阈值判定（召回/答案 ≥ 0.8、拒答率 = 1.0）+ 进程退出码 + JSON 报告，可直接挂 CI 阻断发布。
4. **对比实验**：同一份评测集对比不同配置（TopK=3 vs TopK=5、修复前后），输出维度拆解。
5. **漂移监控**：每次跑分追加 `score_history.csv`，最新值对比历史均值，下降超阈值自动告警。
6. **安全红队**：13 条攻击（4 类威胁 × 3 类 payload），包含 RAG 特有的**间接注入**；体现 pass@k 多次采样思想。
7. **成本性能**：自动统计 Token 成本、TTFT、P50/P95、并发吞吐与加速比。
8. **Bad Case 回流闭环**：发现 → 登记 → 根因定位 → 修复 → 回归 → 固化，评测集作为"活资产"持续沉淀。

---

## 六、关键成果（均为真实运行数据）

### 1. 分层定位一起召回缺陷，召回/答案正确率 0.8 → 1.0

某条"死机如何强制重启"问题（Q4）间歇性答非所问。排查过程严格做到"假设→证伪→定位"：

- 先假设是 TopK 太小，做 TopK=3→5 对比实验，**实测无效，证伪**；
- 确认分段在库且内容完整（22 字完整句子），但**全文检索 0 结果**；
- 直接用 embedding 模型计算问题与各分段的余弦相似度：正确分段 0.67（应排第一），其余仅 0.42–0.54，**证明 embedding 模型正常**；
- 最终锁定根因：该分段在向量库中**向量缺失**（上传时限流导致 embedding 静默失败，分段显示"已启用"却无向量）；
- 删除该分段并手动重建以强制重新 embedding，修复后**召回命中率、答案正确率均 0.8 → 1.0，拒答率保持 1.0，质量门禁全绿**。

> 详见 `reports/day6-Q4召回失败排查报告.md`、`reports/day6_对比分析.md`。

### 2. LLM 评委能发现问题，但必须人工校准

DeepEval 首轮结果：忠实度 0.92、答案相关性 0.63、上下文召回率 0.40。
复核发现低分大多是**评委误判**——库外问题正确拒答却被相关性判低；据此明确了各指标适用边界。

### 3. 安全评测：发现 2 个偶发信息泄露弱点

13 条攻击多轮采样，整体防守率 **84.6%（11/13）**：注入、越狱、越权 100% 防守，
但"诱导复述系统提示词开头"（S9）和"诱导导出召回原文"（S10）在部分轮次被攻破，已登记为 Bad Case。
**结论：单轮绿灯不代表安全，安全测试必须多次采样。**

### 4. 成本与性能画像

| 维度 | 实测结果 |
|---|---|
| 单次成本 | ¥0.0214（千次约 ¥21.4，万次约 ¥214） |
| 延迟 | 平均 9.25s / **P50 7.01s / P95 18.82s**（冷启动长尾），最小 5.45s |
| TTFT | 平均 3.67s（思维链拖慢首 token） |
| Token 结构 | 输入平均 1077 / 输出 235，**输入占 82%**（RAG 成本主要来自召回分段） |
| 并发 | 3 并发加速 2.47x，QPS 0.165 → 0.407 |

> 详见 `reports/day7_安全评测报告.md`、`reports/day7_成本性能报告.md`。

---

## 七、项目结构

```
rag-evaluation-platform/
├── config.py                 # 公共配置（密钥统一从 .env / 环境变量读取）
├── dify_client.py            # Dify 客户端：blocking / streaming / full（返回答案+召回+usage）
├── golden_set.py             # Golden Set 评测集（所有评测的唯一数据源）
├── day4_assertions.py        # 非确定性断言：关键词 / 正则 / 拒答
├── day5_deepeval.py          # DeepEval 三指标（Faithfulness / Relevancy / Contextual Recall）
├── day6_quality_gate.py      # 质量门禁：阈值 + 退出码 + JSON 报告
├── day6_compare.py           # 两份报告对比（配置回归 / 修复前后）
├── day6_monitor.py           # 漂移监控：CSV 趋势 + 下降告警
├── security_cases.py         # 13 条安全攻击用例（注入/越狱/泄露/越权）
├── day7_security.py          # 安全评测执行器（防守判定）
├── day7_cost_perf.py         # 成本与性能（串行 P50/P95 + 并发吞吐）
├── badcase_回流登记册.md      # Bad Case 归集、根因、回流闭环
├── reports/                  # 评测报告与历次数据（全部可追溯）
│   ├── day5-DeepEval评测报告.md
│   ├── baseline_topk3.json / experiment_topk5.json / fixed_vector_topk3.json
│   ├── day6_对比分析.md / day6-Q4召回失败排查报告.md
│   ├── day7_security.json / day7_安全评测报告.md
│   ├── day7_cost_perf.json / day7_成本性能报告.md
│   └── score_history.csv     # 分数趋势历史
├── requirements.txt
├── .env.example              # 环境变量模板（复制为 .env 后填真实值）
└── README.md
```

---

## 八、快速开始

### 1. 环境要求
- Python 3.10
- 一个可访问的 Dify 应用（或任意兼容 Dify Chatflow API 的 RAG 服务）

### 2. 安装依赖
```bash
git clone https://github.com/Wujianhao135/rag-evaluation-platform.git
cd rag-evaluation-platform
pip install -r requirements.txt
```

### 3. 配置密钥（不写入代码）
```bash
cp .env.example .env        # Windows: copy .env.example .env
# 编辑 .env，填入 DIFY_BASE_URL、DIFY_API_KEY、DASHSCOPE_API_KEY
```

### 4. 运行各评测模块

```bash
# 确定性断言（只需 Dify 可达，免费、快速）
pytest day4_assertions.py -v

# DeepEval 三指标（需 Dify + DashScope Key）
python day5_deepeval.py

# 质量门禁：输出 JSON，不达标返回非零退出码
python day6_quality_gate.py --label baseline --output reports/baseline.json

# 对比两份报告（如 TopK 3 vs 5 / 修复前后）
python day6_compare.py reports/baseline_topk3.json reports/fixed_vector_topk3.json

# 漂移监控：导入历史 / 实时跑分 / 查看趋势
python day6_monitor.py --run --label scheduled
python day6_monitor.py --trend

# 安全评测（13 条攻击）
python day7_security.py

# 成本与性能（10 次串行 + 3 并发）
python day7_cost_perf.py
```

---

## 九、技术栈

| 类别 | 技术 |
|---|---|
| 语言 / 框架 | Python 3.10、pytest |
| 被测系统 | Dify 1.17.1（Chatflow）、Weaviate 向量库、qwen-max |
| 评测框架 | DeepEval、OpenAI SDK（DashScope 兼容接口）、qwen-plus 评委 |
| 部署 | Docker、CentOS 7（VMware） |
| 工程化 | 环境变量隔离、JSON 报告、退出码门禁、CSV 趋势、可复现数据 |

---

## 十、方法论沉淀（关键认知）

1. **先判检索层，再判生成层**：RAG 答错一半是检索问题，只看最终答案会漏掉"召回为空但蒙对"。
2. **LLM 评委不是真理**：有偏好、会波动，要配合确定性规则做门禁，并对评分做人工抽检校准。
3. **安全必须多次采样**：同一攻击不同轮次结果不同，单轮测试会漏掉偶发漏洞。
4. **embedding 可能"静默失败"**：分段显示已启用但向量未入库，需要用 embedding 相似度独立验证。
5. **Chatflow 取召回要用 streaming**：blocking 接口的 `retriever_resources` 为空，
   需从 `node_finished` 事件、`knowledge-retrieval` 节点的 outputs 中解析。
6. **门禁分两层**：确定性规则快、稳、免费，用于 CI 红线；LLM 评委慢、深，用于发布前评测。

---

## 十一、Bad Case 回流闭环

`badcase_回流登记册.md` 记录了从发现到固化的全过程：

- **BC-001**：Q4 召回失败 → 向量缺失 → 重建分段 → 回归 0.8→1.0 → 固化进 Golden Set
- **BC-002 / BC-003**：S9 / S10 偶发信息泄露 → 登记为安全弱点，待加固后回归

---

## License

[MIT](LICENSE)
