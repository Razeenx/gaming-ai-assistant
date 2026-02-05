"""
AI Service — интеграция с Groq (Llama, Mixtral) для умных ответов в чате.
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

# Llama 3.3 70B — качественные ответы
DEFAULT_MODEL = "llama-3.3-70b-versatile"
# Альтернатива (быстрее): llama-3.1-8b-instant
FALLBACK_MODEL = "llama-3.1-8b-instant"

_client: Optional[AsyncGroq] = None


def _get_client() -> Optional[AsyncGroq]:
    """Создать клиент Groq, если API ключ задан."""
    global _client
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    if _client is None:
        _client = AsyncGroq(api_key=api_key)
    return _client


async def chat_completion(
    messages: list[dict],
    system_prompt: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
) -> Optional[str]:
    """
    Отправить запрос в Groq и получить текстовый ответ.

    Args:
        messages: История диалога [{"role": "user"|"assistant"|"system", "content": "..."}]
        system_prompt: Системный промпт (описание роли агента)
        model: Имя модели Groq
        max_tokens: Макс. длина ответа

    Returns:
        Текст ответа или None при ошибке
    """
    client = _get_client()
    if not client:
        return None

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        choice = response.choices[0] if response.choices else None
        if choice and choice.message:
            return choice.message.content
        return None
    except Exception as e:
        print(f"[AIService] Groq error: {e}")
        if model != FALLBACK_MODEL:
            return await chat_completion(
                messages=messages,
                system_prompt=system_prompt,
                model=FALLBACK_MODEL,
                max_tokens=max_tokens,
            )
        return None


def is_available() -> bool:
    """Проверить, доступен ли Groq API."""
    return _get_client() is not None
