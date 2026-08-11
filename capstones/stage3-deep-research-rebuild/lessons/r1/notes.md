# R1 · Researcher 纵切 MVP —— 讲义

> 2026-08-11,Windows 端。交付:researcher 子图(ReAct 循环 + 三退出条件 + 并发工具执行),4 测试全绿,拔网线可跑。

## 一、今天造了什么

```
START → researcher ──→ researcher_tools ──→ compress_research → END
           ↑                  │(不满足退出条件)      (R1 占位,R2 主角)
           └──────────────────┘
```

三层图的最底层。R3 的 supervisor = 并发开 N 个这个东西。

## 二、三个新原语

### 1. Command(goto=..., update=...) —— 节点自己当路由器

- 一个对象同时携带路由决定 + 状态增量;对比 `add_conditional_edges`:**决策发生在信息所在的地方**,不用为路由函数往 state 塞只为路由服务的字段。
- researcher 的 goto 是静态的(等价于一条 add_edge,源码用 Command 只为风格统一);**researcher_tools 的动态路由才是 Command 的主场**。
- 参数是**纯关键字**(keyword-only):`Command(goto=..., update=...)`,位置写法直接 TypeError。第一个参数名是 `graph`,另有他用。
- 返回类型注解 `Command[Literal["researcher", "compress_research"]]` **就是边的声明**——LangGraph 编译期读 Literal 注册可能目的地。这就是 researcher ⇄ researcher_tools 之间零条 add_edge 的原因。

### 2. bind_tools —— 交出说明书,不交出方向盘

- 只把工具 schema(名字/docstring/参数)塞进请求,让模型**能表达**"我想调 X"。
- 模型返回的 `tool_calls` 只是**意图声明**;执行、响应、路由全在 researcher_tools 里。
- 工具三光谱:fake_search = **能力**(真干活)/ think_tool = **记录**(反思固化进历史)/ ResearchComplete = **信号**(施为句:调用即宣告,宣告即生效,生效机制是路由代码)。
- ResearchComplete 解决的问题:模型怎么"说完成"且代码可靠听懂?自由文本要猜,tool call 是机器可读结构化意图,`any(call["name"] == "ResearchComplete")` 一行判定。

### 3. reducer —— 声明在数据上的合并协议

- 写在 `state.py` 字段注解第二槽:`Annotated[list[...], operator.add]`。
- 定义:合并函数 `f(旧值, update值) → 新值`。我们不写它、不调它——**声明在第 0 层,生效在引擎里,节点毫不知情**。
- 两种语义同存于一个 update 字典:有 reducer 的字段交**增量**(`[response]`),没 reducer 的字段交**全量新值**(`state.get(...) + 1`)。
- reducer 必须是纯函数:`iconcat`(原地 `+=`)会污染 checkpointer 的历史快照;用 `add`。
- 单线循环里"覆盖 + 全量"与 reducer 等价;**并发 fan-out 下不等价**——R3 多分支同一 superstep 写同一字段,无 reducer 直接 `InvalidUpdateError`。reducer 是并发写入的合并协议,不是语法糖。约束优于自觉(呼应 stage2 capstone)。

## 三、机制细节(踩坑收获)

- **函数内赋值 = 局部变量判定**:对 `configurable_model` 赋值会遮蔽全局(连测试 monkeypatch 的假模型一起遮蔽)。链条起点引用全局,结果存新名字。
- **三层衣服每层返回新对象**:bind_tools/with_retry/with_config 都不改原对象——全局裸机保持干净,测试才能换假模型。
- **tool_calls 元素是 dict**(LangChain `ToolCall` TypedDict,统一各 provider 形状):`call["name"]` / `call["args"]` / `call["id"]`。
- **请求单与回执单**:请求侧编号叫 `id`,回执侧 `ToolMessage(tool_call_id=...)` 把结果钉回请求;provider 按 id 配对不按顺序;悬空调用(有请求无回执)的历史会被 API 拒收。
- **错误也是 observation**:execute_tool_safely 把异常转成字符串喂回模型,让模型自己换招——一次工具故障不终结研究。
- **计数点 × 检查点 = 预算松紧**:`tool_call_iterations` 在 researcher +1(数模型调用轮数,非工具执行数——名不符实,诚实名字是 max_react_iterations);检查在 researcher_tools 执行工具**之后**——最后一轮结果不浪费、历史无悬空。计数挪到检查同节点会 off-by-one 松一格。
- **state 放数据,不放能力**:工具是活对象(闭包/连接)不可序列化,不进 state;重复 get_all_tools 的正确修法是 utils 层记忆化(见 findings)。

## 四、调用链分层(自底向上)

```
第4层  tests/test_r1.py        假模型从顶上按门铃
第3层  deep_researcher.py      唯一"动词层":节点 + compile
第2层  utils.py                工具箱(import state 的 ResearchComplete)
第1层  configuration.py / prompts.py   参数与话术,互不依赖
第0层  state.py                地基:纯数据形状,项目内零依赖
```

运行时:引擎收到 Command → ①按 update 改状态(reducer 此刻被调)→ ②按 goto 跳节点。**你的代码写政策,引擎是执行者**。

## 五、diff 复盘结论

刻意简化(欠条):早退不查原生 websearch(Tavily 用不上)/ 无 api_key+tags 注入(R5)/ 编译未传 `output=ResearcherOutputState, config_schema=`(R2 主角)。

真差异辩论:
1. **重复 get_all_tools**:低危缺陷——R1 无所谓,源码配 MCP 后每轮 2 次真 I/O;修法在 utils 层记忆化(按影响工具箱的配置字段做 key),不动 state 不动节点;源码"无状态重取换简单性"可辩护但配 MCP 后不划算。→ 记入 R5 findings。
2. **早退轮计数虚高 1**:无害(早退后计数不再被比较),但证明计数器数的是轮数不是工具数。
