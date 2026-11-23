"""仓库根便捷入口。实现位于 ``my_code_agent.__main__``。"""

from __future__ import annotations

import sys
from pathlib import Path

_src = Path(__file__).resolve().parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from my_code_agent.__main__ import main

if __name__ == "__main__":
    main()
