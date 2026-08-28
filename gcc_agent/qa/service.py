"""OpenAI-backed QA service."""

import logging
from typing import Optional

from openai import AsyncOpenAI

from gcc_agent.config import settings
from gcc_agent.qa.messages import AI_ERROR

logger = logging.getLogger(__name__)
_openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def call_ai(messages: list[dict], lang: str) -> tuple[str, int]:
    try:
        response = await get_openai_client().chat.completions.create(
            model=settings.ai_model,
            messages=messages,
            max_tokens=settings.ai_max_tokens,
            temperature=0.7,
        )
        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        return content.strip(), tokens
    except Exception:
        logger.exception("OpenAI request failed")
        return AI_ERROR.get(lang, AI_ERROR["zh-TW"]), 0
