"""Public facade for launching PlainChat TUI."""

from typing import Optional

from plainchat.ui.app import ChatbotApp


def start_chatbot(
    *,
    api_key: str,
    base_url: str,
    model: str,
    word: Optional[str] = None,
) -> None:
    """Start chatbot TUI and return after user exits the TUI."""
    app = ChatbotApp(
        word=word,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    app.run()

