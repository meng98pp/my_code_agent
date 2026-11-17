"""``python -m my_code_agent`` 入口。L0 仅打印骨架状态，不访问网络。"""

from __future__ import annotations


def main() -> None:
    print("my_code_agent L0: 仓库骨架就绪。设置 API_KEY 后从 L2 起才能对话。")


if __name__ == "__main__":
    main()
