# 5 个精选信息渠道（Agent 开发）

互联网信息过载，这里只给 5 个最值得投入的，并标注**适合哪一级、用来学什么**。

### 1. Anthropic《Building Effective Agents》+ Cookbook — 打地基（Beginner→Advanced）
- https://www.anthropic.com/research/building-effective-agents
- https://github.com/anthropics/anthropic-cookbook
- 一手资料里最讲人话的一篇，把 agent 常见模式（prompt chaining、routing、
  orchestrator、评估器）讲清楚，且反复强调「先别上框架」。Cookbook 有可跑代码。

### 2. OpenAI / DeepSeek 官方 API 文档 — 一手资料（全程）
- DeepSeek: https://api-docs.deepseek.com/ （function calling、上下文缓存）
- OpenAI: https://platform.openai.com/docs/guides/function-calling
- 写 agent 一定要读一手的 tool use / function calling 文档，二手教程常年过时。
  国内模型多兼容 OpenAI 接口，两边对着看。

### 3. LangGraph 文档与示例 — 看真实工程用法（Intermediate→Advanced）
- https://langchain-ai.github.io/langgraph/
- 到了「多工具编排、状态机、人类介入」阶段再看。前期**先手写**，理解原理后
  再用框架，否则会被框架的抽象绕晕。看它的 how-to 而非营销页。

### 4. 《What We Learned from a Year of Building with LLMs》— 深度实战经验（Advanced）
- https://applied-llms.org/
- 一线团队踩坑总结：评估、上下文、成本、幻觉治理。求职面试里能讲出这些细节
  会显著加分。适合有了原型之后回头精读。

### 5. Latent Space（播客/newsletter）— 持续跟进前沿与答疑（全程，按需）
- https://www.latent.space/
- 跟踪 agent 领域最新进展和从业者访谈。不必期期看，作为「保持嗅觉」的信息源，
  遇到具体新技术（如新框架、新模型能力）时回来找对应期。
