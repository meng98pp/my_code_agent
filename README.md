# my_code_agent

终端编程助手（可安装的 Python 发行包）。当前是 **L0 仓库骨架**：可 `pip install -e .`，尚未对话、调工具或写记忆。

功能语义对齐 `projects/my_claude_code_skills`，代码独立重写。切片只限制**范围**，不降低工程标准。方案见 [`技术总方案.md`](技术总方案.md)。

## 安装

```powershell
cd e:\study\AI_develop\00_python_preview\1_3\code\projects\my_code_agent
pip install -e ".[dev]"
python -m my_code_agent
# 等价：python main.py    或    my-code-agent
```

- Python 3.11+
- L2 起需要环境变量 `API_KEY`（不要写入仓库）
- 可选：`MODEL`（默认将为 `deepseek-flash`）

L0 入口只打印骨架就绪，不访问网络。

导入约定（后续层一律如此）：

```python
from my_code_agent.agent import ...
from my_code_agent.tool import ...
from my_code_agent.memory import ...
```

不要 `import agent`。`agent` / `tool` / `memory` 是发行包内的独立子包。

## 数据根与记忆根（F006，已冻结）

参考实现写死用户主目录（Windows 上通常是 **C:\Users\\...**）。本项目**禁止**把 `Path.home()` 当作默认记忆根。

| 配置 | 作用 | 未设置时 |
|------|------|----------|
| `CODE_AGENT_HOME` | 运行时数据根（会话、审计、用户级 skills/mcp、默认记忆） | `<本仓库>/.data` |
| `CODE_AGENT_MEMORY_ROOT` | 只覆盖记忆树 | `{CODE_AGENT_HOME}/projects/<cwd 转码>/memory` |

L2 将用 `pydantic-settings` 解析；优先级：环境变量 > `settings.toml` > 默认。

```powershell
$env:CODE_AGENT_HOME = "E:\agent-data"
$env:CODE_AGENT_MEMORY_ROOT = "E:\my-memories"   # 可选
```

解析结果若落在 `C:\`，启动失败（单测可用 `CODE_AGENT_ALLOW_C_DRIVE=1`）。`.data/` 已 gitignore。L4 才 mkdir。

## 包边界

```text
my_code_agent.ui
  → my_code_agent.core
    → agent | tool | memory
      → safety | session | llm | config
        → interfaces | utils
```

`agent` 不得依赖 `ui`；`memory` 不得依赖具体 tool 实现。

## 进度

| 层 | 状态 |
|----|------|
| L0 可安装骨架 + src 布局 | 本层 |
| L1 核心接口 | 未开始 |
| L2 起 Agent | 未开始 |
