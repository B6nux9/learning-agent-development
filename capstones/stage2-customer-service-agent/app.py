"""
阶段二 Capstone · 最小部署层 (app.py)

把命令行的 run() 搬上 HTTP：POST /chat。核心生产纪律——
**用户身份从认证来（X-User-Token → user_id），不从请求体信任**。
这条线一以贯之：capstone 工具注入 user_id → MCP server 侧注入 → 这里 HTTP auth 注入。

跑起来（本地）：uv run uvicorn app:app --reload
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from agent import run

app = FastAPI(title="客服 Agent")


# --------------------------------------------------------------------------
# 假认证台账（真实项目里是 JWT / session store / OAuth；这里 token→user_id 映射够演示）
# 关键：身份的**唯一真相在服务端这张表**，客户端只持有不透明 token，改不了自己是谁。
# --------------------------------------------------------------------------
FAKE_TOKENS = {
    "tok_zhang": "u_zhang",
    "tok_li": "u_li",
}


# --------------------------------------------------------------------------
# 请求体模型 —— 只收 message，**故意不含 user_id**（身份从认证来，不从 body 信任）
# --------------------------------------------------------------------------
class ChatRequest(BaseModel):
    # 只声明一个字段：message: str。
    # 想清楚：为什么这里不加 user_id 字段？（写完答我，回扣 MCP 越权那次）
    message: str


class ChatResponse(BaseModel):
    reply: str


# --------------------------------------------------------------------------
# 认证 —— 从 header 取 token，查出 user_id；查不到就 401
# --------------------------------------------------------------------------
def resolve_user(x_user_token: str | None = Header(default=None)) -> str:
    """把请求头 X-User-Token 解析成 user_id。

    接口契约（FastAPI 语法我给了：Header(default=None) 会自动从
    `X-User-Token` 请求头取值；函数名参数 x_user_token 的下划线对应 header 的横线）：
      - token 缺失（None）或不在 FAKE_TOKENS 里 → raise HTTPException(status_code=401, detail="...")
      - 命中 → return 对应的 user_id
    约束：这就是「身份从认证来」的落地点。**绝不从请求体读身份。**
    """
    if not x_user_token:
        raise HTTPException(status_code=401, detail="缺少 X-User-Token")
    if x_user_token not in FAKE_TOKENS:
        raise HTTPException(status_code=401, detail="无效的 X-User-Token")
    return FAKE_TOKENS[x_user_token]


# --------------------------------------------------------------------------
# POST /chat —— 把一句用户消息交给 agent.run，返回答复
# --------------------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user_id: str = Depends(resolve_user)) -> ChatResponse:
    """接口契约：
      1. 先拿身份：user_id = resolve_user(...)。
         —— FastAPI 的做法是把 resolve_user 作为**依赖**注入，而不是自己手调。
            提示：给 chat 再加一个参数 `user_id: str = Depends(resolve_user)`
            （需要 from fastapi import Depends）。这样认证在进 chat 前就跑完，
            401 会在到达这里之前自动返回。
      2. 调 run(req.message, user_id) 拿答复。
      3. run() 可能抛（模型宕机/网络）→ 用 try/except 兜成
         HTTPException(status_code=503, detail="服务暂时不可用，请稍后再试")，
         **不要把异常栈暴露给用户**（生产要 logger.exception 记下来）。
      4. 正常 → return ChatResponse(reply=答复)。
    """
    try:
        reply = run(req.message, user_id)
    except Exception as e:
        # 生产环境里要 logger.exception(e) 记下来
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后再试") from e
    return ChatResponse(reply=reply)


# 健康检查（无需认证）——部署时给容器/负载均衡探活用
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
