"""运行时配置 —— R1 极简版(只保留当课要用的字段)。

⚠️ 这是教练给的临时脚手架:R5 会对照源码全量重建(env 覆盖顺序、
x_oap_ui_config、search_api 枚举等),届时本文件整体推倒。
"""

from pydantic import BaseModel
from langchain_core.runnables import RunnableConfig


class Configuration(BaseModel):
    """研究流程的可调参数。测试通过 config={"configurable": {...}} 覆盖默认值。"""

    research_model: str = "deepseek:deepseek-v4-flash"
    research_model_max_tokens: int = 8192
    search_api: str = "fake"                # "fake" | "tavily";默认离线,测试拔网线纪律不破
    compression_model: str = "deepseek:deepseek-chat"       # 压缩角色独立可配(四模型分工,R4 定选型)
    compression_model_max_tokens: int = 8192
    max_react_tool_calls: int = 10          # ReAct 循环预算(R0 你推导过的"预算耗尽"退出线)
    max_structured_output_retries: int = 3

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig | None = None) -> "Configuration":
        """从 LangGraph 传播的 RunnableConfig 里取 configurable 字段,缺省用类默认值。"""
        configurable = (config or {}).get("configurable", {})
        values = {
            k: v for k, v in configurable.items()
            if k in cls.model_fields and v is not None
        }
        return cls(**values)
