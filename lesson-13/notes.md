# L13 · 可观测性、成本与延迟 + API 调用层可靠性

> 状态：讲授中（2026-08-10 开课）。notes 随讲授增量更新，封版才出 summary.pdf。
> JD 对标：拼多多 JD 点名「成功率、延迟、Token 消耗、业务转化率」；API 重试/超时/限流是 L1–L5 缺口 4（生产必备）。
> L13.5 Agent Harness 专题另起一次坐下（JD2 整篇，Claude Code 锚点），不塞进本节。

## 本节地图（三块 + 一条主线）

主线一句话：**生产 agent 的三个灵魂拷问——它挂没挂（可靠性）、它在干嘛（可观测性）、它值不值（成本/延迟）。**

| 块 | 内容 | 回扣 |
|---|---|---|
| §1 API 调用层可靠性 | 失败分类学 · 超时 · 重试(指数退避+jitter) · 429 限流 · 可重试 vs 不可重试 | L3 只学了**工具报错回传模型自愈**；API 本身挂了模型根本收不到——这是另一层。app.py 的 503 兜底、reflect 的 fail-open 是雏形 |
| §2 可观测性深化 | trace/span/generation 三级结构 · 裸 SDK 版手动埋点 · metadata(session/user) · score 回流(挂 rubric_judge) | Langfuse 已接 LangGraph 版(callback 自动)；L5 金句「验收看 tool_calls 不看话术」的体系化 |
| §3 成本与延迟 | token 成本核算与大头定位 · 模型分层 · P50/P95 · 延迟分解与优化杠杆 | L6 上下文=预算表 · L4 路由用非思考模型 · L8 llm_calls 度量 |

作业预告：**盖一个生产级 `llm_client.py`**（超时/重试/退避/429/错误分类/调用指标），单文件 + 测试，封绿后一刀接进 capstone 三处裸调用。

## §1 API 调用层可靠性

### 开场靶子（capstone 现状）

```python
# agent.py:211 / policy_rag.py:91 / reflect.py:90 —— 三处都是这样的裸调用
resp = client.chat.completions.create(model=..., messages=..., tools=...)
```

**练习 1（讲授前先自己想）**：这一行在生产环境有几种"死法"？逐条列出来，
并对每条标注——重试有用吗？该等多久重试？还是压根不该重试？

**用户首答（2026-08-10）**：列出①运行端网炸②LLM 服务器网炸③模型字段不存在④messages/tools 不合法，
结论"重试大概率都解决不了，尽快回复"。判卷：③④对（4xx fail fast，L6 的 400 经验迁移正确）；
①②错——把"网炸"想成永久故障，漏了**抖动才是常态、重试是第一救命稻草**；漏了超时/429/5xx 三大死法。

### 失败分类学（三箱 + 特殊箱）——分类决定动作（L3"错误也是信息"下沉到传输层）

| 箱 | 包含 | 动作 |
|---|---|---|
| **A 可重试（瞬时）** | 网络抖动、超时、5xx | 指数退避重试（1s→2s→4s，设上限），耗尽后优雅降级 |
| **B 不可重试（永久）** | 400/401/403/404 | fail fast + 日志/告警。重试只会重复同一个错 |
| **C 限流** | 429 | 可重试但**必须等**：尊重 `Retry-After` 头；没有就指数退避 |
| **D 200 但内容坏** | 空 content（L4 亲历）、JSON 不是 dict（L12 亲历） | 应用层校验 + 可选重问一次，与网络重试是两套机制 |

关键细节（面试必问级）：
- **429 立刻重试 = 火上浇油**：服务端已过载，万人齐重试=重试风暴；整点齐重试=同步波峰 → **指数退避 + jitter**（AWS 经典）。
- **重试的隐含前提是幂等**：超时后不知道服务端执行没执行。chat 调用重试=多花钱，安全；
  若包的是 process_refund，超时重试=退两次款 → capstone block4 的幂等防重复正是这条防线。
- **超时最阴**：不设 timeout 不是慢，是**僵**——请求堆积拖垮上游。生产铁律：网络调用必设 timeout。

