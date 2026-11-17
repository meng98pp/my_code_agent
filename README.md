# my_code_agent

学习型终端编程助手。第一阶段只搭仓库骨架（**L0**），还不能对话、不能调工具、不能写记忆。

对照方案见 [`技术总方案.md`](技术总方案.md)。功能语义对齐 `projects/my_claude_code_skills`，代码独立重写。

## 要求

- Python 3.11+
- 从 L2 起需要环境变量 `API_KEY`（不要写入仓库）
- 可选：`MODEL`（默认将为 `deepseek-flash`）、`OPENAI_BASE_URL` / 配置文件中的兼容接口地址

```powershell
cd e:\study\AI_develop\00_python_preview\1_3\code\projects\my_code_agent
pip install -e ".[dev]"
python main.py
```

L0 的 `main.py` 只打印骨架就绪，不会访问网络。

## 数据根与记忆根（F006，已冻结）

参考实现把数据写在用户主目录（Windows 上通常是 **C:\Users\\...**）。本项目**禁止**把 `Path.home()` 当作默认记忆根。

| 配置 | 作用 | 未设置时 |
|------|------|----------|
| `CODE_AGENT_HOME` | 运行时数据根（会话、审计、用户级 skills/mcp、默认记忆） | `<本仓库>/.data` |
| `CODE_AGENT_MEMORY_ROOT` | 只覆盖记忆树 | `{CODE_AGENT_HOME}/projects/<cwd 转码>/memory` |

也可在后续层的 `config/settings.toml` 里写 `home` / `memory_root`，优先级：环境变量 > toml > 默认。

```powershell
# 示例：把全部运行时数据放到 E 盘
$env:CODE_AGENT_HOME = "E:\agent-data"
# 可选：只把记忆放到另一棵树
$env:CODE_AGENT_MEMORY_ROOT = "E:\my-memories"
```

启动后若解析出的数据根 / 记忆根落在 `C:\`，应拒绝启动（单测可用 `CODE_AGENT_ALLOW_C_DRIVE=1` 关闭检查）。`.data/` 已列入 `.gitignore`。

L0 只冻结约定，**不会创建记忆目录**。真正 mkdir 在 L4。

## 包边界（L0 起固定）

依赖只允许向外：`ui` → `core` → `agent` / `tool` / `memory` → `safety` / `session` / `llm` / `config` → `interfaces` / `utils`。

`agent`、`tool`、`memory` 必须保持独立目录，彼此不直接依赖对方的具体实现。

## 当前进度

| 层 | 状态 |
|----|------|
| L0 仓库骨架 | 本层 |
| L1 核心接口 | 未开始 |
| L2 起 Agent | 未开始 |
