# R1 · Researcher 纵切 MVP —— 总结

> 2026-08-11 · Windows 端 · ODR 复现专题第二课(首次动手写图)

## 交付物

- `src/deep_research/state.py`:ResearchComplete 协议类 + ResearcherState(reducer=operator.add)
- `src/deep_research/utils.py`:think_tool 函数体(fake_search / get_all_tools 教练给现成)
- `src/deep_research/deep_researcher.py`:researcher / execute_tool_safely / researcher_tools 三个函数体 + 子图编译(compress_research 为 R2 占位)
- `tests/test_r1.py`:4/4 绿(2 happy + 2 failure path),全程假模型,拔网线可跑
- 配套脚手架:conftest.py、极简 configuration.py(R5 推倒重建)、prompts.py 源码原样复制(R4.5 精读)

## 过程实录(如实)

10 个 TODO 一轮全填,首跑集中爆出六类错,按"名字错 / 语义错 / 签名错"分类逐个修:

1. **`configurable_model = ...` 遮蔽全局**(最深的坑):函数内赋值 = 局部变量判定,全局模型连同测试的假模型一起被遮蔽 → 学到"链条起点引用全局,结果存新名字"+"三层包装每层返回新对象"。
2. **`with_retry` 位置传参** → 纯关键字 `stop_after_attempt=`。
3. **Configuration 字段名想当然**(`.model`/`.max_tokens`)→ 回读契约抓出。
4. **reducer 语义**:update 里带全量历史 → 手动跑表推出消息近似翻倍膨胀(3 条变 7 条);修对后又矫枉过正写出不存在的 `response.messages` → 最终理解"有 reducer 交增量,没 reducer 交全量"。
5. **Command 位置传参** → TypeError 直接教学:参数纯关键字,首位是 `graph` 另有他用。
6. **tool_calls 元素当对象访问** → dict 取值 `["name"]/["args"]/["id"]`,并理解 id 配对机制(请求单/回执单)。

R1-8 学习者主动要求看标准答案(已完成自己版本后),对照吸收了 `hasattr` 防御的来由(原生搜索工具是纯 dict)和 observation/tool_execution_tasks 的术语化命名。

课末学习者反馈"有点懵",教练做了两次整体串讲:①逐 TODO 复盘 + happy path 状态演进表;②自底向上分层调用链(state 第 0 层零依赖 → deep_researcher 唯一动词层)+ reducer 的声明位/定义/调用者。串讲后学习者**自己推出**"删 reducer 后节点交全量与现状等价"——教练确认单线等价、并发下碎裂(R3 InvalidUpdateError),此推理记入 findings。

## Quiz 状态(诚实记录)

**未亲答**。学习者当天选择听讲评,四题参考答案见 quiz.md。**R2 开工前先过 4 道变式题,通过后 R1 quiz 才关闭**——此为下个 session 的第一件事。

热身推导两题:Q1 对一半(update 干活✓,Command 优势论证未完成);Q2 方向对机制错(误用 token 论证预算检查位置)。

## 门禁三条

- ① 环境可复现:无新依赖,全套假模型离线跑 ✅
- ② pytest 绿 ≥1 happy + ≥1 failure:4/4(happy×2 + failure×2)✅
- ③ 无调试残留:清了脚手架填空注释与拖尾空格(prompts.py 保留源码原样)✅

## 面试可引用(本课新增)

1. Command + Literal 注解 = 动态边的声明机制;决策发生在信息所在的地方。
2. reducer 是并发写入的合并协议,不是语法糖;单线等价性在 fan-out 下碎裂;约束优于自觉。
3. 工具三光谱:能力 / 记录 / 信号;ResearchComplete = 施为句(调用即宣告,响应 = 一次路由)。
4. 计数点 × 检查点的相对位置 = 预算的松紧;`max_react_tool_calls` 名不符实,数的是模型调用轮数。
5. state 放数据不放能力(工具不可序列化,不进 checkpoint)。