### 生产视角（不造轮子而不自知）
`openai` SDK 内置：`max_retries=2`、指数退避+jitter、尊重 Retry-After、只重试 连接错误/408/429/5xx，默认 `timeout=600s`。
- 生产没人裸写 retry 循环（SDK 内置 / tenacity）。
- 但默认值不合身：600s 超时对客服=灾难；重试耗尽后的**优雅降级**（转人工/503）SDK 管不了。
- → 作业 = 包一层 `llm_client.py`：错误分类 · 自定义超时/重试预算 · 每调用指标（延迟/token/重试数，喂 §2 可观测）· 耗尽降级。
  自己写分类与退避是为了懂机制（白板题）。

### 检查题结果（2026-08-10）：两题全对 + 一个高光
- (a)(c) 满分；第 2 题答出"稍后重试 or 回复'人工'"= 优雅降级，正确。
- **⭐高光 (b)**：用户自己答出"429 等 20s 在客服场景应直接给用户回复"→ 提炼成金句：
  **重试预算必须服从延迟预算**——重试上界不是次数，是用户还愿意等的时间。
  推论：deadline 总预算做成调用方传参（对话路径小预算 / eval 跑批大预算）。（进 interview-notes 待办）
- 补讲黄金法则：**降级路径不能依赖刚挂掉的依赖**——降级回复必须硬编码模板，不能再调 LLM 生成。
  capstone 已合规（HANDOFF_REPLY 写死、escalate 纯本地），面试话术"降级路径对 LLM 零依赖"。

### 作业蓝图（带着盖楼，2026-08-10 已开工）
`lesson-13/homework/llm_client.py`（用户从空文件写）+ `test_llm_client.py`（用户自写，fake 零网络）。
5 块由内向外：① Category+classify 分类（地基）② compute_backoff 指数退避+full jitter（纯函数）
③ chat_with_retry 主循环 v1 ④ deadline 预算 + Retry-After 裁决（用户 (b) 洞察变代码）
⑤ CallMetrics + LLMUnavailable（指标喂 §2）。封绿后下次坐下反哺 capstone 三处裸调用 + run() 降级出口。
- 埋的坑：① classify 里 RateLimitError 是 APIStatusError 子类 → isinstance 顺序（回扣 L12 except 顺序坑的反向）；
  ② 块 3 附近的**分层重试放大**（SDK 内置 max_retries=2 × 自己重试 3 = 隐形 6 次，须关内层 max_retries=0，重试只在一层做）。
- **块 1 classify 封绿（2026-08-10）**：冒烟 5/5。初版三连翻车=①`openai.error` 0.x 老 import(根因:交前没跑过,教训"写完第一件事是跑")
  ②`http_status` 0.x 属性(v1=`status_code`;更阴:潜伏到第一个真 5xx 才炸→"错误处理路径的 bug 只在出错时爆炸,必须用测试触发")
  ③整段粘贴残留死代码(第二定义静默覆盖第一,第一份恰是无 return 函数)。修复后干净。
  isinstance 顺序陷阱躲过+答对本质,术语钉准:**父接得住子,子接不住父**(与 L12 except 坑同图两方向)。
- **块 2 compute_backoff 封绿**：一行 `random.uniform(0, min(cap, base*2**attempt))` 正确;实测 cap 兜住+撒满区间。
  jitter 下界=0 的问题答对一半(窄带集中撞车),补齐另一半:**便宜一次尝试买"早恢复"彩票**(抖动常几百 ms 就过,0.064s 重试若中省整轮等待;AWS 仿真 full jitter 综合最优)。
- **块 3 chat_with_retry v1 封绿（2026-08-10）**：用户写的循环一次冒烟全过(3/3)。
  加分点：耗尽判断放在 sleep **之前**(省掉"白睡最后一觉"的 8s 延迟)。
  缺件(计数 fake 冒烟+放大题)由**教练代写/代讲**(用户点名"你来写后续";fake=测试脚手架属教练职责)。
  fake 设计点：哨兵用 `object()`(身份唯一,`is` 可证原物,回扣 escalate 测试 is/== 坑)；
  `time.sleep` 借了 finally 还(=monkeypatch 的手工版)。
  **分层重试放大(讲授,面试题库)**：外层 4 尝试 × SDK 内层默认 3 = 最坏 12 个 HTTP 请求。
  三重危险=自制重试风暴/deadline 失真/日志对不上账。修法金句：**重试策略必须有唯一属主,只在一层做**
  → `OpenAI(max_retries=0, timeout=8.0)` 内层缴械+钉死 600s 默认超时。通用规则：层层相乘,查事故先数有几层。
