# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Layout Utilities
"""

from __future__ import annotations

from typing import Any

from ..style import Direction, Alignment
from ..items import (
    LayoutItem,
    LabelItem,
    SeparatorItem,
    ButtonItem,
    ToggleItem,
    PropDisplayItem,
    BoxItem,
    SliderItem,
    NumberItem,
    CheckboxItem,
    ColorItem,
    RadioGroupItem,
)
from ..interactive import LayoutKey


class LayoutUtilityMixin:
    """Mixin methods."""


    def _get_padding(self) -> tuple[int, int]:
        """Return (padding_x, padding_y) for this layout."""
        if self.parent is None or self._draw_background or self._draw_outline:
            return (self.style.scaled_padding_x(), self.style.scaled_padding_y())
        return (0, 0)


    def _get_available_width(self) -> float:
        """利用可能な幅を取得"""
        padding_x, _ = self._get_padding()
        return self.width - padding_x * 2


    def _get_spacing(self) -> int:
        """アイテム間のスペースを取得（align=True で 0）"""
        if self._align:
            return 0
        if self.direction == Direction.HORIZONTAL:
            return self.style.scaled_spacing_x()
        return self.style.scaled_spacing()


    def _element_can_align(self, element: Any) -> bool:
        """Return True if element participates in align-group corner stitching."""
        return isinstance(element, LayoutItem) and element.can_align()


    def _apply_ui_units_x(self) -> None:
        """Apply ui_units_x to width sizing."""
        if self.ui_units_x > 0:
            fixed_width = self.ui_units_x * self.style.scaled_item_height()
            self.sizing.fixed_width = fixed_width
            self.sizing.is_fixed = True
            self.sizing.estimated_width = fixed_width
        else:
            self.sizing.fixed_width = None
            self.sizing.is_fixed = False


    def _next_layout_index(self, kind: str) -> int:
        index = self._path_counters.get(kind, 0)
        self._path_counters[kind] = index + 1
        return index


    def _assign_layout_path(self, element: LayoutItem | GPULayout, kind: str) -> None:
        base = self._layout_path or "root"
        index = self._next_layout_index(kind)
        path = f"{base}.{kind}[{index}]"
        if isinstance(element, GPULayout):
            element._layout_path = path
            element._panel_uid = self._panel_uid
        else:
            element.layout_path = path


    def _make_layout_key(self, layout_path: str, explicit_key: str = "") -> LayoutKey:
        panel_uid = self._panel_uid or "panel"
        return LayoutKey(panel_uid=panel_uid, layout_path=layout_path, explicit_key=explicit_key or None)


    def _get_layout_key_for_item(self, item: LayoutItem) -> LayoutKey:
        layout_path = item.layout_path or f"{self._layout_path}.item[{id(item)}]"
        return self._make_layout_key(layout_path, item.key)


    def _get_item_kind(self, item: LayoutItem) -> str:
        if isinstance(item, LabelItem):
            return "label"
        if isinstance(item, SeparatorItem):
            return "separator"
        if isinstance(item, ButtonItem):
            return "button"
        if isinstance(item, ToggleItem):
            return "toggle"
        if isinstance(item, SliderItem):
            return "slider"
        if isinstance(item, NumberItem):
            return "number"
        if isinstance(item, CheckboxItem):
            return "checkbox"
        if isinstance(item, ColorItem):
            return "color"
        if isinstance(item, RadioGroupItem):
            return "radio"
        if isinstance(item, BoxItem):
            return "box"
        if isinstance(item, PropDisplayItem):
            return "prop_display"
        return "item"


    def _insert_heading_label(self) -> None:
        """
        heading ラベルを挿入

        use_property_split の状態に応じて:
        - True: split を作成し、左カラムにラベル（右寄せ）
        - False: 先頭にラベルを追加

        Note:
            この処理後 self._heading はクリアされ、
            以降のアイテム追加では heading は処理されない。
        """
        heading_text = self._heading
        self._heading = ""  # 重複防止（一度だけ処理）

        if not heading_text:
            return

        if self.use_property_split:
            # use_property_split=True: split で左カラムにラベル
            split = self.split(factor=self.style.split_factor, align=True)

            # 左カラム: ラベル（右寄せ）
            col1 = split.column()
            col1.alignment = Alignment.RIGHT
            col1.use_property_split = False  # 再帰防止
            col1.label(text=heading_text)

            # 右カラム: 空（以降の prop() は別の行として処理される）
            # Note: Blender では以降のアイテムが右カラムに入るが、
            # GPULayout では別の行として処理される。
            # 完全互換より実用性を優先。
        else:
            # use_property_split=False: 先頭にラベルを追加
            label = LabelItem(
                text=heading_text,
                icon="NONE",
                enabled=self.enabled and self.active,
                alert=self.alert
            )
            # 直接 _elements に追加（_add_item を再帰呼び出ししない）
            self._assign_layout_path(label, "label")
            label_width, label_height = label.calc_size(self.style)
            available_width = self._get_available_width()

            if self.direction == Direction.VERTICAL:
                if self.alignment == Alignment.EXPAND:
                    label.width = available_width
                    label.x = self._cursor_x
                else:
                    label.width = label_width * self.scale_x
                    if self.alignment == Alignment.CENTER:
                        label.x = self._cursor_x + (available_width - label.width) / 2
                    elif self.alignment == Alignment.RIGHT:
                        label.x = self._cursor_x + available_width - label.width
                    else:
                        label.x = self._cursor_x
                label.y = self._cursor_y
                label.height = label_height * self.scale_y
                label.alignment = self.alignment
                self._cursor_y -= label.height + self._get_spacing()
            else:
                label.x = self._cursor_x
                label.y = self._cursor_y
                label.width = label_width * self.scale_x
                label.height = label_height * self.scale_y
                self._cursor_x += label.width + self._get_spacing()

            self._register_interactive_item(label)
            self._elements.append(label)


    def _add_item(self, item: LayoutItem) -> None:
        """アイテムを追加"""
        # heading があれば先にラベルを追加
        if self._heading:
            self._insert_heading_label()

        self._dirty = True  # アイテム追加でレイアウト再計算が必要
        self._assign_layout_path(item, self._get_item_kind(item))
        item_width, item_height = item.calc_size(self.style)
        available_width = self._get_available_width()

        if self.direction == Direction.VERTICAL:
            # alignment に応じて幅と位置を計算
            if self.alignment == Alignment.EXPAND:
                # EXPAND: 利用可能幅いっぱいに拡張
                # scale_x は EXPAND では見えにくいので、幅には適用しない
                item.width = available_width
                item.x = self._cursor_x
            else:
                # LEFT/CENTER/RIGHT: 自然サイズを維持
                item.width = item_width * self.scale_x
                if self.alignment == Alignment.CENTER:
                    item.x = self._cursor_x + (available_width - item.width) / 2
                elif self.alignment == Alignment.RIGHT:
                    item.x = self._cursor_x + available_width - item.width
                else:  # LEFT
                    item.x = self._cursor_x

            item.y = self._cursor_y
            item.height = item_height * self.scale_y

            # LabelItem に alignment を継承
            if hasattr(item, 'alignment'):
                item.alignment = self.alignment

            self._cursor_y -= item.height + self._get_spacing()
        else:
            # 水平レイアウト
            item.x = self._cursor_x
            item.y = self._cursor_y
            item.width = item_width * self.scale_x
            item.height = item_height * self.scale_y

            self._cursor_x += item.width + self._get_spacing()

        self._register_interactive_item(item)
        self._elements.append(item)  # Phase 1: _elements に統合
