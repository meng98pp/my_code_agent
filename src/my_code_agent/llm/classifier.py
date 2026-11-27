"""auto 模式旁路 LLM。safety 只提供转写；本模块发 HTTP。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from my_code_agent.safety.classifier import SYSTEM_PROMPT, build_transcript, parse_verdict


async def classify(
    messages: Sequence[Any],
    tool_name: str,
    args: Mapping[str, Any],
    *,
    settings: Any = None,
) -> dict[str, Any]:
    """出错返回 error=True 且 should_block=True，由关卡回退人工。"""
    transcript = build_transcript(messages, tool_name, args)
    api_key = getattr(settings, "api_key", None) or ""
    model = getattr(settings, "model", None) or ""
    base_url = getattr(settings, "base_url", None) or ""
    if not api_key or not model:
        return {
            "should_block": True,
            "reason": "classifier 出错（MissingAPIKeyError），回退人工审批",
            "error": True,
        }
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, base_url=base_url or None)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return parse_verdict(content)
    except Exception as exc:
        return {
            "should_block": True,
            "reason": f"classifier 出错（{type(exc).__name__}），回退人工审批",
            "error": True,
        }
