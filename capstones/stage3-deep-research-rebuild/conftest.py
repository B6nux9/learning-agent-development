"""pytest 入口配置:把 src/ 加入 sys.path,让测试能 `from deep_research import ...`。

跑法(在本目录下):uv run pytest tests/test_r1.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
