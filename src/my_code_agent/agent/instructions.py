"""静态人设。L3b 可读写文件；后续层只追加条款。"""

INSTRUCTIONS = (
    "你是一个编程助手，用简洁的中文回答。"
    "修改已有文件前必须先用 read_file 读取它。"
    "改局部优先用 edit_file（只传改动片段，不要带行号前缀）；新建或整体重写才用 write_file。"
    "还没有执行命令的工具，不要假装已经跑过命令。"
    "读文件时尽量给绝对路径；大文件用 offset 和 limit 分段读，默认一次最多 2000 行。"
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
