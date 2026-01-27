# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Input Widgets
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite, radians
from typing import TYPE_CHECKING, Callable, Optional

from ..style import GPULayoutStyle, WidgetType
from ..drawing import GPUDrawing, BLFDrawing
from .base import LayoutItem


def _scale_drag_step_for_units(step: float, subtype: str) -> float:
    from ..rna_utils import _SUBTYPE_UNIT_CATEGORY, _unit_settings_from_context

    unit_category = _SUBTYPE_UNIT_CATEGORY.get((subtype or "NONE").upper())
    unit_settings = _unit_settings_from_context()
    if unit_settings is None:
        return step

    if unit_category in {"LENGTH", "VELOCITY", "ACCELERATION"} and unit_settings.system != "NONE":
        scale = float(getattr(unit_settings, "scale_length", 1.0)) or 1.0
        step = step * scale
    elif unit_category in {"AREA", "POWER"} and unit_settings.system != "NONE":
        scale = float(getattr(unit_settings, "scale_length", 1.0)) or 1.0
        step = step * (scale ** 2)
    elif unit_category in {"VOLUME", "MASS"} and unit_settings.system != "NONE":
        scale = float(getattr(unit_settings, "scale_length", 1.0)) or 1.0
        step = step * (scale ** 3)

    if unit_category == "ROTATION" and unit_settings.system_rotation != "RADIANS":
        step = radians(step)

    return step


def _snap_value(value: float,
                *,
                min_val: float,
                max_val: float,
                is_int: bool,
                small: bool,
                subtype: str) -> float:
    if not isfinite(min_val) or not isfinite(max_val):
        return value

    from ..rna_utils import _SUBTYPE_UNIT_CATEGORY, _unit_settings_from_context

    unit_category = _SUBTYPE_UNIT_CATEGORY.get((subtype or "NONE").upper())
    unit_settings = _unit_settings_from_context()

    fac = 1.0
    if unit_settings is not None:
        if unit_category == "ROTATION" and unit_settings.system_rotation != "RADIANS":
            fac = radians(1.0)
        elif unit_settings.system != "NONE":
            scale = float(getattr(unit_settings, "scale_length", 1.0)) or 1.0
            if unit_category in {"LENGTH", "VELOCITY", "ACCELERATION"}:
                fac = 1.0 / scale
            elif unit_category in {"AREA", "POWER"}:
                fac = 1.0 / (scale ** 2)
            elif unit_category in {"VOLUME", "MASS"}:
                fac = 1.0 / (scale ** 3)

    value_unit = value / fac
    min_unit = min_val / fac
    max_unit = max_val / fac
    softrange = max_unit - min_unit
    if softrange <= 0:
        return value

    if softrange >= 21.0:
        if not (unit_category == "ROTATION" and unit_settings and
                getattr(unit_settings, "system_rotation", "RADIANS") != "RADIANS"):
            softrange = 20.0

    if is_int:
        snap = 100 if small else 10
        return round(value_unit / snap) * snap * fac

    if softrange < 2.10:
        snap = 0.01 if small else 0.1
    elif softrange < 21.0:
        snap = 0.1 if small else 1.0
    else:
        snap = 1.0 if small else 10.0

    return round(value_unit / snap) * snap * fac

if TYPE_CHECKING:
    from ..interactive import ItemRenderState