- **块 4 封绿（2026-08-10，教练代写，用户点名）**：deadline_s 预算 + Retry-After。冒烟 6/6。
  ⚠️ 交接事故：用户把契约贴成第二个同名 def(空体)静默覆盖 v1=块1死代码教训当场重演,已借机点破
  "版本历史是 git 的活不是文件的活"。
  设计决定(已讲)：①`_retry_after_seconds` 单拎(脏活隔离,"别信外部输入哪怕来自服务端")
  ②预算检查写一次,两种 wait 汇流后过闸 ③monotonic 防墙钟回拨(注释写约束不写行为)。
  已出 2 道理解验证题(待答)：⑥为何 calls==1 不是 0 / deadline 管不到哪种卡住(答案:请求本身挂起,靠 client timeout=8.0 补)。
- **块 4(重写)+块 5 完工（2026-08-10，均教练代写，用户点名"你来完成"）**：冒烟 6/6，commit 8d0d517。
  用户重写块 4 中途改为委托（曾布置掏空重写、参考版存 git 26568b9）。
  两道验证题用户答对：⑥calls==1 因预算只裁决"等待"不裁决"开始" / deadline 管不到请求挂起→client timeout 补。
  块 5 设计决定（已讲，可当面试题）：①**失败也要记账**=异常携带 metrics（最贵的调用是失败的,只记成功→延迟大盘漏最差样本,同 L8 度量陷阱）
  ②try/except/else(try 块最小化,return 在 else) ③**FATAL 不翻译**："把400包进服务不可用=把该修代码的问题伪装成该等待的问题,bug 要炸给人看不是兜给用户"
  ④`from exc`→`__cause__` 保留元凶,翻译异常不销毁证据(冒烟③⑥有断言版答案) ⑤getattr 双层防御取 usage(D 箱落地)。
- **测试正式化完成（2026-08-10，commit cd06bff）：13 passed**。过程：用户自写初版→**收集期 ImportError 0 条执行**
  （llm_client.py 还被回退成空桩=编辑器旧缓冲事故,块4/5实现一度消失,git restore 找回——"版本历史是 git 的活"再验证）。
  用户版三组病（已复盘）：A 挡路（SENTINEL 不在模块层/幽灵 import wsgiref/req≠REQ/SENTINELa typo→**又是没跑就交,本节第3次**）
  B 语义（没按现行契约解包 tuple / `deadline=` 拼错被 **kwargs 静默吞 / 退避下界写 0.1=~10% flaky——**flaky test 比没有更糟,教团队"红了重跑"**）
  C 灵魂缺失（sleeps fixture 注入 6 次断言 0 次 / 无 calls / 无 __cause__ / 无 metrics——"它红的时候,能红在你关心的事上吗"）。
  教练重写版新增**行为文档测试** test_kwarg_typo_is_swallowed（把今天现场撞的 kwargs 吞 typo 坑钉成规格）；
  compute_backoff 边界测试改抽样×4 攻位精确 `0<=`。llm_client 删掉 __main__ 冒烟（职责移交正式测试,门禁3）。
- 当前断点：**作业代码全部完工（llm_client 13 测试绿）**。下一步（按序）：
  ①**反哺 capstone**（⚠️尽量拉回用户亲手写）：三处裸调用换 chat_with_retry + client 构造加 max_retries=0/timeout=8 + run() 捕 LLMUnavailable 走降级
  ② §2 可观测性深化(Langfuse 手动埋点/score 回流) ③ §3 成本延迟讲授 ④ quiz ⑤ 封版三门禁+summary.pdf+interview-notes(「十四」草稿见上方金句)。
- ⚠️ 教学观察(下 session 注意)：本节后半用户连续三次委托代写(块4缺件/块4重写/块4+5)。已用"验证题+读代码审设计"保底学习量,
  但**动手量明显低于既往节奏**——反哺 capstone 与测试正式化两步应尽量拉回用户亲手写,至少让他做接线与断言。
