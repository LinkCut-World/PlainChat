"""Public facade for launching PlainChat TUI."""

from typing import Any, Dict, Optional

from plainchat.ui.app import ChatbotApp


def start_chatbot(
    *,
    history_file: str,
    api_key: str,
    base_url: str,
    model: str,
    prefill_query: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> None:
    """Start chatbot TUI and return after user exits the TUI."""
    app = ChatbotApp(
        history_file=history_file,
        prefill_query=prefill_query,
        extras=extras,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    app.run()

