# my_code_agent

终端编程助手（可安装的 Python 发行包）。当前是 **L3c**：能读写文件，并能 `run_command`（前台超时 / 后台 job）。还没有五档权限和记忆落盘。

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

跑测试请在**本仓库根目录**执行（`tests/__init__.py` 会把 `src/` 加进路径）。当前解释器若已 `pip install -e .`，两种方式都可以：

```powershell
python -m unittest tests.test_l3c_command_policy tests.test_l3c_jobs -v
```

## 数据根与记忆根

| 配置 | 作用 | 未设置时 |
|------|------|----------|
| `CODE_AGENT_HOME` | 运行时数据根 | `<本仓库>/.data` |
| `CODE_AGENT_MEMORY_ROOT` | 只覆盖记忆树 | `{HOME}/projects/<cwd 转码>/memory` |

优先级：环境变量 > `settings.toml`（cwd 覆盖仓库 `config/settings.toml`）> 默认。  
解析到 `C:\` 则启动失败（`CODE_AGENT_ALLOW_C_DRIVE=1` 仅测试用）。L4 才 mkdir。

## 模型采样与思考

改仓库内 [`config/settings.toml`](config/settings.toml)，或用环境变量覆盖。未写的项不传给 API，用模型默认值。

| 配置 | 环境变量 | 说明 |
|------|----------|------|
| `temperature` | `CODE_AGENT_TEMPERATURE` | 0～2，越低越稳 |
| `top_p` | `CODE_AGENT_TOP_P` | 核采样；一般不要和 temperature 一起改 |
| `max_tokens` | `CODE_AGENT_MAX_TOKENS` | 单次回复上限 |
| `timeout` | `CODE_AGENT_TIMEOUT` | 请求超时（秒） |
| `thinking` | `CODE_AGENT_THINKING` | `true` / `false`，或 `low` / `medium` / `high` / `max` |

`build_agent` 会把这些填进 pydantic-ai 的 `model_settings`。

## 进度

| 层 | 状态 |
|----|------|
| L0 可安装骨架 | 完成 |
| L1 核心接口 | 完成 |
| L2 无工具对话 | 完成 |
| L3a 注册表 + read_file | 完成 |
| L3b write/edit + undo | 完成 |
| L3c shell + jobs | 本层 |
| L3d 起五档权限 | 未开始 |
