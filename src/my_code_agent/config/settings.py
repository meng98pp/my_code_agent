"""从环境变量与 settings.toml 加载配置。import 本模块不会校验 API_KEY。"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from .errors import MissingAPIKeyError
from .paths import (
    AppPaths,
    default_home,
    ensure_not_c_drive,
    repository_root,
)


def _toml_paths() -> list[Path]:
    return [
        repository_root() / "config" / "settings.toml",
        Path.cwd() / "settings.toml",
    ]


def _load_toml() -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for path in _toml_paths():
        if not path.is_file():
            continue
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        if isinstance(data, dict):
            merged.update(data)
    return merged


class TomlFileSource(PydanticBaseSettingsSource):
    """优先级低于环境变量：仓库 config/settings.toml，再被 cwd/settings.toml 覆盖。"""

    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self._data = _load_toml()

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        if field_name in self._data:
            return self._data[field_name], field_name, False
        return None, field_name, False

    def prepare_field_value(
        self,
        field_name: str,
        field: Any,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name in self.settings_cls.model_fields:
            value, _key, complex_ = self.get_field_value(
                self.settings_cls.model_fields[name],
                name,
            )
            if value is not None:
                out[name] = self.prepare_field_value(
                    name,
                    self.settings_cls.model_fields[name],
                    value,
                    complex_,
                )
        return out


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    api_key: str = Field(default="", validation_alias=AliasChoices("API_KEY"))
    model: str = Field(default="deepseek-flash", validation_alias=AliasChoices("MODEL"))
    base_url: str = Field(
        default="https://api.deepseek.com",
        validation_alias=AliasChoices("CODE_AGENT_BASE_URL", "OPENAI_BASE_URL"),
    )
    home: Path | None = Field(default=None, validation_alias=AliasChoices("CODE_AGENT_HOME", "home"))
    memory_root: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("CODE_AGENT_MEMORY_ROOT", "memory_root"),
    )
    allow_c_drive: bool = Field(
        default=False,
        validation_alias=AliasChoices("CODE_AGENT_ALLOW_C_DRIVE", "allow_c_drive"),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            TomlFileSource(settings_cls),
            file_secret_settings,
        )


def load_settings() -> Settings:
    return Settings()


def require_api_key(settings: Settings) -> None:
    if not (settings.api_key or "").strip():
        raise MissingAPIKeyError("请先设置环境变量 API_KEY")


def resolve_paths(settings: Settings) -> AppPaths:
    home = (settings.home or default_home()).expanduser().resolve()
    override = None
    if settings.memory_root is not None:
        override = settings.memory_root.expanduser().resolve()
    ensure_not_c_drive(home, allow_c_drive=settings.allow_c_drive, label="CODE_AGENT_HOME")
    if override is not None:
        ensure_not_c_drive(
            override,
            allow_c_drive=settings.allow_c_drive,
            label="CODE_AGENT_MEMORY_ROOT",
        )
    return AppPaths(home=home, memory_override=override, allow_c_drive=settings.allow_c_drive)
