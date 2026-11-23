"""模型客户端工厂。仅在显式调用时检查 API_KEY，import 本模块不会退出进程。"""

from __future__ import annotations

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.settings import ModelSettings

from my_code_agent.config import Settings, require_api_key


def build_model_settings(settings: Settings) -> ModelSettings | None:
    options = settings.model_request_options()
    return options or None  # type: ignore[return-value]


def build_chat_model(settings: Settings) -> OpenAIChatModel:
    require_api_key(settings)
    base = (settings.base_url or "").rstrip("/")
    if "deepseek.com" in base:
        from pydantic_ai.providers.deepseek import DeepSeekProvider

        provider = DeepSeekProvider(api_key=settings.api_key)
    else:
        from pydantic_ai.providers.openai import OpenAIProvider

        provider = OpenAIProvider(api_key=settings.api_key, base_url=settings.base_url)
    return OpenAIChatModel(settings.model, provider=provider)
