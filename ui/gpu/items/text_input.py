# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Text Input
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import bpy

from ..drawing import BLFDrawing, GPUDrawing
from ..style import GPULayoutStyle, WidgetType
from .base import LayoutItem


_KEY_ENTER = {"RET", "NUMPAD_ENTER"}
_KEY_DELETE = {"DEL", "BACK_SPACE"}
_KEY_ARROWS = {"LEFT_ARROW", "RIGHT_ARROW", "UP_ARROW", "DOWN_ARROW"}
_KEY_HOME_END = {"HOME", "END"}


@dataclass
class TextEditState:
    """編集中のテキスト状態"""
    text: str = ""
    cursor: int = 0
    sel_start: int = 0
    sel_end: int = 0
    scroll_x: float = 0.0
    original_text: str = ""

    @classmethod
    def begin(cls, text: str, *, select_all: bool = False) -> TextEditState:
        length = len(text)
        cursor = length
        if select_all:
            sel_start, sel_end = (0, length)
        else:
            sel_start = sel_end = cursor
        return cls(
            text=text,
            cursor=cursor,
            sel_start=sel_start,
            sel_end=sel_end,
            scroll_x=0.0,
            original_text=text,
        )

    def has_selection(self) -> bool:
        return self.sel_start != self.sel_end

    def selection_range(self) -> tuple[int, int]:
        if self.sel_start <= self.sel_end:
            return (self.sel_start, self.sel_end)
        return (self.sel_end, self.sel_start)

    def clear_selection(self) -> None:
        self.sel_start = self.cursor
        self.sel_end = self.cursor

    def set_cursor(self, pos: int, *, select: bool = False) -> None:
        pos = max(0, min(len(self.text), pos))
        if select:
            if not self.has_selection():
                self.sel_start = self.cursor
                self.sel_end = pos
            else:
                if self.sel_start == self.cursor:
                    self.sel_start = pos
                else:
                    self.sel_end = pos
        else:
            self.sel_start = pos
            self.sel_end = pos
        self.cursor = pos

    def select_all(self) -> None:
        self.sel_start = 0
        self.sel_end = len(self.text)
        self.cursor = self.sel_end

    def delete_selection(self) -> bool:
        if not self.has_selection():
            return False
        start, end = self.selection_range()
        self.text = self.text[:start] + self.text[end:]
        self.cursor = start
        self.sel_start = start
        self.sel_end = start
        return True

    def insert_text(self, text: str, *, max_length: int = 0) -> bool:
        if not text:
            return False
        if max_length > 0:
            available = max_length - len(self.text)
            if self.has_selection():
                start, end = self.selection_range()
                available += (end - start)
            if available <= 0:
                return False
            text = text[:available]

        if self.has_selection():
            self.delete_selection()

        before = self.text[:self.cursor]
        after = self.text[self.cursor:]
        self.text = f"{before}{text}{after}"
        self.cursor += len(text)
        self.sel_start = self.cursor
        self.sel_end = self.cursor
        return True

    def backspace(self) -> bool:
        if self.has_selection():
            return self.delete_selection()
        if self.cursor <= 0:
            return False
        self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
        self.cursor -= 1
        self.sel_start = self.cursor
        self.sel_end = self.cursor
        return True

    def delete(self) -> bool:
        if self.has_selection():
            return self.delete_selection()
        if self.cursor >= len(self.text):
            return False
        self.text = self.text[:self.cursor] + self.text[self.cursor + 1:]
        self.sel_start = self.cursor
        self.sel_end = self.cursor
        return True

    def move_cursor(self, delta: int, *, select: bool = False) -> None:
        self.set_cursor(self.cursor + delta, select=select)

    def move_to_start(self, *, select: bool = False) -> None:
        self.set_cursor(0, select=select)

    def move_to_end(self, *, select: bool = False) -> None:
        self.set_cursor(len(self.text), select=select)

    def handle_key_event(self, event, *, max_length: int = 0) -> bool:
        if event.type == 'TEXTINPUT':
            if getattr(event, "ctrl", False) or getattr(event, "alt", False):
                return False
            text = getattr(event, "unicode", "") or ""
            text = text.replace("\r", "").replace("\n", "")
            return self.insert_text(text, max_length=max_length)

        if event.value not in {'PRESS', 'REPEAT'}:
            return False

        if event.type in _KEY_DELETE:
            if event.type == 'BACK_SPACE':
                return self.backspace()
            return self.delete()

        if event.type in _KEY_ARROWS:
            select = bool(getattr(event, "shift", False))
            if event.type == 'LEFT_ARROW':
                self.move_cursor(-1, select=select)
            elif event.type == 'RIGHT_ARROW':
                self.move_cursor(1, select=select)
            elif event.type == 'UP_ARROW':
                self.move_to_start(select=select)
            else:
                self.move_to_end(select=select)
            return True

        if event.type in _KEY_HOME_END:
            select = bool(getattr(event, "shift", False))
            if event.type == 'HOME':
                self.move_to_start(select=select)
            else:
                self.move_to_end(select=select)
            return True

        if getattr(event, "ctrl", False):
            if event.type == 'A':
                self.select_all()
                return True
            if event.type == 'C':
                start, end = self.selection_range()
                if start != end:
                    bpy.context.window_manager.clipboard = self.text[start:end]
                    return True
            if event.type == 'X':
                start, end = self.selection_range()
                if start != end:
                    bpy.context.window_manager.clipboard = self.text[start:end]
                    self.delete_selection()
                    return True
            if event.type == 'V':
                clip = bpy.context.window_manager.clipboard or ""
                if clip:
                    return self.insert_text(clip, max_length=max_length)

        return False


