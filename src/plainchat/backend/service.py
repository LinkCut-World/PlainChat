"""OpenAI-compatible streaming chat service."""

from typing import Dict, Generator, List, Optional

from openai import APIConnectionError, APITimeoutError, AuthenticationError, OpenAI
from requests.exceptions import ConnectionError as RequestsConnectionError


class ChatServiceError(RuntimeError):
    """Raised when chat service configuration or network calls fail."""


_CLIENT: Optional[OpenAI] = None
_CLIENT_CFG: Optional[tuple[str, str]] = None


def _build_client(api_key: str, base_url: str) -> OpenAI:
    global _CLIENT, _CLIENT_CFG

    cfg = (api_key, base_url)
    if _CLIENT is not None and _CLIENT_CFG == cfg:
        return _CLIENT

    _CLIENT = OpenAI(api_key=api_key, base_url=base_url)
    _CLIENT_CFG = cfg
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
    messages: List[Dict[str, str]],
    *,
    api_key: Optional[str],
    base_url: Optional[str],
    model: Optional[str],
    word: Optional[str] = None,
) -> Generator[str, None, None]:
    if not messages:
        raise ChatServiceError("messages cannot be empty")
    if not api_key or not base_url or not model:
        raise ChatServiceError(
            "缺少模型配置：api_key/base_url/model 均需由宿主显式传入。"
        )

    client = _build_client(api_key=api_key, base_url=base_url)
    payload_messages = _with_word_system_prompt(messages, word)

    try:
        stream = client.chat.completions.create(
            model=model,
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

