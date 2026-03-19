from plainchat.ui.app import ChatbotApp


def main() -> None:
    print("Starting PlainChat TUI (Standalone Mode)...")
    app = ChatbotApp()
    app.run()
    print("TUI exited cleanly. Back to normal CLI.")


if __name__ == "__main__":
    main()

