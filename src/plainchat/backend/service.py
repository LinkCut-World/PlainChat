"""OpenAI-compatible streaming chat service."""

import os
from pathlib import Path
from typing import Dict, Generator, List, Optional

from dotenv import load_dotenv
from openai import APIConnectionError, APITimeoutError, AuthenticationError, OpenAI
from requests.exceptions import ConnectionError as RequestsConnectionError


class ChatServiceError(RuntimeError):
    """Raised when chat service configuration or network calls fail."""


_CLIENT: Optional[OpenAI] = None
_MODEL: Optional[str] = None


def _data_env_path() -> Path:
    data_dir = os.environ.get("SHANBEI_DATA_DIR")
    if data_dir:
        return Path(data_dir) / ".env"
    return Path.cwd() / "data" / ".env"


def _root_env_path() -> Path:
    return Path.cwd() / ".env"


def _load_env() -> None:
    """Load environment variables from known .env locations (non-overriding)."""
    data_env = _data_env_path()
    if data_env.exists():
        load_dotenv(data_env, override=False)

    root_env = _root_env_path()
    if root_env.exists():
        load_dotenv(root_env, override=False)


def _build_client() -> OpenAI:
    global _CLIENT, _MODEL

    if _CLIENT is not None:
        return _CLIENT

    _load_env()

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL")

    missing = []
    if not api_key:
        missing.append("OPENAI_API_KEY")
    if not base_url:
        missing.append("OPENAI_BASE_URL")
    if not model:
        missing.append("OPENAI_MODEL")

    if missing:
        joined = ", ".join(missing)
        raise ChatServiceError(
            f"Missing required environment variable(s): {joined}. "
            "Set OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL in data/.env or .env."
        )

    _MODEL = model
    _CLIENT = OpenAI(api_key=api_key, base_url=base_url)
    return _CLIENT


def _with_word_system_prompt(
    messages: List[Dict[str, str]], word: Optional[str]
) -> List[Dict[str, str]]:
    if not word:
        return list(messages)

    system_prompt = {
        "role": "system",
        "content": (
            "You are a helpful assistant. "
            f"The user is currently focused on the word '{word}'. "
            "When helpful, explain usage clearly and provide natural examples."
        ),
    }

    if messages and messages[0].get("role") == "system":
        out = list(messages)
        out[0] = system_prompt
        return out

    return [system_prompt, *messages]


def chat_stream(
    messages: List[Dict[str, str]], word: Optional[str] = None
) -> Generator[str, None, None]:
    if not messages:
        raise ChatServiceError("messages cannot be empty")

    client = _build_client()
    payload_messages = _with_word_system_prompt(messages, word)

    try:
        stream = client.chat.completions.create(
            model=_MODEL,
            messages=payload_messages,
            stream=True,
        )
    except AuthenticationError as exc:  # pragma: no cover
        raise ChatServiceError("API 认证失败：请检查 OPENAI_API_KEY 是否有效。") from exc
    except APITimeoutError as exc:  # pragma: no cover
        raise ChatServiceError("请求超时：请检查网络后重试。") from exc
    except (APIConnectionError, RequestsConnectionError) as exc:  # pragma: no cover
        raise ChatServiceError("网络连接失败：请检查网络或代理配置。") from exc
    except Exception as exc:  # pragma: no cover
        raise ChatServiceError(f"Failed to start chat stream: {exc}") from exc

    try:
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if not delta:
                continue
            text = getattr(delta, "content", None)
            if text:
                yield text
    except AuthenticationError as exc:  # pragma: no cover
        raise ChatServiceError("API 认证失败：请检查 OPENAI_API_KEY 是否有效。") from exc
    except APITimeoutError as exc:  # pragma: no cover
        raise ChatServiceError("请求超时：请检查网络后重试。") from exc
    except (APIConnectionError, RequestsConnectionError) as exc:  # pragma: no cover
        raise ChatServiceError("网络连接失败：请检查网络或代理配置。") from exc
    except Exception as exc:  # pragma: no cover
        raise ChatServiceError(f"Streaming interrupted: {exc}") from exc

