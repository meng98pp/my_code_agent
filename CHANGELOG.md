# Changelog

## 0.1.1-layer0 — 2026-11-17

### Changed

- 改为 src 布局可安装发行包 `my_code_agent`（`pip install -e .` / `python -m my_code_agent`）
- 领域包改为子包：`my_code_agent.agent` / `.tool` / `.memory`，不再占用顶层模块名
- 声明工程标准：洋葱只切范围，不切质量；配置预留 `pydantic-settings`

## 0.1.0-layer0 — 2026-11-17

### Added

- 空包骨架与对照方案、词汇表、记忆根配置约定
