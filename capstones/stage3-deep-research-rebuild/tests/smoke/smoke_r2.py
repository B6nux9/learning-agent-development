"""R2 冒烟:researcher 子图首次真跑(DeepSeek + Tavily)。

跑法(在 stage3-deep-research-rebuild/ 目录):uv run python tests/smoke/smoke_r2.py
成本护栏:max_react_tool_calls=3。
"""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(REPO_ROOT / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from langchain_core.messages import HumanMessage
from deep_research.deep_researcher import researcher_subgraph


async def main() -> None:
    topic = "What are the practical differences between LangGraph's Send API and plain asyncio.gather for fanning out parallel agents?"
    result = await researcher_subgraph.ainvoke(
        {
            # 研究主题以种子 HumanMessage 进场(R3 里这是 supervisor_tools 的活,冒烟先代劳)
            "researcher_messages": [HumanMessage(content=topic)],
            "research_topic": topic,
        },
        config={"configurable": {"search_api": "tavily", "max_react_tool_calls": 3}},
    )
    print("=== compressed_research ===")
    print(result["compressed_research"][:2000])
    print()
    print(f"raw_notes: {len(result['raw_notes'])} 条,共 {len(result['raw_notes'][0])} 字符")
    print("R2 smoke ✅")


if __name__ == "__main__":
    asyncio.run(main())
