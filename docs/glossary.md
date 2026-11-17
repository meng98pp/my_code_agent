# 领域词汇表（L0 冻结）

后续层实现必须沿用这些词，避免和 finagent「Agent 四层 / 记忆四层」混名。

## 产品

| 术语 | 含义 |
|------|------|
| 编程助手 | 终端里用自然语言驱动读文件、改文件、跑命令的 Agent，不训练模型 |
| 一轮 / turn | 用户一次回车到模型不再调工具（End） |
| 工作区 | 进程当前工作目录，写文件硬卡口的主根之一 |

## 运行时职责（不要叫「记忆四层架构」）

| 术语 | 含义 | 本仓库落点 |
|------|------|------------|
| 编排 | 固定顺序：命令 → 压缩 → 检查点 → @ → 召回 → Agent 循环 | `core/`（L2 起） |
| Agent 循环 | ReAct：模型请求 ↔ 工具执行直到 End | `agent/` |
| 工具 | 模型以 function calling 触发的 Python 函数 | `tool/` |
| 记忆 | 跨会话 Markdown 笔记 + 检索 | `memory/` |
| 权限 / 硬卡口 | 工具执行前的 allow/ask/deny，bypass 也不能越过 deny | `safety/` |

## 记忆分层（只作认知模型，实现仍按对照表 H 节）

| 层 | 含义 | 本仓库落点 |
|----|------|------------|
| 工作记忆 | 当次发给模型的 Prompt 拼装结果，不单独落库 | `agent` 组装的 system + history + reminder |
| 短期记忆 | 本会话可 `/resume` 的对话 | `session/` jsonl 与 compact |
| 长期记忆 | 稳定偏好与项目事实（user/feedback/project/reference） | `memory/` 下 Markdown |
| 语义记忆 | 按当前输入检索若干条再注入 | BM25 + 可选 LLM 挑选，无向量库 |

## 配置（F006）

| 术语 | 含义 |
|------|------|
| 数据根 `CODE_AGENT_HOME` | 会话、审计、用户级 Skill/MCP、默认记忆的根 |
| 记忆根 `CODE_AGENT_MEMORY_ROOT` | 可选覆盖，只改笔记落盘位置 |
| 默认 `.data/` | 仓库内目录，与学习仓同盘；禁止默认使用 `Path.home()` |

## 与参考项目对齐的用户可见名

斜杠命令、工具函数名、五档权限名在后续层保持与参考实现一致（`read_file`、`/memory`、`default`…），便于对照学习。