@dataclass
class SliderItem(LayoutItem):
    """
    スライダー（wcol_numslider テーマ対応）

    数値の範囲選択に使用。ドラッグで値を変更。

    Attributes:
        value: 現在値
        min_val: 最小値
        max_val: 最大値
        precision: 表示精度（小数点以下の桁数）
        step: ステップ値（表示精度に使用）
        text: ラベルテキスト（空の場合は値のみ表示）
        on_change: 値変更時のコールバック
    """
    value: float = 0.0
    min_val: float = 0.0
    max_val: float = 1.0
    step: float = 0.01
    precision: int = 2
    subtype: str = "NONE"
    text: str = ""
    is_int: bool = False
    on_change: Optional[Callable[[float], None]] = None

    # 状態（layout 側から設定される）
    _hovered: bool = field(default=False, repr=False)
    _dragging: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """スライダーのサイズを計算"""
        text_size = style.scaled_text_size()
        display_text = self._get_display_text()
        text_w, _ = BLFDrawing.get_text_dimensions(display_text, text_size)
        padding = style.scaled_padding()
        # 最小幅を確保（テキスト + パディング、または 100px）
        min_width = max(text_w + padding * 4, style.ui_scale(100))
        return (max(self.width, min_width), style.scaled_item_height())

    def _get_display_text(self) -> str:
        """表示用テキストを生成"""
        from ..rna_utils import format_numeric_value

        value_str = format_numeric_value(
            self.value,
            self.subtype,
            self.precision,
            step=self.step,
            max_value=self.max_val,
        )
        if self.text:
            return f"{self.text}: {value_str}"
        return value_str

    def _get_normalized_value(self) -> float:
        """値を 0.0〜1.0 の範囲に正規化（クランプ付き）"""
        if self.max_val == self.min_val:
            return 0.0
        normalized = (self.value - self.min_val) / (self.max_val - self.min_val)
        return max(0.0, min(1.0, normalized))  # 範囲外の値をクランプ

    def get_value(self) -> float:
        """ValueWidget Protocol 準拠"""
        return self.value

    def set_value(self, value: float) -> None:
        """ValueWidget Protocol 準拠"""
        self.value = max(self.min_val, min(self.max_val, value))

    def set_value_from_position(self,
                                x: float,
                                *,
                                shift: bool = False,
                                ctrl: bool = False,
                                alt: bool = False) -> None:
        """X 座標から値を設定（ドラッグ時に使用）"""
        # 幅が 0 以下の場合は安全にスキップ
        if self.width <= 0:
            return
        # 相対位置を計算
        rel_x = (x - self.x) / self.width
        rel_x = max(0.0, min(1.0, rel_x))
        # 値に変換
        target_value = self.min_val + rel_x * (self.max_val - self.min_val)
        speed = 0.1 if shift else 1.0
        if alt:
            speed *= 10.0
        new_value = self.value + (target_value - self.value) * speed
        if ctrl:
            new_value = _snap_value(
                new_value,
                min_val=self.min_val,
                max_val=self.max_val,
                is_int=self.is_int,
                small=shift,
                subtype=self.subtype,
            )
        if self.is_int:
            new_value = round(new_value)
        new_value = max(self.min_val, min(self.max_val, new_value))
        if new_value != self.value:
            self.value = new_value
            if self.on_change:
                self.on_change(new_value)

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """スライダーを描画（wcol_numslider テーマ使用）"""
        if not self.visible:
            return

        # テーマカラーを取得
        wcol = style.get_widget_colors(WidgetType.SLIDER)
        if wcol is None:
            # フォールバック: 通常のボタンスタイルで描画
            self._draw_fallback(style, state)
            return

        # 状態の判定
        hovered = state.hovered if state else self._hovered
        dragging = state.pressed if state else self._dragging
        enabled = state.enabled if state else self.enabled

        # 角丸半径を計算（Blender 準拠: roundness × height × 0.5）
        radius = int(wcol.roundness * self.height * 0.5)

        # === 1. 背景描画 ===
        if dragging:
            bg_color = wcol.inner_sel
        elif hovered:
            # ホバー時は inner を少し明るく
            bg_color = tuple(min(1.0, c * 1.15) for c in wcol.inner[:3]) + (wcol.inner[3],)
        else:
            bg_color = wcol.inner

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            radius, bg_color, self.corners
        )

        # === 2. 値バー描画（item カラー） ===
        normalized = self._get_normalized_value()
        if normalized > 0.001:  # 0% に近い場合はスキップ
            bar_width = self.width * normalized

            # 値バー用 corners を計算
            # 左側は self.corners を継承、右側は 100% 未満なら直角
            if normalized >= 0.99:
                bar_corners = self.corners  # フルなので親と同じ
            else:
                # 右側を直角に（値バーが背景より短い）
                # corners: (bottomLeft, topLeft, topRight, bottomRight)
                bar_corners = (self.corners[0], self.corners[1], False, False)

            item_color = wcol.item if enabled else tuple(c * 0.5 for c in wcol.item[:3]) + (wcol.item[3],)
            GPUDrawing.draw_rounded_rect(
                self.x, self.y, bar_width, self.height,
                radius, item_color, bar_corners
            )

        # === 3. アウトライン描画 ===
        # ドラッグ中は outline_sel を使用
        base_outline = wcol.outline_sel if dragging else wcol.outline
        outline_color = base_outline if enabled else tuple(c * 0.5 for c in base_outline[:3]) + (base_outline[3],)
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # === 4. テキスト描画 ===
        text_color = wcol.text_sel if dragging else wcol.text
        if not enabled:
            text_color = tuple(c * 0.5 for c in text_color[:3]) + (text_color[3],)

        display_text = self._get_display_text()
        text_size = style.scaled_text_size()
        available_width = max(0.0, self.width - style.scaled_padding() * 2)
        display_text = BLFDrawing.get_text_with_ellipsis(display_text, available_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)

        # 中央揃え
        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)

    def _draw_fallback(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """テーマがない場合のフォールバック描画"""
        hovered = state.hovered if state else self._hovered
        dragging = state.pressed if state else self._dragging
        enabled = state.enabled if state else self.enabled

        # 角丸半径（デフォルト roundness 0.4、Blender 準拠: roundness × height × 0.5）
        radius = int(0.4 * self.height * 0.5)

        # 背景
        bg_color = style.button_press_color if dragging else (
            style.button_hover_color if hovered else style.button_color
        )
        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(self.x, self.y, self.width, self.height, radius, bg_color, self.corners)

        # 値バー
        normalized = self._get_normalized_value()
        if normalized > 0.001:
            bar_width = self.width * normalized
            bar_color = style.highlight_color if enabled else tuple(c * 0.5 for c in style.highlight_color[:3]) + (style.highlight_color[3],)

            # 値バー用 corners（左側は継承、右側は 100% 未満なら直角）
            if normalized >= 0.99:
                bar_corners = self.corners
            else:
                bar_corners = (self.corners[0], self.corners[1], False, False)

            GPUDrawing.draw_rounded_rect(self.x, self.y, bar_width, self.height, radius, bar_color, bar_corners)

        # アウトライン
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, style.outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # テキスト
        text_color = style.button_text_color if enabled else style.text_color_disabled
        display_text = self._get_display_text()
        text_size = style.scaled_text_size()
        available_width = max(0.0, self.width - style.scaled_padding() * 2)
        display_text = BLFDrawing.get_text_with_ellipsis(display_text, available_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)
        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2
        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)


