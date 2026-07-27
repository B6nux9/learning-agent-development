# 锚点 L8 · smolagents CodeAgent(代码即动作 / CodeAct)

> 机制:v3 三·补一「源码锚点」。有界只读,≤90min,只为答三个引导问题而读。
> 仓库:`reference/repos/smolagents`(浅克隆,不入库),HEAD `e3a5b89`。
> 核心文件:`src/smolagents/agents.py`(1813 行)· `src/smolagents/local_python_executor.py`(1768 行)。
> 读图:`MultiStepAgent`(基类,268)→ `run`(436)→ `_run_stream`(540,主循环)→ `_step_stream`;
> `ToolCallingAgent`(1215,JSON 范式)· `CodeAgent`(1505,CodeAct 范式)。

**一句话总纲**:两个 `_step_stream` 的 docstring 一字不差——
*"Perform one step in the ReAct framework: the agent thinks, acts, and observes the result."*
两种 agent 共用同一个 ReAct 骨架,**区别只在「动」和「看」两步的表示法**。
(呼应 L8:我 L2 手写的 loop 本质就是 ReAct。)

---

## 引导问题 1:两种范式的「想→动→看」各长什么样?

| | ① smolagents 怎么做 | ② 我(L8 executor)怎么做 | ③ 差异原因 |
|---|---|---|---|
| **动(Act)** | `ToolCallingAgent`:`model.generate(tools_to_call_from=...)` → 返回结构化 `tool_calls`[{name, JSON args}](`agents.py:1309`)。`CodeAgent`:`generate` **不传工具清单**,靠 `stop_sequences` + 代码块标签 → 模型返回自由文本夹一段 Python → `parse_code_blobs` 解析 → `self.python_executor(code)` 扔进沙箱执行(`1677/1708/1726`) | JSON tool-calling:模型返回 `tool_calls`,我逐个 `_execute_tool(name, args)` | 我的范式 = ToolCallingAgent。CodeAgent 把「动作」从「选一个具名工具+填 JSON」换成「写一段任意 Python」 |
| **看(Observe)** | ToolCalling:工具返回值 `str()` 化成 observation。CodeAgent:observation = 代码的 **stdout(执行日志)+ 最后返回值**(`1733/1753`) | 工具执行结果(成功 JSON / error JSON)回传 | CodeAct 的「看」是**代码执行产物**,不是单个工具返回 |
| **谁承担多步编排** | ToolCalling:每步结果**回传模型**再决定下一步 = **一次 LLM 往返/步**。CodeAgent:循环/算术/A的输出喂B **全写在一段代码里**,Python 一次跑完,模型不为中间步骤被重唤醒 | 每个工具调用一次往返(loop 涌现链式) | **CodeAct 把「受益于循环与组合的中间步骤」从 LLM 往返下沉到一次代码执行** |

**扇出算例**(订单列表逐个乘汇率再求和):ToolCalling 需 N+ 次往返(数据依赖的链式,并行也省不了——`ThreadPoolExecutor`@`1426` 只能省彼此无关的调用);CodeAgent 一句 `sum(o['amount']*rate for o in get_orders())` 一步完。

---

## 引导问题 2:代码即动作的代价?

| 维度 | ① smolagents 怎么做 | ② 我(JSON 范式)的情况 | ③ 差异原因 |
|---|---|---|---|
| **安全** | 执行 LLM 生成的任意代码 → 攻击面近乎**无界**(注入可写 `import os;os.system(...)`)。防线:`local_python_executor` 不是 `exec()`,是**自走 AST 的受限解释器**,只放行白名单 import/builtins(挡在 `agents.py:1745` "Import of X is not allowed");不够就换 `executor_type=docker/e2b` 真沙箱 | 攻击面**有界**:模型只能从白名单挑工具+填参,说不出没给的动作 | **约束点从「设计期(能力清单)」挪到「运行期(沙箱)」**:更灵活,更贵、更险 |
| **能力门槛** | 要模型当场写出语法对、API 用对、能跑的 Python → 多一套解析兜底(`AgentParsingError`@`1713`,失败重写) | 填 name+JSON,门槛低 | 强模型吃表达力红利;**弱模型在这里崩坏**(语法错/幻觉函数) |
| **可控/可观测** | 动作 = 一整段代码,工具是沙箱里的函数,模型随便调;调用前**无法** bind 校验;任何异常 → 统一 `AgentExecutionError`@`1750`(**粗粒度单通道**);审计要 parse 代码/看日志 | 单工具粒度:调用前 `inspect.signature().bind()` 校验,调用后 fatal/transient/business **三类分流**,name+args 都在 loop 里 | **CodeAct 用「可控性」换「表达力」**;我 L8 那套精细护栏在 CodeAct 里基本失效 |

**结论**:客服这种要合规、要逐笔审计、要对高危操作二次确认的场景,**更适合 JSON tool-calling 的有界动作**;CodeAct 适合自主长执行、受益于代码组合的编码类任务。

---

## 引导问题 3:显式规划何时帮、何时添乱?

smolagents 三个决定性事实:
1. **planning 默认关**:`planning_interval: int|None = None`(`agents.py:305`)。出厂就是纯 ReAct 不带 planner。
2. **开了也是周期性重规划**,不是 P&E 的一次定死:`(step_number-1) % planning_interval == 0`(`550`)——夹在纯 ReAct 和 P&E 中间。
3. **更新计划时主动「忘掉旧计划」只喂真实观察**:update 分支 `write_memory_to_messages(summary_mode=True)`,注释原话 *"Removing previous planning messages avoids influencing too much the new plan"*(`681-713`)。

| | 结论 |
|---|---|
| **规划何时帮** | 任务步数多、步骤间依赖强、需要让人看懂/审意图时 |
| **何时添乱** | 步骤运行时动态变化 → 计划过时;无变化时重规划 = 纯延迟。**我 L8 Part C 亲历**:P&E 开局把计划写死,扇出任务开局不知道要几路 → 执行错。smolagents 用**周期性重规划 + 只喂真实观察**规避 |
| **为何 pi/Claude Code 不内置 planner,客服常要显式路由** | 编码 agent = 自主长执行、环境实时变,按原计划走大概率出错 → 走一步看一步(ReAct);客服 = 短对话 + 合规 + 要可预测 → 显式路由,给可靠答复 |

---

## 摘进 interview-notes 的(第③栏精华)
- **动作表示法两范式**:JSON tool-calling(有界动作,靠能力清单约束)vs CodeAct(任意代码,靠沙箱约束)。CodeAct 省的是「把循环/组合的中间步从 LLM 往返下沉到一次代码执行」,代价是安全面无界 + 弱模型崩坏 + 可控性退化(细粒度拦截→沙箱+事后日志)。
- **选型判据**:合规/审计/高危二次确认的客服 → JSON tool-calling;自主长执行/代码组合受益的编码 → CodeAct。
- **规划轴**:纯 ReAct ↔ 周期性重规划(smolagents,喂真实观察防锚死)↔ Plan-and-Execute(一次定死,扇出易翻)。
