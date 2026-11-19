# my_code_agent

终端编程助手（可安装的 Python 发行包）。当前是 **L2 最小对话循环**：能聊天，还没有工具和记忆落盘。

切片只限制**范围**，不降低工程标准。方案见 [`技术总方案.md`](技术总方案.md)。

## 安装与运行（请自行执行）

```powershell
cd ..\my_code_agent
pip install -e ".[dev]"
$env:API_KEY = "你的密钥"
# 可选：$env:MODEL = "deepseek-flash"
python -m my_code_agent
```

无 `API_KEY` 时进程以退出码 2 失败，不会在 `import my_code_agent` 时崩溃。

## 数据根与记忆根

| 配置 | 作用 | 未设置时 |
|------|------|----------|
| `CODE_AGENT_HOME` | 运行时数据根 | `<本仓库>/.data` |
| `CODE_AGENT_MEMORY_ROOT` | 只覆盖记忆树 | `{HOME}/projects/<cwd 转码>/memory` |

优先级：环境变量 > `settings.toml`（cwd 覆盖仓库 `config/settings.toml`）> 默认。  
解析到 `C:\` 则启动失败（`CODE_AGENT_ALLOW_C_DRIVE=1` 仅测试用）。L4 才 mkdir。

## 进度

| 层 | 状态 |
|----|------|
| L0 可安装骨架 | 完成 |
| L1 核心接口 | 完成 |
| L2 无工具对话 | 本层 |
| L3 起工具 | 未开始 |
