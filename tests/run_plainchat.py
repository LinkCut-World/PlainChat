import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from plainchat.app_facade import start_chatbot


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_history_file = str((script_dir / "data/history.json").resolve())

    parser = argparse.ArgumentParser(description="Start plainchat chatbot")
    parser.add_argument(
        "-f",
        "--history-file",
        type=str,
        default=default_history_file,
        help="path to history.json",
    )
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL")
    if not api_key or not base_url or not model:
        print("Missing OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL, please configure in .env")
        return

    start_chatbot(
        history_file=args.history_file,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


if __name__ == "__main__":
    main()