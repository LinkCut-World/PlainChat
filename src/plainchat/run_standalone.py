import os

from dotenv import load_dotenv

from plainchat.ui.app import ChatbotApp


def main() -> None:
    print("Starting PlainChat TUI (Standalone Mode)...")
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL")
    if not api_key or not base_url or not model:
        print("Missing OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL in .env.")
        return

    app = ChatbotApp(api_key=api_key, base_url=base_url, model=model)
    app.run()
    print("TUI exited cleanly. Back to normal CLI.")


if __name__ == "__main__":
    main()