@dataclass
class TextInputItem(LayoutItem):
    """テキスト入力フィールド"""
    value: str = ""
    placeholder: str = ""
    text: str = ""
    max_length: int = 0
    widget_type: WidgetType = WidgetType.TEXT
    on_change: Optional[Callable[[str], None]] = None
    on_confirm: Optional[Callable[[str], None]] = None
    on_cancel: Optional[Callable[[], None]] = None

    _hovered: bool = field(default=False, repr=False)
    _editing: bool = field(default=False, repr=False)
    _edit_state: Optional[TextEditState] = field(default=None, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_size = style.scaled_text_size()
        display_text = self._get_display_text()
        text_w, _ = BLFDrawing.get_text_dimensions(display_text, text_size)
        padding = style.scaled_padding()
        min_width = max(text_w + padding * 4, style.ui_scale(120))
        return (max(self.width, min_width), style.scaled_item_height())

    def get_value(self) -> str:
        return self.value

    def set_value(self, value: str) -> None:
        self.value = str(value) if value is not None else ""

    def _get_display_text(self) -> str:
        value_text = self.value
        if not value_text and self.placeholder:
            value_text = self.placeholder
        if self.text:
            return f"{self.text}: {value_text}"
        return value_text

    def begin_editing(self, *, select_all: bool = False) -> None:
        if not self.enabled:
            return
        self._editing = True
        self._edit_state = TextEditState.begin(self.value, select_all=select_all)

    def end_editing(self, *, confirm: bool) -> None:
        if not self._editing or self._edit_state is None:
            return
        if confirm:
            new_value = self._edit_state.text
            self.value = new_value
            if self.on_change:
                self.on_change(new_value)
            if self.on_confirm:
                self.on_confirm(new_value)
        else:
            if self.on_cancel:
                self.on_cancel()
        self._editing = False
        self._edit_state = None

    def handle_key_event(self, event) -> bool:
        if not self._editing or self._edit_state is None:
            return False

        if event.type in _KEY_ENTER:
            self.end_editing(confirm=True)
            return True
        if event.type == 'ESC':
            self.end_editing(confirm=False)
            return True

        handled = self._edit_state.handle_key_event(event, max_length=self.max_length)
        if handled:
            return True
        return False

    def set_cursor_from_mouse(self, mouse_x: float, style: GPULayoutStyle) -> None:
        if not self._editing or self._edit_state is None:
            return
        text_x, text_width = self._text_area(style)
        local_x = mouse_x - text_x + self._edit_state.scroll_x
        self._edit_state.set_cursor(self._cursor_from_x(local_x, style))

    def _cursor_from_x(self, x: float, style: GPULayoutStyle) -> int:
        if self._edit_state is None:
            return 0
        text = self._edit_state.text
        text_size = style.scaled_text_size()
        if x <= 0:
            return 0
        if not text:
            return 0
        low = 0
        high = len(text)
        while low < high:
            mid = (low + high) // 2
            width, _ = BLFDrawing.get_text_dimensions(text[:mid + 1], text_size)
            if width < x:
                low = mid + 1
            else:
                high = mid
        return low

    def _text_area(self, style: GPULayoutStyle) -> tuple[float, float]:
        padding = style.scaled_padding()
        return (self.x + padding, max(0.0, self.width - padding * 2))

    def _ensure_cursor_visible(self, style: GPULayoutStyle) -> None:
        if self._edit_state is None:
            return
        text_size = style.scaled_text_size()
        cursor_x, _ = BLFDrawing.get_text_dimensions(
            self._edit_state.text[:self._edit_state.cursor], text_size
        )
        _, area_width = self._text_area(style)
        if area_width <= 0:
            return

        if cursor_x - self._edit_state.scroll_x > area_width - 2:
            self._edit_state.scroll_x = cursor_x - (area_width - 2)
        elif cursor_x - self._edit_state.scroll_x < 0:
            self._edit_state.scroll_x = cursor_x

    def draw(self, style: GPULayoutStyle, state=None) -> None:
        if not self.visible:
            return

        wcol = style.get_widget_colors(self.widget_type)
        if wcol is None:
            return

        hovered = state.hovered if state else self._hovered
        focused = state.focused if state else self._editing
        enabled = state.enabled if state else self.enabled

        radius = int(wcol.roundness * self.height * 0.5)

        if focused:
            bg_color = wcol.inner_sel
        elif hovered:
            bg_color = tuple(min(1.0, c * 1.15) for c in wcol.inner[:3]) + (wcol.inner[3],)
        else:
            bg_color = wcol.inner

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            radius, bg_color, self.corners
        )

        outline_base = wcol.outline_sel if focused else wcol.outline
        outline_color = outline_base if enabled else tuple(c * 0.5 for c in outline_base[:3]) + (outline_base[3],)
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        text_size = style.scaled_text_size()
        text_x, text_width = self._text_area(style)
        text_y = self.y - (self.height + BLFDrawing.get_text_dimensions("Wg", text_size)[1]) / 2
        clip_rect = BLFDrawing.calc_clip_rect(text_x, self.y, text_width, self.height, 0)

        if self._editing and self._edit_state is not None:
            self._ensure_cursor_visible(style)
            text_value = self._edit_state.text
            draw_x = text_x - self._edit_state.scroll_x

            if self._edit_state.has_selection():
                sel_start, sel_end = self._edit_state.selection_range()
                start_w, _ = BLFDrawing.get_text_dimensions(text_value[:sel_start], text_size)
                end_w, _ = BLFDrawing.get_text_dimensions(text_value[:sel_end], text_size)
                sel_x = draw_x + start_w
                sel_w = max(1.0, end_w - start_w)
                sel_color = style.highlight_color
                GPUDrawing.draw_rect(sel_x, self.y, sel_w, self.height, sel_color)

            text_color = wcol.text_sel if focused else wcol.text
            if not enabled:
                text_color = tuple(c * 0.5 for c in text_color[:3]) + (text_color[3],)
            BLFDrawing.draw_text_clipped(draw_x, text_y, text_value, text_color, text_size, clip_rect)

            cursor_w, _ = BLFDrawing.get_text_dimensions(text_value[:self._edit_state.cursor], text_size)
            cursor_x = draw_x + cursor_w
            GPUDrawing.draw_rect(cursor_x, self.y, max(1.0, style.ui_scale(1)), self.height, text_color)
            return

        display_text = self._get_display_text()
        text_color = wcol.text if enabled else tuple(c * 0.5 for c in wcol.text[:3]) + (wcol.text[3],)
        if not self.value and self.placeholder:
            text_color = style.text_color_secondary if enabled else style.text_color_disabled
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)
