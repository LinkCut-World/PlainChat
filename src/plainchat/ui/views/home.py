import re

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.margins import PromptMargin
from prompt_toolkit.widgets import Frame, TextArea

from plainchat.backend.storage import search_conversations


class HomeView:
    VISIBLE_WINDOW_SIZE = 31

    def __init__(self, on_submit_callback, initial_text=""):
        self.on_submit_callback = on_submit_callback
        self.filtered_data = []
        self.selected_index = -1
        self.window_start = 0
        self.last_move_dir = None

        self.kb = KeyBindings()

        @self.kb.add("up")
        def _(event):
            self.scroll_up()

        @self.kb.add("down")
        def _(event):
            self.scroll_down()

        def accept_handler(buff):
            text = buff.text.strip()
            if self.selected_index != -1 and self.selected_index < len(self.filtered_data):
                selected_item = self.filtered_data[self.selected_index]
                self.on_submit_callback(selected_item.title, selected_item.conversation_id)
            else:
                if text:
                    self.on_submit_callback(text, None)
                    buff.text = ""

            return True

        self.search_field = TextArea(
            prompt="Ask AI (or search history): ",
            multiline=False,
            accept_handler=accept_handler,
        )
        self.search_field.control.key_bindings = self.kb
        self.search_field.buffer.on_text_changed += self._on_text_changed

        self.list_window = Window(
            content=FormattedTextControl(self._get_list_text),
            wrap_lines=True,
            get_line_prefix=lambda line_number, wrap_count: "  " if wrap_count > 0 else "",
            right_margins=[PromptMargin(lambda: [("", "  ")])],
        )

        self.container = HSplit(
            [
                Frame(self.list_window, title=" History "),
                Frame(self.search_field, title=" Chat "),
            ]
        )

        if initial_text:
            self.search_field.text = initial_text
            self.search_field.buffer.cursor_position = len(initial_text)

        self._refresh_results()

    def _refresh_results(self):
        query = self.search_field.text
        self.filtered_data = search_conversations(query)
        self.selected_index = -1
        self.window_start = 0
        self.last_move_dir = None

    def _clamp_window_start(self, total_count):
        max_start = max(0, total_count - self.VISIBLE_WINDOW_SIZE)
        self.window_start = max(0, min(self.window_start, max_start))

    def _ensure_selection_visible(self):
        total_count = len(self.filtered_data)
        if total_count == 0:
            self.window_start = 0
            return

        self._clamp_window_start(total_count)

        if self.selected_index == -1:
            return

        window_end = self.window_start + self.VISIBLE_WINDOW_SIZE - 1
        if self.selected_index < self.window_start:
            self.window_start = self.selected_index
        elif self.selected_index > window_end:
            self.window_start = self.selected_index - self.VISIBLE_WINDOW_SIZE + 1

        self._clamp_window_start(total_count)

    def scroll_up(self):
        moved = False
        if self.filtered_data and self.selected_index > 0:
            self.selected_index -= 1
            moved = True
        elif self.selected_index == -1 and self.filtered_data:
            self.selected_index = 0
            moved = True

        if moved:
            self.last_move_dir = "up"
            self._ensure_selection_visible()

    def scroll_down(self):
        moved = False
        if self.filtered_data:
            if self.selected_index == -1:
                self.selected_index = len(self.filtered_data) - 1
                moved = True
            elif self.selected_index < len(self.filtered_data) - 1:
                self.selected_index += 1
                moved = True

        if moved:
            self.last_move_dir = "down"
            self._ensure_selection_visible()

    def _on_text_changed(self, _):
        self._refresh_results()

    def _highlight_match(self, text, base_style):
        keyword = self.search_field.text.strip()
        if not keyword:
            return [(base_style, text)]

        parts = re.split(f"({re.escape(keyword)})", text, flags=re.IGNORECASE)
        fragments = []
        for part in parts:
            if not part:
                continue
            if part.lower() == keyword.lower():
                fragments.append((f"{base_style} fg:#ffffff", part))
            else:
                fragments.append((base_style, part))
        return fragments

    def _get_list_text(self):
        result = []
        if not self.filtered_data:
            result.append(("", "  No results found.\n"))
        else:
            self._ensure_selection_visible()
            window_end = self.window_start + self.VISIBLE_WINDOW_SIZE
            visible_items = self.filtered_data[self.window_start : window_end]

            for local_index, item in enumerate(visible_items):
                global_index = self.window_start + local_index
                is_selected = global_index == self.selected_index
                query_text = f"{item.title}\n"
                preview_text = f"{item.match_content or '(No answer yet)'}\n\n"
                cursor_at_end = self.last_move_dir == "down"

                if is_selected:
                    if not cursor_at_end:
                        result.append(("[SetCursorPosition]", ""))
                    result.append(("class:hlight.indicator", "▶ "))
                    result.extend(self._highlight_match(query_text, "class:hlight.query"))
                    result.append(("", "  "))
                    result.extend(self._highlight_match(preview_text, "class:hlight.preview"))
                    if cursor_at_end:
                        result.append(("[SetCursorPosition]", ""))
                else:
                    result.append(("", "  "))
                    result.extend(self._highlight_match(query_text, "class:query"))
                    result.append(("", "  "))
                    result.extend(self._highlight_match(preview_text, "class:preview"))

        return result

