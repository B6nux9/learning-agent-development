# R3 · Quiz(考推导不考背诵)

> ✅ **状态:已关账**(2026-08-18 亲答,5/5 全过)。代写债(R3-8/10/11)经 Q1-Q4 推导验证消化,销账。
> 出题侧重:R3-8(二次代写)、R3-10、R3-11(代写)三段——代写债随卷验收。
> 答题规矩:**说结论必带机制**,鼓励带行号引证。

---

## Q1(R3-8 债 · gather 与 zip 的对齐契约)

fan-out 段用 `zip(research_results, allowed_conduct_research_calls)` 组装回礼。

a. 三张派活单并发执行,完成顺序是 乙→丙→甲(乙最快)。`research_results` 里的顺序是什么?凭什么?
b. 如果有人把 `asyncio.gather` 换成"谁先完成先收谁"的 `asyncio.as_completed` 风格收集,这段代码会发生什么?错误会在哪一层暴露——Python 报错、provider 报错、还是静默出错?哪种最危险?

## Q2(通道分工 · 为什么成果走两条路)

`compressed_research` 装进 ToolMessage,`raw_notes` 只进 state。

a. 两条通道各自的读者是谁?把 raw_notes 也塞进 ToolMessage 会破坏 R2 的哪个设计?具体破坏机制是什么?
b. 回礼那行 `.get("compressed_research", "Error synthesizing research report: ...")` 的兜底文案,在什么真实场景下会被触发?(提示:R2 的重试循环,三连败之后防火墙送出来的 dict 长什么样?)

## Q3(R3-10 债 · 超发教育的两层道理)

预算 2,模型一轮派了 5 张 ConductResearch 单。

a. 后 3 张单"活不干",为什么 ToolMessage 回执一张都不能少?少了一张,**什么时候**、**谁**会报错?
b. 回执文案里为什么要把预算数字(`{max_concurrent_research_units} or fewer`)明说给模型?对比"沉默丢弃后 3 张"和"回执只说 Error 不说数字",三种做法下模型下一轮的行为分别会怎样?
c. 反向推导:如果把超发处理从"裁剪+回执"改成"直接抛异常炸掉本轮",现有代码里**哪一段会接住它**?最终行为是什么?这算优雅降级还是事故?

## Q4(R3-11 债 · findings① 与前置检查)

a. 源码 334 行:`if is_token_limit_exceeded(e, configurable.research_model) or True:`。论证这里的嗅探为什么是死代码;再论证:如果删掉 `or True` 让嗅探真的生效,**非 token 类异常**会走到哪里去?后果是什么?(这就是复现版选择"诚实写法"的理由)
b. supervisor_tools 前置检查 vs researcher_tools 后置检查:两者交换会各自付出什么代价?(用"一次工具执行的成本"论证,量纲要说清)

## Q5(串联题 · 三重预算的量纲)

R2 真跑时你实证过"设 max_react_tool_calls=3 却发生 5 次搜索"(深度预算管不住宽度)。

a. R3 的三条预算各自管"深度"还是"宽度"?量纲各是什么?
b. supervisor 层的宽度失控(一轮派 20 张单)和 researcher 层的宽度失控(单轮并发 5 次搜索),官方分别用什么手段治理?为什么 researcher 层没有 max_concurrent 切片?(提示:两层"一单位"的成本差多少量级?)

---

## 战绩(答题后填)

| 题 | 结果 | 备注 |
|---|---|---|
| Q1 | ✅ 过 | gather 按位置组装、顺序继承调用列表;三层暴露分析(Python/provider/静默)全中,"协议合法掩护语义错配" |
| Q2 | ✅ 过 | **反驳出题提示前提**:三连败时错误文案经 compress 降级 return 写进值,.get 第二参数仅防 key 缺失(结构保险) |
| Q3 | ✅ 过 | c 超范围发现:异常抛在 gather 后,已执行子图的成果留在局部变量、END 时丢弃——"降级通道用成自毁开关" |
| Q4 | ✅ 过(a 修正) | a 的 NameError 机制属复现版(try 内首次赋值);源码 all_tool_messages 在 try 前初始化,实际是 fall-through→goto supervisor→未应答 id 下轮 400。b 满分:两层互换代价+researcher 前置的悬空 tool_calls 隐患 |
| Q5 | ✅ 过 | 三预算量纲表 + 硬/软治理分野;金句"治理强度对齐单位成本,而不是对齐失控这个词本身" |

## 课中已过的验收追问(不重复计入)

- Group B 验收两问:①R4 忘用 override 信封的三条后果(system prompt 特权位/旧剧本续写压力/永不清场)——**超范围答出,过**;②`[response]` 普通 list 为何在 override_reducer 下照样追加("不出示信封,它就是 operator.add 本人")——**过**。
