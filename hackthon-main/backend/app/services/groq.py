"""Shared chatbot/planner client using the already-installed HTTP client."""
import httpx
from fastapi import HTTPException

from app.config import get_settings


def complete(messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(503, "The travel assistant is not configured yet.")
    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "max_completion_tokens": 4096 if json_mode else 1200,
        "stream": False,
    }
    if settings.groq_model.startswith("openai/gpt-oss-"):
        payload["reasoning_effort"] = "low"
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json=payload, timeout=45,
        )
    except httpx.TimeoutException:
        raise HTTPException(504, "The assistant took too long. Please try again.") from None
    except httpx.RequestError:
        raise HTTPException(502, "The assistant is temporarily unreachable. Please try again.") from None
    # Do not log provider response bodies or headers: they may contain sensitive data.
    if response.status_code == 429:
        raise HTTPException(429, "Groq’s usage limit was reached. Please wait and try again; no paid fallback is used.")
    if response.status_code in (401, 403):
        raise HTTPException(503, "The assistant could not authenticate. Ask the site owner to check its Groq configuration.")
    if not response.is_success:
        raise HTTPException(502, "Groq could not process this request. Please try again later.")
    try:
        text = response.json()["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("empty response")
    except (ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(502, "The assistant returned an empty or invalid response. Please try again.") from None
    return text.strip()
