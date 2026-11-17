# Changelog

## 0.1.0-layer0 — 2026-11-17

### Added

- 空包骨架：`interfaces` / `core` / `config` / `llm` / `agent` / `tool` / `memory` / `safety` / `session` / `ui` / `utils`
- `pyproject.toml` 依赖与 Ruff 占位
- 冻结数据根 / 记忆根配置约定（`CODE_AGENT_HOME`、`CODE_AGENT_MEMORY_ROOT`，默认仓库 `.data/`，不使用用户主目录）
- `docs/glossary.md`、`docs/learning-notes/L0.md`
- L0 入口 `main.py`（仅打印，无 LLM）
