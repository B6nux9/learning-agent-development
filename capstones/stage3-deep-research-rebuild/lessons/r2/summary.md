# R2 · 压缩与上下文隔离 —— 总结

> 2026-08-13/14 · Windows 端 · ODR 复现专题第三课

## 交付物

- `state.py`:ResearcherOutputState(BaseModel,出墙滤网)
- `deep_researcher.py`:子图编译加 `output_schema`/`context_schema`(用户自行按 deprecation 警告升级参数名);compress_research 真实现(模式切换 + 3 次重试 + token 截断 + 降级兜底)
- `utils.py`:remove_up_to_last_ai_message(用户写)、is_token_limit_exceeded(源码拷,给现成)、get_all_tools 按 `search_api` 配置切 Tavily/fake(用户写)
- `configuration.py`:compression_model 对 + search_api 字段(给现成)
- `tests/`:10/10 绿——R1 四条改道 raw_notes 审计通道,R2 新增防火墙/压缩/韧性×3/开关共 6 条;FakeChatModel 升级支持剧本抛异常
- `tests/smoke/smoke_r2.py`:**researcher 子图首次真跑**(DeepSeek + Tavily),压缩稿结构完整,raw_notes 32,138 字符留墙内

## 教学模式变更(本课起生效)

1. **分组交付**:用户明确要求不被 10 个 TODO 淹没——改为 A 防火墙(2)→ B 压缩(2)→ C 韧性(2)→ D 真搜索(1)四组,每组先讲"调用链定位",过一组开下一组。体验良好,R3 沿用。
2. **对话零 diff**:用户反馈文件编辑过程严重伤害对话可读性——批量文件改动全部改走后台 agent,教学文本集中成篇。已入长期记忆。

## 过程实录(如实)

- **A 组**:两 TODO 一次过;用户主动按 deprecation 警告把 `output=`/`config_schema=` 升级为 `output_schema=`/`context_schema=`,并追问 TypedDict vs BaseModel 的选型理由(答:pydantic-at-the-edges)。
- **防火墙的连锁反应**:R1 四条测试因偷看内部字段全灭(KeyError/StopIteration)——借机上了"边界同时约束消费方和测试"一课,断言改道 raw_notes 审计通道后复活。
- **B 组**:R2-3 一次过;R2-4 的 raw_notes 类型链断裂(在 list 上取 .content)——用"由内向外标类型"方法教学,用户求证正确写法后修复。
- **C 组**:R2-6 用户一次写对(纯函数、边界、兜底全中);**R2-5 用户要求教练代写**——如实照办并当场摊牌两个 ⚠️(原地 append 污染 / 嗅探传参错位),代写债在 quiz Q2 验证消化。
- **D 组**:R2-7 一次过(惰性构造在分支内);smoke 首跑即成功,输出成为 Q3 的活教材(3 轮预算 5 次搜索)。
- **quiz 4/4 亲手一次过**,全部带机制带行号;Q4 主动回答了"bug 为何在上游存活"这个未问的问题。与 R1 quiz(讲评代过)对比,推导能力跃升明显。

## 与源码的差异总账

**我们更好(2 处,均为状态/参数正确性修正)**:①模式切换拼新列表 vs 源码原地 append 污染 state(538 行);②token 嗅探传 compression_model vs 源码传 research_model(569 行,异构 provider 下误判致必死)。

**源码更强(欠条)**:自研 tavily 工具带逐页摘要管线(R4 模型分工时算账);SearchAPI 枚举化管理(R5)。

**findings 池(R5 汇总)现四条**:or True(334)、原地 append(538)、嗅探错位(569)、max_react_tool_calls 名不符实。

## 门禁三条

- ① 环境可复现:无新依赖(langchain-tavily R0 已入);key 走 .env;单测默认离线 ✅
- ② pytest 10/10 绿,含 happy 与 failure path(预算强退、工具炸、重试耗尽、降级存活)✅
- ③ 无调试残留:grep 拖尾空格/脚手架注释为零 ✅

## 面试可引用(本课新增,详见 interview-notes 十四)

context isolation 落地三要素 / pydantic-at-the-edges / 模式切换双保险与截断相容 / 错误分类学与降级不抛 / 嗅探必须传实际干活的模型(含上游存活三层掩体)/ 预算单位=模型回合≠工具次数。
