# R2 · Quiz

> 状态:**4/4 亲手作答,全部一次过,关账 ✅**(2026-08-14)。
> 与 R1(讲评代过 + 次日变式补账)对比:本轮全部带机制、带行号引证——"说结论必带机制"口令自 R2 起退役。

## Q1:把 raw_notes 从 ResearcherOutputState 删掉,10 条测试哪几条挂?丢掉什么架构能力?

**用户答案(满分)**:挂 6 条,且分出两种挂法——5 条 KeyError(test_r1 的 happy/budget/tool_error + test_r2 的 compress_produces/gives_up 摸不到字段),1 条断言失败(firewall 测试 key 集合不等);不挂 4 条(research_complete、remove 单元、token_retry、search_defaults)逐条说明了原因。架构能力:**降级通道**(压缩失败原料保命)+ 主动补了**可审计性**(墙立后外部观察循环的唯一窗口)。引用了行号与代码注释作证。

**判定**:两种挂法的区分说明在脑内跑了代码;可审计性是未提示的加分项。

## Q2(代写债):截断把尾部模式切换 HumanMessage 剪掉后,重试还能压缩吗?靠什么?

**用户答案(满分)**:能,靠 **system prompt 冗余通道**。完整推导链:双保险识别 → HumanMessage 排在所有 AI 之后必然被剪且不再补回 → 但 messages 在 while 循环内重组,压缩任务书住在 SystemMessage 里每次重试都新鲜。附反事实:若只靠 HumanMessage 单通道,截断会剪掉任务书本身——"这正是双保险的价值"。

**判定**:反事实推理到位,R2-5 代写债经此题验证已消化。

## Q3:max_react_tool_calls=3 为何拦不住 smoke 里的 5 次搜索?怎么真正卡死在 3?

**用户答案(满分)**:两处代码合谋——计数单位是模型回合(researcher 每次发言 +1,不管带几个 tool_calls;DeepSeek 支持并行工具调用,TavilySearch 单 query 接口使模型倾向并发多调)+ 预算检查先执行后检查(踩线回合的搜索照样全部打出去)。两种改法:方案 A `bind_tools(tools, parallel_tool_calls=False)` 对齐预算单位(代价:think_tool 占预算、串行变慢);方案 B 执行侧维护已执行搜索数、裁剪本回合 tool_calls 到余额、**裁掉的补"budget exhausted" ToolMessage**、归零路由去 compress。

**判定**:自发现"工具 schema 反塑模型调用形态";方案 B 同时遵守回执铁律,是其早前"每轮限 10 次"提案的自我修正闭环。

## Q4:嗅探传参 bug 何时无害、何时有害?后果链推到用户看到什么。

**用户答案(满分 + 加分)**:无害两种成因——①同 provider 前缀碰巧对;②前缀不被识别 → provider=None → **全分支嗅探是任何单分支的超集**(本仓库默认 deepseek 前缀正是此种,"零杀伤——这也是 bug 在上游长期没被发现的原因之一")。有害:research=被识别的 provider A、compression=不同 provider B,嗅探锁死 A 分支不再兜底。后果链:B 家超限异常 → A 分支模式全不匹配返回 False → 不截断盲重试 → 同样超长上下文确定性三连败(一刀能救活的场景必死)→ 兜底文案 → **报错字符串被当成研究成果拼进最终报告,且无日志提示"剪一刀就能好"**。

**判定**:主动回答了未问的问题("为什么 bug 能在上游存活"——默认配置掩护 + 异构才触发 + 表象错位三层掩体);影响力量到用户脸上而非异常栈。
