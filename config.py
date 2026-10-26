"""
公共配置文件
================
所有脚本共用的配置都集中在这里，改配置只需要改这一个文件。

敏感配置（Dify 地址 / Dify API Key / DashScope Key）统一从环境变量或本地
``.env`` 文件读取，**不写进代码、不提交到 Git**。

首次使用：
    1. 复制 ``.env.example`` 为 ``.env``
    2. 在 ``.env`` 里填入真实的 Dify 地址、应用 API Key、DashScope Key
"""

import os

from dotenv import load_dotenv

# 加载本地 .env（若存在）；已存在的系统环境变量优先级更高，不会被覆盖
load_dotenv()

# ============================================================
# Dify 被测应用配置
# ============================================================
# 被测 Dify 应用的访问地址（本地虚拟机 / 服务器）
DIFY_BASE_URL = os.environ.get("DIFY_BASE_URL", "http://localhost")

# Dify 应用的 API Key（app-xxx 格式，在「访问 API」页面获取）
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "app-xxxxxxxx")


# ============================================================
# DashScope 评委模型配置（DeepEval 用）
# ============================================================
# 从环境变量 / .env 读取付费密钥，避免写进代码
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

# 评委模型（qwen-plus 便宜快速；被测应用用的是 qwen-max，两者分开）
JUDGE_MODEL = "qwen-plus"

# 请求间隔（秒），避免触发 DashScope 限流
SLEEP_BETWEEN_CASES = 3
