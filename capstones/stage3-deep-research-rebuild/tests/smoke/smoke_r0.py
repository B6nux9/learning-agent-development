"""R0 smoke test:验证两条外部依赖各自能通(DeepSeek + Tavily)。

运行方式(在 stage3-deep-research-rebuild 目录下):
    uv run python tests/smoke/smoke_r0.py

预期输出:两段各打印一行结果,无异常退出。
这是手动冒烟脚本,不进 pytest(单测纪律=拔网线也能跑绿,冒烟=专门联网验证)。
"""

from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch

# key 在课程仓库根的 .env(smoke → tests → 模块目录 → capstones → 仓库根)
REPO_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(REPO_ROOT / ".env")


def smoke_llm() -> str:
    """调通 DeepSeek:让模型回答一个固定问题,返回回答文本。

    契约:
    - 用 init_chat_model 初始化 "deepseek:deepseek-chat"
      (源码同款入口,模型无关抽象;key 自动从环境变量 DEEPSEEK_API_KEY 读)
    - invoke 一个简单问题(如"用一句话介绍 LangGraph")
    - 返回 str:模型回复的正文(提示:invoke 返回的是 AIMessage,不是 str)
    """
    # TODO(R0-1): 初始化模型 → invoke → 返回回复正文(约 3 行)
    client = init_chat_model("deepseek:deepseek-v4-flash")
    response = client.invoke("用一句话介绍 LangGraph")
    return response.content

def smoke_search() -> str:
    """调通 Tavily:搜一个查询,返回第一条结果的标题。

    契约:
    - 用 TavilySearch(max_results=3) 建工具
      (key 自动从环境变量 TAVILY_API_KEY 读)
    - invoke 查询字符串(如 "LangGraph supervisor pattern")
    - 返回 str:第一条结果的标题
      (提示:invoke 返回 dict,真正的结果列表在哪个键下、每条结果的标题又在哪个键下——
       print 出来看一眼结构再取,这个"先看形状再取数"的动作 R2 还会用到)
    """
    # TODO(R0-2): 建工具 → invoke → 返回第一条标题(约 3 行)
    search_tool = TavilySearch(max_results=3)
    response = search_tool.invoke("LangGraph supervisor pattern")
    return response["results"][0]["title"]

if __name__ == "__main__":
    print("[1/2] DeepSeek:", smoke_llm())
    print("[2/2] Tavily :", smoke_search())
    print("R0 smoke ✅ 两条外部依赖都通了")
