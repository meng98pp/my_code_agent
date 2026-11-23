"""``python -m my_code_agent``

也可直接 ``python src/my_code_agent/__main__.py``：此时解释器不会把
``src/`` 放进 ``sys.path``，下面在导入前补上。
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    src_root = Path(__file__).resolve().parents[1]
    src_str = str(src_root)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

from my_code_agent.ui.cli import main

if __name__ == "__main__":
    main()
