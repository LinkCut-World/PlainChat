# PlainChat

PlainChat is a minimal full-screen terminal chatbot (TUI) inspired by web chat UX:

- Runs in terminal (alternate screen, clean exit back to your shell)
- Minimal by design (no tools/skills framework)
- Searchable conversation history and resume conversations

## Install

```bash
pip install "plainchat @ git+https://github.com/LinkCut-World/PlainChat.git"
```

## Configure

Create `.env` in your working directory (or `data/.env`), with an OpenAI-compatible endpoint:

```ini
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=deepseek-chat
```

## Run

```bash
plainchat
```

