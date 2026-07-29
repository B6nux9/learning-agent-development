"""
入口/实验层 (main.py) —— 今天只验证「查订单」纵切链路。

模拟一个「已登录用户」：会话里 user_id = u_zhang（代码注入，不是用户输入的）。
两个问题演示这条链路 + 越权保护：
  1. 问自己的订单 A123 → 应查到、正常答
  2. 问别人的订单 C789（属于 u_li）→ 应收敛成「没查到」，不泄露存在性
"""

from __future__ import annotations

from agent import run

SESSION_USER_ID = "u_zhang"  # 假装此人已登录

if __name__ == "__main__":
    demo = [
        "我的订单 A123 到哪了？",          # 查订单：正常
        "帮我查下订单 C789 的状态",         # 查订单：别人的 → 收敛「没查到」
        "我要退订单 A123 的款",            # 退款：199≤200 → 自动退
        "那帮我退了 D999 吧",              # 退款：699>200 → 阈值挡下转人工
        "退货运费到底谁出啊？",           # 政策问答：命中组 → 生成文本
        "你们双十一有啥活动？"            # 政策问答：未覆盖组 → 转人工
    ]
    for q in demo:
        print(f"\n用户({SESSION_USER_ID}): {q}")
        print(f"客服: {run(q, SESSION_USER_ID)}")
