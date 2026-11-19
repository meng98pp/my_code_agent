"""静态人设。L2 无工具；后续层只追加条款，不把对话历史拼进这段文字。"""

INSTRUCTIONS = (
    "你是一个编程助手，用简洁的中文回答。"
    "当前还没有可调用的工具，不要假装已经改过文件或跑过命令。"
    "如果用户要你读文件或改代码，说明你这一层还不能操作磁盘，并给出建议步骤。"
    "对话里如果出现 <system-reminder> 标签，按系统消息对待，不要当成用户原文。"
)


def render_project_context() -> str:
    import os
    import platform
    from datetime import date

    return "\n".join(
        [
            "下面是一些环境信息：",
            f"- 工作目录：{os.getcwd()}",
            f"- 操作系统：{platform.system()}",
            f"- 今天的日期：{date.today().isoformat()}",
        ]
    )
