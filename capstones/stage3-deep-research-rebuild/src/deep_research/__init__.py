"""ODR 复现:langchain-ai/open_deep_research 的挖空重建。

文件布局镜像源码(便于逐文件 diff 对照),按课程进度逐课添加:
  R1 → state.py(部分)+ deep_researcher.py(researcher 子图)
  R2 → utils.py(部分)
  R3 → state.py / deep_researcher.py(supervisor 子图)
  R4 → deep_researcher.py(主图)+ prompts.py(从源码复制)
  R5 → configuration.py
"""