@dataclass
class NumberItem(LayoutItem):
    """
    数値フィールド（wcol_num テーマ対応）

    数値の表示・編集に使用。ドラッグまたは増減ボタンで値を変更。

    Attributes:
        value: 現在値
        min_val: 最小値
        max_val: 最大値
        step: ドラッグ時の変化量（ピクセルあたり）
        precision: 表示精度（小数点以下の桁数）
        text: ラベルテキスト（空の場合は値のみ表示）
        show_buttons: 増減ボタン（◀ ▶）を表示するか
        on_change: 値変更時のコールバック
    """
    value: float = 0.0
    min_val: float = -float('inf')
    max_val: float = float('inf')
    step: float = 0.01
    precision: int = 2
    subtype: str = "NONE"
    text: str = ""
    is_int: bool = False
    show_buttons: bool = False
    on_change: Optional[Callable[[float], None]] = None

    # 状態（layout 側から設定される）
    _hovered: bool = field(default=False, repr=False)
    _dragging: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """数値フィールドのサイズを計算"""
        text_size = style.scaled_text_size()
        display_text = self._get_display_text()
        text_w, _ = BLFDrawing.get_text_dimensions(display_text, text_size)
        padding = style.scaled_padding()
        button_width = self._get_button_width(style) if self.show_buttons else 0
        # 最小幅を確保（テキスト + パディング + ボタン、または 80px）
        min_width = max(text_w + padding * 4 + button_width * 2, style.ui_scale(80))
        return (max(self.width, min_width), style.scaled_item_height())

    def _get_display_text(self) -> str:
        """表示用テキストを生成"""
        from ..rna_utils import format_numeric_value

        value_str = format_numeric_value(
            self.value,
            self.subtype,
            self.precision,
            step=self.step,
            max_value=self.max_val,
        )
        if self.text:
            return f"{self.text}: {value_str}"
        return value_str

    def _get_button_width(self, style: GPULayoutStyle) -> float:
        """増減ボタンの幅を取得"""
        return style.ui_scale(16)

    def get_value(self) -> float:
        """ValueWidget Protocol 準拠"""
        return self.value

    def set_value(self, value: float) -> None:
        """ValueWidget Protocol 準拠"""
        self.value = max(self.min_val, min(self.max_val, value))

    def _calc_drag_step(self, *, shift: bool, alt: bool) -> float:
        from ..rna_utils import UI_PRECISION_FLOAT_SCALE

        step = float(self.step)
        if not self.is_int:
            step *= UI_PRECISION_FLOAT_SCALE
        step = _scale_drag_step_for_units(step, self.subtype)
        if shift:
            step *= 0.1
        if alt:
            step *= 10.0
        return step

    def set_value_from_delta(self,
                             dx: float,
                             *,
                             shift: bool = False,
                             ctrl: bool = False,
                             alt: bool = False) -> None:
        """ドラッグ移動量から値を設定"""
        step = self._calc_drag_step(shift=shift, alt=alt)
        new_value = self.value + dx * step
        if ctrl:
            new_value = _snap_value(
                new_value,
                min_val=self.min_val,
                max_val=self.max_val,
                is_int=self.is_int,
                small=shift,
                subtype=self.subtype,
            )
        if self.is_int:
            new_value = round(new_value)
        # 範囲内にクランプ
        new_value = max(self.min_val, min(self.max_val, new_value))
        if new_value != self.value:
            self.value = new_value
            if self.on_change:
                self.on_change(new_value)

    def increment(self) -> None:
        """値を1ステップ増加"""
        # step の 10 倍を増分として使用（ボタン用）
        step = self._calc_drag_step(shift=False, alt=False)
        new_value = self.value + step * 10
        new_value = min(self.max_val, new_value)
        if new_value != self.value:
            self.value = new_value
            if self.on_change:
                self.on_change(new_value)

    def decrement(self) -> None:
        """値を1ステップ減少"""
        step = self._calc_drag_step(shift=False, alt=False)
        new_value = self.value - step * 10
        new_value = max(self.min_val, new_value)
        if new_value != self.value:
            self.value = new_value
            if self.on_change:
                self.on_change(new_value)

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """数値フィールドを描画（wcol_num テーマ使用）"""
        if not self.visible:
            return

        # テーマカラーを取得
        wcol = style.get_widget_colors(WidgetType.NUMBER)
        if wcol is None:
            # フォールバック: 通常のボタンスタイルで描画
            self._draw_fallback(style, state)
            return

        # 状態の判定
        hovered = state.hovered if state else self._hovered
        dragging = state.pressed if state else self._dragging
        enabled = state.enabled if state else self.enabled

        # 角丸半径を計算（Blender 準拠: roundness × height × 0.5）
        radius = int(wcol.roundness * self.height * 0.5)

        # === 1. 背景描画 ===
        if dragging:
            bg_color = wcol.inner_sel
        elif hovered:
            # ホバー時は inner を少し明るく
            bg_color = tuple(min(1.0, c * 1.15) for c in wcol.inner[:3]) + (wcol.inner[3],)
        else:
            bg_color = wcol.inner

        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            radius, bg_color, self.corners
        )

        # === 2. アウトライン描画 ===
        base_outline = wcol.outline_sel if dragging else wcol.outline
        outline_color = base_outline if enabled else tuple(c * 0.5 for c in base_outline[:3]) + (base_outline[3],)
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # === 3. 増減ボタン描画（オプション） ===
        button_width = 0
        if self.show_buttons:
            button_width = self._get_button_width(style)
            self._draw_buttons(style, wcol, enabled, button_width)

        # === 4. テキスト描画 ===
        text_color = wcol.text_sel if dragging else wcol.text
        if not enabled:
            text_color = tuple(c * 0.5 for c in text_color[:3]) + (text_color[3],)

        # 中央揃え（ボタンを考慮）
        text_area_x = self.x + button_width
        text_area_width = self.width - button_width * 2

        display_text = self._get_display_text()
        text_size = style.scaled_text_size()
        available_width = max(0.0, text_area_width - style.scaled_padding() * 2)
        display_text = BLFDrawing.get_text_with_ellipsis(display_text, available_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)
        text_x = text_area_x + (text_area_width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        # クリップ矩形（ボタン領域を除く）
        clip_rect = BLFDrawing.calc_clip_rect(
            text_area_x, self.y, text_area_width, self.height, 0
        )
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)

    def _draw_buttons(self, style: GPULayoutStyle, wcol: ThemeWidgetColors,
                      enabled: bool, button_width: float) -> None:
        """増減ボタンを描画"""
        # ボタンの高さはアイテムの高さと同じ
        button_height = self.height

        # 左ボタン（◀ 減少）
        left_x = self.x
        left_center_x = left_x + button_width / 2
        center_y = self.y - self.height / 2

        # 右ボタン（▶ 増加）
        right_x = self.x + self.width - button_width
        right_center_x = right_x + button_width / 2

        # 三角形のサイズ
        tri_size = style.ui_scale(5)
        tri_color = wcol.text if enabled else tuple(c * 0.5 for c in wcol.text[:3]) + (wcol.text[3],)

        # 左三角形（◀）
        GPUDrawing.draw_triangle(
            left_center_x + tri_size / 2, center_y - tri_size,
            left_center_x + tri_size / 2, center_y + tri_size,
            left_center_x - tri_size / 2, center_y,
            tri_color
        )

        # 右三角形（▶）
        GPUDrawing.draw_triangle(
            right_center_x - tri_size / 2, center_y - tri_size,
            right_center_x - tri_size / 2, center_y + tri_size,
            right_center_x + tri_size / 2, center_y,
            tri_color
        )

    def _draw_fallback(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """テーマがない場合のフォールバック描画"""
        hovered = state.hovered if state else self._hovered
        dragging = state.pressed if state else self._dragging
        enabled = state.enabled if state else self.enabled

        # 角丸半径（デフォルト roundness 0.4、Blender 準拠: roundness × height × 0.5）
        radius = int(0.4 * self.height * 0.5)

        # 背景
        bg_color = style.button_press_color if dragging else (
            style.button_hover_color if hovered else style.button_color
        )
        if not enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        GPUDrawing.draw_rounded_rect(self.x, self.y, self.width, self.height, radius, bg_color, self.corners)

        # アウトライン
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            radius, style.outline_color,
            line_width=style.line_width(),
            corners=self.corners
        )

        # テキスト
        text_color = style.button_text_color if enabled else style.text_color_disabled
        display_text = self._get_display_text()
        text_size = style.scaled_text_size()
        available_width = max(0.0, self.width - style.scaled_padding() * 2)
        display_text = BLFDrawing.get_text_with_ellipsis(display_text, available_width, text_size)
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, text_size)
        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2
        clip_rect = self.get_clip_rect()
        BLFDrawing.draw_text_clipped(text_x, text_y, display_text, text_color, text_size, clip_rect)


