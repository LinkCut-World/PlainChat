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

PlainChat library does not read `.env` by itself. Host apps should provide
`api_key/base_url/model` explicitly.

For standalone mode (`plainchat`), this project loads `.env` via `load_dotenv()`
and lets python-dotenv search current/parent directories automatically.
Create `.env` (for example at your workspace root) with:

```ini
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=deepseek-chat
```

## Run

```bash
plainchat
```

