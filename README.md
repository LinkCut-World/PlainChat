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

### `start_chatbot(...)` arguments

- required: `history_file`, `api_key`, `base_url`, `model`
- optional: `prefill_query`, `extras`

`prefill_query` is used to prefill the home input box when the TUI starts.
`extras` is persisted on each new conversation as host-provided context data.

Example:

```python
start_chatbot(
    history_file="data/history.json",
    api_key=api_key,
    base_url=base_url,
    model=model,
    prefill_query="eager",
    extras={"source": "shanbei", "word": "eager"},
)
```