@dataclass
class ColorItem(LayoutItem):
    """
    カラースウォッチ（色の表示・選択ウィジェット）

    Blender スタイルの横長カラーバーを描画。
    左側に RGB（不透明）、右側にチェッカー+RGBA（アルファ表示）。

    現在の実装:
        - use_property_split=True スタイル: ラベルを固定比率領域（split_factor）に右揃え
        - カラーバーは残りの領域に配置（整列される）

    Attributes:
        color: 表示する色 (R, G, B, A) - 各値は 0.0-1.0
        text: ラベルテキスト（空の場合はカラーバーのみ）
        on_click: クリック時のコールバック

    TODO(将来の拡張):
        - use_property_split=False スタイル: ラベル+コロンを上の行、カラーバーを下の行（2行構成）
        - layout.prop() との統合時に HitRect をカラーバー部分のみに設定（get_bar_rect() 使用）
    """
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    text: str = ""
    on_click: Optional[Callable[[], None]] = None
    _hovered: bool = field(default=False, repr=False)

    # カラーバーの高さ比率（アイテム高さに対して）
    # 1.0 = フル高さ（他のウィジェットと統一）
    BAR_HEIGHT_RATIO: float = 1.0

    def _get_bar_height(self) -> float:
        """カラーバーの高さを取得

        Note:
            self.height は layout.py で scale_y を適用済みなので、
            ここでは self.height を使用して scale_y に追従する。
        """
        return self.height * self.BAR_HEIGHT_RATIO

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """サイズを計算

        Note:
            width は親レイアウトから設定される（row 全体に広がる）。
            ラベル領域は split_factor で固定比率（約40%）として確保される。
        """
        height = style.scaled_item_height()
        # width は親レイアウトから設定される（row 全体に広がる）
        # デフォルトは最小幅として適当な値を返す
        min_width = style.scaled_item_height() * 4  # 最小幅
        return (self.width if self.width > 0 else min_width, height)

    @property
    def value(self) -> tuple[float, float, float, float]:
        """ValueWidget Protocol 準拠"""
        return self.color

    @value.setter
    def value(self, value: tuple[float, float, float, float]) -> None:
        self.set_value(value)

    def get_value(self) -> tuple[float, float, float, float]:
        """ValueWidget Protocol 準拠"""
        return self.color

    def set_value(self, value: tuple[float, float, float, float]) -> None:
        """ValueWidget Protocol 準拠"""
        if isinstance(value, (list, tuple)):
            if len(value) == 3:
                color = (*value, 1.0)
            elif len(value) >= 4:
                color = tuple(value[:4])
            else:
                color = (1.0, 1.0, 1.0, 1.0)
        else:
            color = (1.0, 1.0, 1.0, 1.0)

        def _clamp(channel: float) -> float:
            return max(0.0, min(1.0, float(channel)))

        self.color = (
            _clamp(color[0]),
            _clamp(color[1]),
            _clamp(color[2]),
            _clamp(color[3]),
        )

    def draw(self, style: GPULayoutStyle, state: Optional[ItemRenderState] = None) -> None:
        """描画

        Blender スタイル: [  RGB (不透明)  |  RGBA (チェッカー)  ]
        """
        if not self.visible:
            return

        hovered = state.hovered if state else self._hovered
        enabled = state.enabled if state else self.enabled

        # テーマカラーを取得（角丸計算用）
        wcol = style.get_widget_colors(WidgetType.REGULAR)

        bar_height = self._get_bar_height()
        spacing = style.scaled_spacing()

        # use_property_split=True スタイル: ラベルを固定比率領域に右揃え
        if self.text:
            text_size = style.scaled_text_size()
            label_text = self.text + ":"

            # 固定比率でラベル領域を確保（split_factor: 約40%）
            label_region_width = self.width * style.split_factor

            # テキストがラベル領域に収まるか確認、収まらない場合は省略
            available_width = label_region_width - spacing * 2

            # ラベル領域が十分にある場合のみテキストを描画
            if available_width > 0:
                label_text = BLFDrawing.truncate_text(label_text, text_size, available_width)
                text_w, text_h = BLFDrawing.get_text_dimensions(label_text, text_size)

                # テキスト幅がラベル領域に収まる場合のみ描画
                if text_w <= available_width:
                    text_color = style.text_color if enabled else style.text_color_disabled
                    text_y = self.y - (self.height + text_h) / 2
                    text_x = self.x + label_region_width - text_w - spacing  # 右揃え
                    # 左端を超えないようにクリップ
                    text_x = max(text_x, self.x + spacing)
                    BLFDrawing.draw_text(text_x, text_y, label_text, text_color, text_size)

            bar_x = self.x + label_region_width
            bar_width = self.width - label_region_width
        else:
            bar_x = self.x
            bar_width = self.width

        # カラーバーの位置（垂直中央揃え）
        bar_y = self.y - (self.height - bar_height) / 2

        # 角丸半径（Blender 準拠: roundness × height × 0.5）
        if wcol is not None:
            radius = int(wcol.roundness * bar_height * 0.5)
        else:
            radius = int(0.4 * bar_height * 0.5)

        # バー幅が小さすぎる場合は描画しない
        if bar_width < bar_height:
            return

        # === Blender スタイル: 左=RGB、右=RGBA(チェッカー) ===
        # 左右の分割位置（50:50）
        rgb_width = bar_width / 2
        alpha_width = bar_width - rgb_width

        # 色の計算
        rgb_color = (self.color[0], self.color[1], self.color[2], 1.0)  # 不透明
        rgba_color = self.color  # アルファ込み

        if not enabled:
            # 無効時は彩度を下げる
            gray = 0.299 * self.color[0] + 0.587 * self.color[1] + 0.114 * self.color[2]
            rgb_color = (
                self.color[0] * 0.5 + gray * 0.5,
                self.color[1] * 0.5 + gray * 0.5,
                self.color[2] * 0.5 + gray * 0.5,
                1.0
            )
            rgba_color = (
                rgb_color[0], rgb_color[1], rgb_color[2],
                self.color[3] * 0.5
            )

        # === 1. 右側: チェッカーパターン背景 ===
        alpha_x = bar_x + rgb_width
        self._draw_checker_pattern_rect(
            alpha_x, bar_y, alpha_width, bar_height,
            radius, style,
            corners=(False, False, True, True)  # 右側のみ角丸
        )

        # === 2. 右側: RGBA カラー（チェッカーの上に半透明で描画） ===
        GPUDrawing.draw_rounded_rect(
            alpha_x, bar_y, alpha_width, bar_height,
            radius, rgba_color,
            corners=(False, False, True, True)
        )

        # === 3. 左側: RGB カラー（不透明） ===
        GPUDrawing.draw_rounded_rect(
            bar_x, bar_y, rgb_width, bar_height,
            radius, rgb_color,
            corners=(True, True, False, False)  # 左側のみ角丸
        )

        # === 4. アウトライン（全体） ===
        if hovered:
            outline_color = style.highlight_color
            line_width = style.line_width() * 1.5
        else:
            outline_color = style.outline_color
            line_width = style.line_width()

        if not enabled:
            outline_color = tuple(c * 0.5 for c in outline_color[:3]) + (outline_color[3],)

        GPUDrawing.draw_rounded_rect_outline(
            bar_x, bar_y, bar_width, bar_height,
            radius, outline_color,
            line_width=line_width
        )

    def _draw_checker_pattern_rect(self, x: float, y: float, width: float, height: float,
                                    radius: int, style: GPULayoutStyle,
                                    corners: tuple[bool, bool, bool, bool] = (True, True, True, True)) -> None:
        """チェッカーパターンを矩形領域に描画"""
        cell_size = max(4, style.ui_scale(4))  # 4px (scaled)
        light_color = (0.7, 0.7, 0.7, 1.0)
        dark_color = (0.4, 0.4, 0.4, 1.0)

        # まず背景色（明るい方）で角丸矩形を塗りつぶす
        GPUDrawing.draw_rounded_rect(x, y, width, height, radius, light_color, corners)

        # 暗いセルを描画（簡易版 - 角丸クリッピングなし）
        # TODO: 正確な角丸クリッピングは将来シェーダーで実装
        margin = radius * 0.3
        inner_x = x + margin
        inner_y = y - margin
        inner_width = width - margin * 2
        inner_height = height - margin * 2

        cols = int(inner_width / cell_size) + 1
        rows = int(inner_height / cell_size) + 1

        for row in range(rows):
            for col in range(cols):
                if (row + col) % 2 == 1:
                    cell_x = inner_x + col * cell_size
                    cell_y = inner_y - row * cell_size
                    # 範囲内にクリップ
                    cell_w = min(cell_size, inner_x + inner_width - cell_x)
                    cell_h = min(cell_size, cell_y - (inner_y - inner_height))
                    if cell_w > 0 and cell_h > 0:
                        GPUDrawing.draw_rect(cell_x, cell_y, cell_w, cell_h, dark_color)

    def click(self) -> None:
        """クリック処理

        TODO(layout.prop統合):
            - ヒットポイントはカラーバー部分のみ
            - ラベル部分はクリック対象外
            - layout.py の _register_interactive_item で HitRect を調整
        """
        if self.enabled and self.on_click:
            self.on_click()

    def get_bar_rect(self, style: GPULayoutStyle) -> tuple[float, float, float, float]:
        """カラーバー部分の矩形を取得（ヒットテスト用）

        Returns:
            (x, y, width, height) - カラーバーの位置とサイズ

        TODO(layout.prop統合):
            - _register_interactive_item でこのメソッドを使って HitRect を設定
        """
        bar_height = self._get_bar_height()

        # use_property_split=True スタイル: 固定比率でバー位置を計算
        if self.text:
            label_region_width = self.width * style.split_factor
            bar_x = self.x + label_region_width
            bar_width = self.width - label_region_width
        else:
            bar_x = self.x
            bar_width = self.width

        bar_y = self.y - (self.height - bar_height) / 2

        return (bar_x, bar_y, bar_width, bar_height)
