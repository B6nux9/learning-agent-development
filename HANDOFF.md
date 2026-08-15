# HANDOFF · 换机交接文档

> 生成日期:2026-08-15。读者:另一台电脑上的新 Claude session + 用户本人。
> 用途:在新机器上无缝接续 open_deep_research(ODR)挖空复现课程,当前停在 **R3 Group A**。

---

## 一、环境搭建

1. Clone 本仓库后,进入 `capstones/stage3-deep-research-rebuild/`。
2. 安装依赖:`uv sync`(仓库用 uv 管理;若无 uv 先 `pip install uv`)。
3. 配置钥匙:在 capstone 目录建 `.env`,写入两把钥匙:
   - `DEEPSEEK_API_KEY`(模型调用)
   - `TAVILY_API_KEY`(真搜索)

   **钥匙绝不入库**——`.env` 已在 gitignore 里,也绝不许粘进对话。日常测试**默认离线**(FakeChatModel + fake_search),不需要任何钥匙;只有 `tests/smoke/` 真跑冒烟才用。
4. 验证环境:

   ```bash
   uv run pytest tests/test_r1.py tests/test_r2.py -v
   ```

   应 **10/10 绿**。`tests/test_r3.py` 当前 import 红灯**属预期**,见下文第四节。

---

## 二、课程进度总览

| 课 | 状态 | Commit |
|---|---|---|
| R1 · researcher 子图 ReAct 循环 | ✅ 封版 + quiz 变式题 4/4 关账 | `c4cc8c4` / `68b8cef` |
| R2 · 压缩 + 防火墙 + token 韧性 + Tavily 真跑 | ✅ 封版(10 测试绿 + 冒烟通过 + quiz 4/4 亲答满分) | `b4be0b2` |
| **R3 · Supervisor 与并发派活** | 🔶 **Group A 骨架已交付,用户正在填** | 本 commit |
| R4 / R4.5 / R5 / R6 | ⬜ 未开 | — |

**findings 池**(源码问题,R5 汇总成 findings.md):① `deep_researcher.py:334` 的 `or True`;② 538 行原地 `append` 污染 state;③ 569 行 `is_token_limit_exceeded` 错传 research_model(应为 compression_model);④ `max_react_tool_calls` 名不符实(计回合不计调用次数)。

---

## 三、R3 Group A 讲义精要(已在旧机器上讲完,勿重复开讲)

### 调用链定位

supervisor ⇄ supervisor_tools 是 researcher ⇄ researcher_tools 的**镜像 ReAct 骨架**,但有三个关键差别:

1. **supervisor 的工具零真实执行**——`[ConductResearch, ResearchComplete, think_tool]` 全部按名字拦截转手:think_tool 内联造 ToolMessage;ConductResearch 转手变成 `researcher_subgraph.ainvoke(...)`。这是 R2 防火墙的下游回报:supervisor 只见 `compressed_research` 提炼稿,不见 32k 垃圾山。
2. **前置检查 vs 后置检查**——researcher_tools 后置(先执行后查预算,"厚道");supervisor_tools 前置(进门先查三个退出条件)。因为这一层一次"工具执行"= 整个 researcher 子图跑一遍,成本结构变了,检查时机跟着变。
3. **system prompt 来源不同**——researcher 在节点内自己拼 SystemMessage;supervisor 的 system prompt 由 R4 主图 write_research_brief 用 override 信封整体写入 state,节点内不拼。R3 测试手动 seed。

### 三个 TODO(都在 `src/deep_research/state.py`)

- **R3-1 `override_reducer`**:R1 quiz"写 0 等于没写"的官方解法——在数据通道里内嵌控制协议。`{"type": "override", "value": X}` 信封 → 旧值整体替换为 X;其他任何值 → `operator.add` 老路。代价:字段从此不能安全存放恰好长得像信封的普通数据(协议占用数据空间)——**quiz 素材**。
- **R3-2 `ConductResearch`**:带字段的协议工具(对比 ResearchComplete 空壳)。`research_topic: str` + `Field(description=...)`,description 是给模型的填表须知(要求单一课题 + 至少一段话高细节),源码 `state.py:15-19` 照抄。
- **R3-3 `SupervisorState`**:TypedDict,5 字段——`supervisor_messages` / `notes` / `raw_notes` 挂 override_reducer,`research_brief: str`,`research_iterations: int`。

### 当前红灯属预期

骨架已把 ResearcherState / ResearcherOutputState 的 `raw_notes` 升级为挂 `override_reducer`(源码同款),但函数本体是 R3-1 的作业——**用户填完 R3-1 之前,import state 会失败**,这是故意的教学设计,不是 bug。

---

## 四、作业与验收(接手后第一件事)

1. 用户依次填 R3-1 → R3-2 → R3-3(骨架 TODO 注释里有完整契约)。
2. 验收:`uv run pytest tests/test_r3.py -v` 应 **8 绿**(3 reducer + 3 ConductResearch + 2 SupervisorState),且 test_r1 / test_r2 回归不破。
3. 之后按组推进:**Group B**(supervisor 节点)→ **Group C**(拦截与 fan-out)→ **Group D**(预算与超发教育)。源码参照 `deep_researcher.py:178-363`。

---

## 五、新 session 接续话术

在新机器上对 Claude 说:

> 继续 ODR,读 HANDOFF.md 和 REBUILD-PLAN.md F 区。R3 Group A 骨架已交付,我填完了/正在填。

### 课程规约(新 session 必须遵守)

- **分组交付**:TODO 不一次全给,按组走,每组开讲先讲"这段在调用链的哪一环"。
- **对话整洁**:批量文件改动走后台 agent,不在对话里刷 diff;pytest 输出留在对话。
- **封版流程**:lessons/rN/{notes,quiz,summary}.md + summary.pdf → interview-notes.md 追加 → REBUILD-PLAN.md F 区断点 → PROGRESS.md 状态行(append-only)→ commit(`R<N> 封版: ...` / `进度: ...`,尾行 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`)→ push。
- **不抢跑**:下一课只在用户明说"开始 RN"后才开工。
- **quiz 考推导不考背诵**:未过不硬推,欠账记入 F 区下次关账。
- **语言**:对话中文,代码/术语英文。

---

## 六、关键文件地图

| 文件 | 作用 |
|---|---|
| `capstones/stage3-deep-research-rebuild/REBUILD-PLAN.md` | 课程总纲,**F 区 = 断点账本**(每次封版写入下一课作业指令) |
| `PROGRESS.md`(仓库根) | 全课程进度流水,append-only |
| `interview-notes.md`(仓库根) | 面试弹药库,「十四」节 = 本 capstone 的 R1/R2 条目 |
| `capstones/.../lessons/r1/`, `lessons/r2/` | 各课讲义/quiz/总结 + PDF |
| `capstones/.../src/deep_research/` | 复现主体(state / configuration / prompts / utils / deep_researcher) |
| `capstones/.../tests/` | test_r1 / test_r2 / test_r3(Group A)+ smoke/ |
| 源码参照 | 需要本地有一份 [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) clone 用于 diff 对照;旧机器在 `E:\Agent\open_deep_research`,新机器路径自便,告诉 Claude 位置即可 |
