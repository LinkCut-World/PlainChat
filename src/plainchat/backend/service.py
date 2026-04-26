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


def chat_stream(
    messages: List[Dict[str, str]],
    *,
    api_key: Optional[str],
    base_url: Optional[str],
    model: Optional[str],
) -> Generator[str, None, None]:
    if not messages:
        raise ChatServiceError("messages cannot be empty")
    if not api_key or not base_url or not model:
        raise ChatServiceError(
            "Missing model configuration: api_key/base_url/model must all be explicitly provided by the host."
        )

    client = _build_client(api_key=api_key, base_url=base_url)
    payload_messages = list(messages)

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=payload_messages,
            stream=True,
        )
    except AuthenticationError as exc:  # pragma: no cover
        raise ChatServiceError("API authentication failed: please check if OPENAI_API_KEY is valid.") from exc
    except APITimeoutError as exc:  # pragma: no cover
        raise ChatServiceError("Request timed out: please check your network and try again.") from exc
    except (APIConnectionError, RequestsConnectionError) as exc:  # pragma: no cover
        raise ChatServiceError("Network connection failed: please check your network or proxy configuration.") from exc
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
        raise ChatServiceError("API authentication failed: please check if OPENAI_API_KEY is valid.") from exc
    except APITimeoutError as exc:  # pragma: no cover
        raise ChatServiceError("Request timed out: please check your network and try again.") from exc
    except (APIConnectionError, RequestsConnectionError) as exc:  # pragma: no cover
        raise ChatServiceError("Network connection failed: please check your network or proxy configuration.") from exc
    except Exception as exc:  # pragma: no cover
        raise ChatServiceError(f"Streaming interrupted: {exc}") from exc

