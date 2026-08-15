"""R3 测试 —— supervisor 子图(状态协议 / supervisor 节点 / 拦截与 fan-out / 预算)。

Group A:状态协议(override_reducer / ConductResearch / SupervisorState)。
"""

from typing import get_args, get_type_hints

import pytest
from pydantic import ValidationError

from deep_research.state import ConductResearch, SupervisorState, override_reducer


class TestOverrideReducer:
    """双语义 reducer:普通值走追加,{"type": "override"} 信封走整体替换。"""

    def test_add_mode_appends(self):
        # 普通 list 走 operator.add 老路
        assert override_reducer([1, 2], [3]) == [1, 2, 3]

    def test_override_mode_replaces(self):
        # override 信封:旧值整个丢弃
        assert override_reducer([1, 2], {"type": "override", "value": [9]}) == [9]

    def test_override_empty_list_resets(self):
        # R1 quiz 的老问题"add reducer 无法清空字段"——override 信封做到了
        assert override_reducer([1, 2], {"type": "override", "value": []}) == []


class TestConductResearch:
    """派活协议工具:带字段的那种(对比 ResearchComplete 的空壳)。"""

    def test_research_topic_field_exists(self):
        cr = ConductResearch(research_topic="quantum computing impact on cryptography")
        assert cr.research_topic == "quantum computing impact on cryptography"

    def test_research_topic_required(self):
        # 派活单不许空着交
        with pytest.raises(ValidationError):
            ConductResearch()

    def test_field_description_is_model_facing(self):
        # Field(description=...) 会进 bind_tools 生成的 schema——是写给模型的填表说明
        desc = ConductResearch.model_fields["research_topic"].description
        assert desc and "topic" in desc.lower()


class TestSupervisorState:
    """supervisor 子图状态:5 字段,3 个挂 override_reducer。"""

    def test_field_set(self):
        assert set(SupervisorState.__annotations__) == {
            "supervisor_messages",
            "research_brief",
            "notes",
            "research_iterations",
            "raw_notes",
        }

    def test_override_reducer_attached(self):
        hints = get_type_hints(SupervisorState, include_extras=True)
        for field in ("supervisor_messages", "notes", "raw_notes"):
            assert override_reducer in get_args(hints[field]), f"{field} 应挂 override_reducer"
