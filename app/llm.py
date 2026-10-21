"""
app/llm.py - DeepSeek LLM integration using the OpenAI Python SDK.
Configured for streaming responses with temperature 0.2 and robust error handling.
NEVER logs, prints, or exposes the API key.
"""

import json
import logging
import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from openai import AsyncOpenAI, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger("burj_guide.llm")

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def get_deepseek_client() -> tuple[AsyncOpenAI | None, str, str | None]:
    """
    Get configured AsyncOpenAI client pointed at DeepSeek API.
    Returns (client, model, error_message).
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    if not api_key:
        return None, model, "DeepSeek API key is not configured. Please set DEEPSEEK_API_KEY in your .env file."

    # Validate placeholder key
    if api_key in ("your_deepseek_api_key_here", "your_api_key_here", ""):
        return None, model, "DeepSeek API key contains placeholder value. Please provide a valid key in .env."

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url
    )
    return client, model, None


async def stream_chat_completion(
    messages: list[dict],
    system_prompt: str
) -> AsyncGenerator[str, None]:
    """
    Stream chat completion tokens from DeepSeek via Server-Sent Events (SSE).
    Each SSE packet has format: data: {"text": "..."}\n\n
    Final packet: data: [DONE]\n\n
    Error packet: data: {"error": "..."}\n\n
    """
    client, model, config_error = get_deepseek_client()

    if config_error:
        yield f"data: {json.dumps({'error': config_error})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Prepare message payload with system prompt first
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=0.2,
            stream=True
        )

        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = delta.content
            if content:
                yield f"data: {json.dumps({'text': content})}\n\n"

        yield "data: [DONE]\n\n"

    except AuthenticationError:
        logger.warning("DeepSeek API authentication failed (invalid API key).")
        err_msg = "Authentication failed: The provided DeepSeek API key is invalid or expired."
        yield f"data: {json.dumps({'error': err_msg})}\n\n"
        yield "data: [DONE]\n\n"

    except RateLimitError:
        logger.warning("DeepSeek API rate limit reached.")
        err_msg = "Rate limit reached: DeepSeek API is currently busy. Please wait a moment and try again."
        yield f"data: {json.dumps({'error': err_msg})}\n\n"
        yield "data: [DONE]\n\n"

    except APIConnectionError:
        logger.warning("DeepSeek API connection failed.")
        err_msg = "Network failure: Unable to connect to DeepSeek API servers. Please check your internet connection."
        yield f"data: {json.dumps({'error': err_msg})}\n\n"
        yield "data: [DONE]\n\n"

    except APIStatusError as e:
        logger.error("DeepSeek API returned HTTP status error: %s", e.status_code)
        err_msg = f"DeepSeek API error (Status {e.status_code}): {e.message or 'Request failed'}"
        yield f"data: {json.dumps({'error': err_msg})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.exception("Unexpected error in stream_chat_completion: %s", e)
        err_msg = "An unexpected error occurred while communicating with the DeepSeek API."
        yield f"data: {json.dumps({'error': err_msg})}\n\n"
        yield "data: [DONE]\n\n"
