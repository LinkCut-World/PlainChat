import asyncio
import threading
import time
from typing import Any, Dict, List, Optional

from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import ConditionalContainer, HSplit
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

from plainchat.backend import storage
from plainchat.backend.service import ChatServiceError, chat_stream

from .views.home import HomeView
from .views.dialog import DialogView


class ChatbotApp:
    def __init__(
        self,
        *,
        history_file,
        prefill_query: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
        api_key=None,
        base_url=None,
        model=None,
    ):
        self.current_route = "home"
        self.prefill_query = prefill_query
        self.conversation_extras = dict(extras or {})
        if self.prefill_query:
            self.conversation_extras.setdefault("prefill_query", self.prefill_query)
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        storage.set_history_file_path(history_file)
        self.current_conversation_id = None
        self._stream_thread = None
        self._stream_lock = threading.Lock()

        initial_text = self.prefill_query if self.prefill_query else ""
        self.home_view = HomeView(self._on_home_submit, initial_text=initial_text)
        self.dialog_view = DialogView(self._on_dialog_submit)

        self.home_container = ConditionalContainer(
            content=self.home_view.container,
            filter=Condition(lambda: self.current_route == "home"),
        )
        self.dialog_container = ConditionalContainer(
            content=self.dialog_view.container,
            filter=Condition(lambda: self.current_route == "dialog"),
        )
        self.container = HSplit([self.home_container, self.dialog_container])
        self.layout = Layout(self.container)

        self.kb = KeyBindings()
        self._bind_keys()

        style = Style.from_dict(
            {
                "frame.border": "#888888",
                "frame.label": "bold default",
                "query": "bold #ffffff",
                "preview": "#aaaaaa",
                "hlight.indicator": "bold #d8b4e2",
                "hlight.query": "bold #d8b4e2",
                "hlight.preview": "#b39dbd",
            }
        )

        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=style,
            full_screen=True,
            mouse_support=True,
            refresh_interval=0.1,
        )

    def _on_home_submit(self, query, history_id):
        if history_id:
            conversation = storage.get_conversation(history_id)
            if not conversation:
                return

            self.current_conversation_id = history_id
            history_messages = [
                {"role": message.role, "content": message.content}
                for message in conversation.messages
            ]
            self.dialog_view.load_history(history_messages)
            self._set_route("dialog", self.app)
            return

        if not query:
            return

        conversation = storage.create_conversation(self.conversation_extras)
        self.current_conversation_id = conversation.id
        self.dialog_view.load_history([])
        self._set_route("dialog", self.app)
        self._handle_user_query(query)

    def _on_dialog_submit(self, query):
        self._handle_user_query(query)

    def _handle_user_query(self, query):
        if not query:
            return

        if self.dialog_view.is_streaming:
            return

        if not self.current_conversation_id:
            conversation = storage.create_conversation(self.conversation_extras)
            self.current_conversation_id = conversation.id

        conv_id = self.current_conversation_id
        storage.add_message(conv_id, "user", query)
        self.dialog_view.add_message("user", query)
        assistant_index = self.dialog_view.add_assistant_placeholder()
        self.dialog_view.set_input_enabled(False)
        self.app.invalidate()

        history_messages = self._get_conversation_messages_for_llm(conv_id)
        self._stream_thread = threading.Thread(
            target=self._stream_answer_worker,
            args=(conv_id, history_messages, assistant_index),
            daemon=True,
        )
        self._stream_thread.start()

    def _get_conversation_messages_for_llm(self, conv_id) -> List[Dict[str, str]]:
        conversation = storage.get_conversation(conv_id)
        if not conversation:
            return []

        messages: List[Dict[str, str]] = []
        for message in conversation.messages:
            if message.role in ("user", "assistant", "system"):
                messages.append({"role": message.role, "content": message.content})
        return messages

    def _stream_answer_worker(self, conv_id, history_messages, assistant_index):
        with self._stream_lock:
            pending_chunks: List[str] = []
            full_chunks: List[str] = []
            pending_size = 0
            last_flush_at = time.monotonic()

            def flush_pending():
                nonlocal pending_chunks, pending_size, last_flush_at
                if not pending_chunks:
                    return
                chunk = "".join(pending_chunks)
                pending_chunks = []
                pending_size = 0
                self.dialog_view.append_to_message(assistant_index, chunk)
                self.app.invalidate()
                last_flush_at = time.monotonic()

            try:
                for token in chat_stream(
                    history_messages,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model=self.model,
                ):
                    full_chunks.append(token)
                    pending_chunks.append(token)
                    pending_size += len(token)
                    now = time.monotonic()
                    if pending_size >= 5 or now - last_flush_at >= 0.05:
                        flush_pending()

                flush_pending()

                full_answer = "".join(full_chunks).strip()
                if not full_answer:
                    full_answer = "(No response from model.)"
                    self.dialog_view.append_to_message(assistant_index, full_answer)
                    self.app.invalidate()

                storage.add_message(conv_id, "assistant", full_answer)
            except ChatServiceError as err:
                error_text = f"System message: {err}"
                placeholder = self.dialog_view.get_message(assistant_index)
                if placeholder and placeholder.get("content", "").strip():
                    self.dialog_view.add_message("assistant_error", error_text)
                else:
                    self.dialog_view.set_message(assistant_index, "assistant_error", error_text)
                storage.add_message(conv_id, "assistant", error_text)
                self.app.invalidate()
            except Exception as err:  # pragma: no cover
                error_text = f"System message: An unknown error occurred, please try again later. ({err})"
                placeholder = self.dialog_view.get_message(assistant_index)
                if placeholder and placeholder.get("content", "").strip():
                    self.dialog_view.add_message("assistant_error", error_text)
                else:
                    self.dialog_view.set_message(assistant_index, "assistant_error", error_text)
                storage.add_message(conv_id, "assistant", error_text)
                self.app.invalidate()
            finally:
                self.dialog_view.set_input_enabled(True)
                self.app.invalidate()

    def _set_route(self, route, app_or_event):
        app = getattr(app_or_event, "app", app_or_event)
        if self.current_route != route:
            self.current_route = route

            if route == "home":
                app.layout.focus(self.home_view.search_field)
            elif route == "dialog":
                app.layout.focus(self.dialog_view.input_field)

            app.renderer.clear()
            app.invalidate()
            app.create_background_task(self._deferred_refresh(app))

    async def _deferred_refresh(self, app):
        await asyncio.sleep(0.01)
        app.invalidate()

    def _bind_keys(self):
        @self.kb.add("c-c")
        def exit_app(event):
            event.app.exit()

        @self.kb.add("tab")
        def toggle_view(event):
            if self.current_route == "dialog":
                self._set_route("home", event.app)

    def run(self):
        self.app.run()

