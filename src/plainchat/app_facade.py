"""Public facade for launching PlainChat TUI."""

from typing import Optional

from plainchat.ui.app import ChatbotApp


def start_chatbot(word: Optional[str] = None) -> None:
    """Start chatbot TUI and return after user exits the TUI."""
    app = ChatbotApp(word=word)
    app.run()

