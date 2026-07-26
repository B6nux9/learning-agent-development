"""让 pytest 在任意目录下都能 import 本作业的模块（executor / planner / tools）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
