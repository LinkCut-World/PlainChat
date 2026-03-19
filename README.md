# PlainChat

PlainChat is a minimal full-screen terminal chatbot (TUI) inspired by web chat UX.
It is designed as a host-integrated shell, not a standalone app:

- Runs in terminal (alternate screen, clean exit back to your shell)
- Minimal by design (no tools/skills framework)
- Searchable conversation history and resume conversations
- Host app must provide model config and `history.json` path

## Install

```bash
pip install "plainchat @ git+https://github.com/LinkCut-World/PlainChat.git"
```

## Host Integration

The host app should:
- load `.env` (if needed)
- read `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`
- decide where `history.json` is stored
- call `start_chatbot(...)` with explicit arguments

