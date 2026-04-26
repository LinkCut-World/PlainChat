import threading

from prompt_toolkit.application import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.widgets import Frame, TextArea
from rich.console import Console
from rich.console import Group
from rich.markdown import Markdown, TableElement
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text


class ChineseWrappingTableElement(TableElement):
    def __rich_console__(self, console, options):
        table = Table(
            box=box.SIMPLE,
            pad_edge=False,
            style="markdown.table.border",
            show_edge=True,
            show_lines=True,
            collapse_padding=True,
        )

        if self.header is not None and self.header.row is not None:
            for column in self.header.row.cells:
                heading = column.content.copy()
                heading.stylize("markdown.table.header")
                table.add_column(heading, overflow="fold")

        if self.body is not None:
            for row in self.body.rows:
                row_content = [element.content for element in row.cells]
                table.add_row(*row_content)

        yield table


class PlainChatMarkdown(Markdown):
    elements = Markdown.elements.copy()
    elements["table_open"] = ChineseWrappingTableElement


def _render_message_lines(message, width):
    console = Console(force_terminal=True, color_system="256", width=max(1, width))
    role = message["role"]
    content = message["content"]
    if role == "user":
        title = "❖ You"
        color = "blue"
    elif role in ("assistant_error", "error"):
        title = "❖ System"
        color = "red"
    else:
        title = "❖ AI"
        color = "green"

    with console.capture() as capture:
        inner_text = f"[bold {color}]{title}:[/bold {color}]"
        if role in ("assistant", "ai"):
            renderable = Group(Text.from_markup(inner_text), Text(""), PlainChatMarkdown(content))
        elif role in ("assistant_error", "error"):
            renderable = Group(
                Text.from_markup(inner_text),
                Text(""),
                Text(content, style="bold red"),
            )
        else:
            renderable = inner_text + "\n\n" + content
        console.print(Panel(renderable, border_style="black", expand=True))

    return list(split_lines(to_formatted_text(ANSI(capture.get()))))


class HistoryViewerControl(UIControl):
    def __init__(self, history_getter):
        self._history_getter = history_getter
        self.scroll_offset = 0
        self._follow_tail = True
        self._last_width = 0
        self._last_height = 0
        self._cache_key = None
        self._cached_lines = [[]]

    def scroll_to_bottom(self):
        self._follow_tail = True

    def is_following_tail(self):
        return self._follow_tail

    def reset_cache(self):
        self._cache_key = None

    def _get_all_lines(self, width):
        history = self._history_getter()
        cache_key = (width, tuple((item["role"], item["content"]) for item in history))
        if cache_key != self._cache_key:
            lines = []
            for message in history:
                lines.extend(_render_message_lines(message, width))
            self._cached_lines = lines or [[]]
            self._cache_key = cache_key
        return self._cached_lines

    def _max_offset(self):
        return max(0, len(self._cached_lines) - max(1, self._last_height))

    def create_content(self, width, height):
        self._last_width = max(1, width)
        self._last_height = max(1, height)
        lines = self._get_all_lines(self._last_width)
        max_offset = max(0, len(lines) - self._last_height)

        if self._follow_tail:
            self.scroll_offset = max_offset
        else:
            self.scroll_offset = min(self.scroll_offset, max_offset)

        self.scroll_offset = max(0, self.scroll_offset)
        visible_lines = lines[self.scroll_offset : self.scroll_offset + self._last_height]

        return UIContent(
            get_line=lambda line_index: visible_lines[line_index] if line_index < len(visible_lines) else [],
            line_count=max(1, len(visible_lines)),
            cursor_position=Point(x=0, y=0),
            show_cursor=False,
        )

    def mouse_handler(self, mouse_event):
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            self._follow_tail = False
            self.scroll_offset = max(0, self.scroll_offset - 3)
            get_app().invalidate()
            return None

        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            max_offset = self._max_offset()
            self.scroll_offset = min(max_offset, self.scroll_offset + 3)
            self._follow_tail = self.scroll_offset >= max_offset
            get_app().invalidate()
            return None

        return NotImplemented


class DialogView:
    def __init__(self, on_submit_callback):
        self.on_submit_callback = on_submit_callback
        self.history = []
        self._history_lock = threading.Lock()
        self.is_streaming = False
        self.history_control = HistoryViewerControl(self._get_history_snapshot)

        input_key_bindings = KeyBindings()

        @input_key_bindings.add("enter")
        def _handle_enter(event):
            if self.is_streaming:
                return
            buff = event.current_buffer
            text = buff.text.strip()
            if text:
                buff.text = ""
                self.on_submit_callback(text)

        @input_key_bindings.add("c-j")
        @input_key_bindings.add("escape", "enter")
        def _handle_newline(event):
            event.current_buffer.insert_text("\n")

        def get_input_height():
            # 根据当前文本的换行数动态返回确切的行数高度
            line_count = self.input_field.text.count("\n") + 1
            return min(2, max(1, line_count))

        self.input_field = TextArea(prompt="> ", multiline=True, height=get_input_height)
        self.input_field.control.key_bindings = input_key_bindings

        self.history_window = Window(content=self.history_control, wrap_lines=False, always_hide_cursor=True)

        self.container = HSplit(
            [
                Frame(self.history_window, title=" Chat History (Scroll to browse) "),
                Frame(self.input_field, title=" Message (Press Enter to Post) "),
            ]
        )

    def _get_history_snapshot(self):
        with self._history_lock:
            return [dict(item) for item in self.history]

    def add_message(self, role, content):
        with self._history_lock:
            self.history.append({"role": role, "content": content})
        self.history_control.reset_cache()
        self.history_control.scroll_to_bottom()

    def append_to_message(self, index, text_chunk):
        if not text_chunk:
            return
        should_follow_tail = self.history_control.is_following_tail()
        with self._history_lock:
            if 0 <= index < len(self.history):
                self.history[index]["content"] += text_chunk
        self.history_control.reset_cache()
        if should_follow_tail:
            self.history_control.scroll_to_bottom()

    def set_message(self, index, role, content):
        should_follow_tail = self.history_control.is_following_tail()
        with self._history_lock:
            if 0 <= index < len(self.history):
                self.history[index]["role"] = role
                self.history[index]["content"] = content
            else:
                return
        self.history_control.reset_cache()
        if should_follow_tail:
            self.history_control.scroll_to_bottom()

    def get_message(self, index):
        with self._history_lock:
            if 0 <= index < len(self.history):
                return dict(self.history[index])
        return None

    def add_assistant_placeholder(self):
        with self._history_lock:
            self.history.append({"role": "assistant", "content": ""})
            index = len(self.history) - 1
        self.history_control.reset_cache()
        self.history_control.scroll_to_bottom()
        return index

    def set_input_enabled(self, enabled):
        self.is_streaming = not enabled

    def load_history(self, messages):
        with self._history_lock:
            self.history = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
        self.history_control.reset_cache()
        self.history_control.scroll_to_bottom()
