"""
门禁 · app.py HTTP 接口测试 (test_app.py)

FastAPI TestClient：不用真起 uvicorn，直接在进程内打接口。
正例会走到 run() → 碰网络，故 monkeypatch 掉 app.run（在**使用处**打桩，L10 回扣），零网络。
反例（401）在认证阶段就返回，到不了 run，天然不碰网络。

覆盖三条：
  ① 正：合法 token → 200 + 返回 run 的答复
  ② 反：无 token → 401（认证挡在 run 之前）
  ③ 安全：合法 token 但 body 偷塞 user_id → run 收到的仍是 **token 对应的身份**，不是 body 的
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import app

client = TestClient(app)


@pytest.fixture
def spy_run(monkeypatch):
    """把 app.run 换成一个「不碰网络、且记下被调用参数」的假 run。
    返回一个 dict，测试里可读 calls['args'] 看 run 到底收到了什么 (message, user_id)。"""
    calls = {}

    def fake_run(user_message, session_user_id, guard=None):
        calls["args"] = (user_message, session_user_id)
        return "[假答复] 已处理"

    monkeypatch.setattr(app_module, "run", fake_run)
    return calls


# --------------------------------------------------------------------------
# ① 正：合法 token → 200 + 返回 run 的答复
# --------------------------------------------------------------------------
def test_chat_valid_token(spy_run):
    resp = client.post(
        "/chat",
        headers={"X-User-Token": "tok_zhang"},
        json={"message": "我的订单 A123 到哪了？"},
    )
    # 200 + 返回 run 的答复 + run 收到的 user_id 是 token 解析出的 u_zhang
    assert resp.status_code == 200
    assert resp.json()["reply"] == "[假答复] 已处理"
    assert spy_run["args"][1] == "u_zhang"


# --------------------------------------------------------------------------
# ② 反：无 token → 401（不该走到 run）
# --------------------------------------------------------------------------
def test_chat_missing_token(spy_run):
    resp = client.post("/chat", json={"message": "你好"})
    # 401，且 run 根本没被调用（验证「认证挡在 run 之前」，不只测状态码）
    assert resp.status_code == 401
    assert "args" not in spy_run


# --------------------------------------------------------------------------
# ③ 安全：合法 token 但 body 偷塞 user_id → run 收到的仍是 token 的身份
#   这条把「身份从认证来、不从 body 信任」用测试钉死，是招牌卖点的测试背书。
# --------------------------------------------------------------------------
def test_chat_body_cannot_spoof_identity(spy_run):
    resp = client.post(
        "/chat",
        headers={"X-User-Token": "tok_li"},          # 认证身份 = u_li
        json={"message": "帮我查订单 A123", "user_id": "u_zhang"},  # body 想冒充 u_zhang
    )
    # 200，且 run 收到的 user_id 是 token 的 u_li（**不是** body 偷塞的 u_zhang）
    assert resp.status_code == 200
    assert spy_run["args"][1] == "u_li"
