"""
L5 作业:给 agent 加【长期记忆】(跨会话/跨重启记住用户)

沿用你 capstone 的肌肉(多轮 REPL + 工具 loop),这次只挖 L5 的新肌肉——长期记忆的"存 + 取":

  TODO 1  load_memory() / save_memory():读写一个 memory.json(持久层)
  TODO 2  会话启动时,把长期记忆【注入 system prompt】(这就是"取")
  TODO 3  remember 工具:让模型识别到"值得记住的事实"时,自己调它把事实写回文件("存")
          —— 呼应 L4:把"要不要记"这个判断折进 tool use,而不是另起一个分类调用

跑通标准(分两次运行验证跨重启记忆):
  第 1 次运行:
    你> 我叫小明,以后只收顺丰快递
    (模型应调用 remember 把这两条写进 memory.json)
    你> 退出
  第 2 次运行(重开程序):
    你> 你还记得我吗?
    (agent 应答出"小明""偏好顺丰"——记忆活过了重启)
"""

import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

MODEL = "deepseek-v4-flash"
MAX_TURNS = 8
MEMORY_FILE = "memory.json"


# ---- 一个演示用的业务工具(你已有的肌肉,给全)----
FAKE_ORDERS = {
    "A123": {"status": "运输中", "carrier": "顺丰"},
    "B456": {"status": "已签收", "carrier": "京东"},
}

def query_order(order_id: str) -> str:
    order = FAKE_ORDERS.get(order_id)
    if order is None:
        return json.dumps({"error": f"查无此订单:{order_id}"}, ensure_ascii=False)
    return json.dumps(order, ensure_ascii=False)


# ============================================================
#  TODO 1:长期记忆的持久层 —— 读 / 写 memory.json
# ============================================================
def load_memory() -> dict:
    """读取 memory.json 返回一个 dict。
    提示:文件不存在(第一次运行)时,别崩,返回空 dict {}。
    """
    # 你的代码:
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_memory(memory: dict) -> None:
    """把 memory 整个写回 memory.json(用 ensure_ascii=False,想想为什么——L4 学过)。"""
    # 你的代码:
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=4)


# ============================================================
#  TODO 3:remember 工具 —— 让模型自己"存"
# ============================================================
def remember(key: str, value: str) -> str:
    """把一条要长期记住的事实写进 memory.json,如 key='name' value='小明'。
    实现:load 出当前 memory -> 更新这条 key -> save 回去 -> 返回一句成功 JSON。
    """
    # 你的代码:
    memory = load_memory()
    memory[key] = value
    save_memory(memory)
    return json.dumps({"ok": True, "message": f"已记住: {key} = {value}"}, ensure_ascii=False)


TOOLS = [
    {"type": "function", "function": {
        "name": "query_order",
        "description": "根据订单号查询物流状态和承运商",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string", "description": "订单号,如 A123"}}, "required": ["order_id"]}}},
    # ---- TODO 3(续):给 remember 写 schema ----
    # 要求:name 对上号;两个参数 key、value(都必填);description 里引导模型
    #   "当用户透露了值得长期记住的个人信息/偏好(如姓名、快递偏好)时,调用它记下来"。
    # 你的 schema:
    {"type": "function", "function": {
        "name": "remember",
        "description": "当用户透露了值得长期记住的个人信息/偏好(如姓名、快递偏好)时,调用它记下来",
        "parameters" : {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "要记住的事实的键,如 'name' 或 'preferred_carrier'"},
                "value": {"type": "string", "description": "要记住的事实的值,如 '小明' 或 '顺丰'"}
            },
            "required": ["key", "value"]
        }}
    }
]

AVAILABLE_TOOLS = {"query_order": query_order, "remember": remember}


# ============================================================
#  TODO 2:把长期记忆注入 system prompt("取")
# ============================================================
def build_system_prompt() -> str:
    """读出长期记忆,拼进 system prompt。
    提示:
      - 基础人设固定:"你是电商客服助手..."
      - load_memory() 若非空,把里面的键值格式化成一段"你已知的用户信息:..."追加进去。
      - 若为空(新用户),就只有基础人设。
    想清楚:为什么注入 system 而不是伪装成一条 user 消息?(quiz Q4 你答过)
    """
    # 你的代码:
    memory = load_memory()
    base_prompt = "你是电商客服助手,请礼貌、专业地回答用户的问题,并在必要时调用工具查询订单信息或记住用户的偏好。"
    return base_prompt + ("\n你已知的用户信息:\n" + "\n".join(f"{k}: {v}" for k, v in memory.items()) if memory else "")

def run_agent(messages: list) -> str:
    turn = 0
    while turn < MAX_TURNS:
        turn += 1
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        msg = response.choices[0].message
        if not msg.tool_calls:
            messages.append(msg)
            return msg.content
        messages.append(msg)
        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            try:
                result = AVAILABLE_TOOLS[name](**args)
            except Exception as e:
                result = json.dumps({"error": str(e)}, ensure_ascii=False)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
    return "抱歉,这个问题我暂时处理不了,已为您转接人工客服"


def main():
    # 会话启动:system prompt 里已带上长期记忆(TODO 2 完成后)
    messages = [{"role": "system", "content": build_system_prompt()}]
    while True:
        user_input = input("你> ")
        if user_input.lower() in ["quit", "exit", "退出"]:
            print("客服助手: 感谢使用,再见!")
            break
        messages.append({"role": "user", "content": user_input})
        print(f"客服助手: {run_agent(messages)}")


if __name__ == "__main__":
    main()
