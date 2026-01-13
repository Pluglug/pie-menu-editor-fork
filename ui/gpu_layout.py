# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout System - Blender UILayout API を模した GPU 描画レイアウト

Phase 1: 読み取り専用レイアウト（ツールチップ向け）
Phase 2: インタラクティブ要素（ボタン、トグル）

使用例:
    layout = GPULayout(x=100, y=100, width=300)
    layout.label(text="Hello", icon='INFO')
    row = layout.row()
    row.label(text="Left")
    row.label(text="Right")
    layout.separator()
    layout.draw()

参考: bl_ui_widgets (GPL-3.0) https://github.com/mmmrqs/bl_ui_widgets
"""

from __future__ import annotations

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional, Union
from math import pi, cos, sin
from enum import Enum, auto

if TYPE_CHECKING:
    from bpy.types import Event


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

# Blender 4.0+ でシェーダー名が変更
_SHADER_NAME = 'UNIFORM_COLOR' if bpy.app.version >= (4, 0, 0) else '2D_UNIFORM_COLOR'

# デフォルトフォント ID
_FONT_ID = 0


class Direction(Enum):
    """レイアウト方向"""
    VERTICAL = auto()
    HORIZONTAL = auto()


class Alignment(Enum):
    """
    アラインメント

    - EXPAND: 利用可能幅いっぱいに拡張（デフォルト）
    - LEFT: 自然サイズを維持し、左寄せ
    - CENTER: 自然サイズを維持し、中央寄せ
    - RIGHT: 自然サイズを維持し、右寄せ
    """
    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()
    EXPAND = auto()


# ═══════════════════════════════════════════════════════════════════════════════
# Style - Blender テーマ統合
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GPULayoutStyle:
    """
    レイアウトスタイル定義

    Blender テーマから自動取得、または個別にオーバーライド可能
    """
    # 背景（通常状態）
    bg_color: tuple[float, float, float, float] = (0.2, 0.2, 0.2, 0.95)
    outline_color: tuple[float, float, float, float] = (0.1, 0.1, 0.1, 1.0)

    # 背景（選択状態）
    bg_color_sel: tuple[float, float, float, float] = (0.3, 0.5, 0.8, 0.95)
    outline_color_sel: tuple[float, float, float, float] = (0.2, 0.4, 0.7, 1.0)

    # アイテム色（メニューアイテム、チェックマーク等）
    item_color: tuple[float, float, float, float] = (0.4, 0.4, 0.4, 1.0)

    # テキスト（通常状態）
    text_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    text_color_secondary: tuple[float, float, float, float] = (0.7, 0.7, 0.7, 1.0)
    text_color_disabled: tuple[float, float, float, float] = (0.5, 0.5, 0.5, 1.0)

    # テキスト（選択状態）
    text_color_sel: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)

    text_size: int = 13

    # ボタン
    button_color: tuple[float, float, float, float] = (0.3, 0.3, 0.3, 1.0)
    button_hover_color: tuple[float, float, float, float] = (0.4, 0.4, 0.4, 1.0)
    button_press_color: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 1.0)
    button_text_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)

    # 特殊色
    alert_color: tuple[float, float, float, float] = (0.8, 0.2, 0.2, 1.0)
    highlight_color: tuple[float, float, float, float] = (0.3, 0.5, 0.8, 1.0)

    # 区切り線
    separator_color: tuple[float, float, float, float] = (0.15, 0.15, 0.15, 1.0)

    # レイアウト
    padding: int = 10
    spacing: int = 4
    item_height: int = 22
    border_radius: int = 6
    roundness: float = 0.4  # 0.0-1.0、テーマから取得

    # ドロップシャドウ（パネル/メニュー用）
    shadow_enabled: bool = True
    shadow_color: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.3)
    shadow_offset: tuple[int, int] = (4, -4)
    shadow_blur: int = 8  # ぼかし半径

    # テキストシャドウ
    text_shadow_enabled: bool = True
    text_shadow_color: float = 0.0  # 0.0 = 黒, 1.0 = 白
    text_shadow_alpha: float = 0.5
    text_shadow_offset: tuple[int, int] = (1, -1)

    @classmethod
    def from_blender_theme(cls, style_name: str = 'TOOLTIP') -> GPULayoutStyle:
        """
        Blender テーマから自動取得

        Args:
            style_name: 'TOOLTIP', 'BOX', 'PANEL', 'REGULAR', 'PIE_MENU', 'MENU', 'TOOL'

        Note:
            - preferences.view.ui_scale: ユーザーが設定するスケール値 (0.5-6.0)
            - preferences.system.ui_scale: OS DPI × ユーザー設定 = 最終スケール
            - preferences.system.ui_line_width: 計算されたライン太さ（ピクセル）
        """
        try:
            prefs = bpy.context.preferences
            theme = prefs.themes[0]
            ui = theme.user_interface
            ui_styles = prefs.ui_styles[0]

            # スタイル名からテーマ属性を取得
            style_map = {
                'TOOLTIP': 'wcol_tooltip',
                'BOX': 'wcol_box',
                'PANEL': 'wcol_regular',
                'REGULAR': 'wcol_regular',
                'TOOL': 'wcol_tool',
                'RADIO': 'wcol_radio',
                'PIE_MENU': 'wcol_pie_menu',
                'MENU': 'wcol_menu',
                'MENU_ITEM': 'wcol_menu_item',
                'TOGGLE': 'wcol_toggle',
                'OPTION': 'wcol_option',
                'NUM': 'wcol_num',
                'NUMSLIDER': 'wcol_numslider',
            }
            wcol_name = style_map.get(style_name, 'wcol_tooltip')
            wcol = getattr(ui, wcol_name)

            # ボタン用のカラーを取得（wcol_tool を使用）
            wcol_button = ui.wcol_tool

            # ヘルパー関数: 色を RGBA に変換
            def to_rgba(color, alpha: float = 1.0) -> tuple[float, float, float, float]:
                """色を RGBA タプルに変換"""
                c = tuple(color)
                if len(c) == 3:
                    return c + (alpha,)
                return c

            # ThemeFontStyle からシャドウ設定を取得
            font_style = ui_styles.widget
            shadow_type = font_style.shadow  # 0=none, 3=shadow, 5=blur, 6=outline
            shadow_enabled = shadow_type > 0

            # roundness から border_radius を計算（0-1 → ピクセル値）
            # roundness 1.0 で約 10px、スケールを考慮
            roundness_val = wcol.roundness
            base_radius = int(roundness_val * 10)

            return cls(
                # 背景（通常状態）
                bg_color=to_rgba(wcol.inner),
                outline_color=to_rgba(wcol.outline),

                # 背景（選択状態）
                bg_color_sel=to_rgba(wcol.inner_sel),
                outline_color_sel=to_rgba(wcol.outline_sel) if hasattr(wcol, 'outline_sel') else to_rgba(wcol.outline),

                # アイテム色
                item_color=to_rgba(wcol.item),

                # テキスト（通常状態）
                text_color=to_rgba(wcol.text),
                text_color_secondary=to_rgba(wcol.text, 0.7),  # メインテキストの 70%
                text_color_disabled=to_rgba(wcol.text, 0.4),   # メインテキストの 40%

                # テキスト（選択状態）
                text_color_sel=to_rgba(wcol.text_sel),

                text_size=int(font_style.points),

                # ボタン（wcol_tool から取得）
                button_color=to_rgba(wcol_button.inner),
                button_hover_color=to_rgba(wcol_button.inner_sel),
                button_press_color=to_rgba(wcol_button.item),
                button_text_color=to_rgba(wcol_button.text),

                # 特殊色
                alert_color=(0.8, 0.2, 0.2, 1.0),  # 赤系（Blender の alert は固定色）
                highlight_color=to_rgba(wcol.inner_sel),

                # 区切り線（アウトラインより少し暗く）
                separator_color=to_rgba(wcol.outline, 0.5),

                # レイアウト
                border_radius=max(4, base_radius),
                roundness=roundness_val,

                # ドロップシャドウ（widget_emboss を使用）
                shadow_color=to_rgba(ui.widget_emboss),

                # テキストシャドウ（ThemeFontStyle から取得）
                text_shadow_enabled=shadow_enabled,
                text_shadow_color=font_style.shadow_value,  # 0.0=黒, 1.0=白
                text_shadow_alpha=font_style.shadow_alpha,
                text_shadow_offset=(font_style.shadow_offset_x, font_style.shadow_offset_y),
            )
        except Exception:
            # フォールバック
            return cls()

    def ui_scale(self, value: float) -> float:
        """
        UI スケールを適用

        Note:
            system.ui_scale は OS DPI も考慮した最終値。
            view.ui_scale はユーザー設定値のみ。
            アドオンでは system.ui_scale の使用が推奨される。
        """
        return value * bpy.context.preferences.system.ui_scale

    def line_width(self) -> float:
        """
        推奨ライン太さを取得

        OS 設定と UI スケールに基づいた、カスタム UI 要素用の推奨値。
        """
        return bpy.context.preferences.system.ui_line_width

    def scaled_padding(self) -> int:
        return int(self.ui_scale(self.padding))

    def scaled_spacing(self) -> int:
        return int(self.ui_scale(self.spacing))

    def scaled_item_height(self) -> int:
        return int(self.ui_scale(self.item_height))

    def scaled_text_size(self) -> int:
        return int(self.ui_scale(self.text_size))


# ═══════════════════════════════════════════════════════════════════════════════
# Drawing Utilities - 描画ユーティリティ
# ═══════════════════════════════════════════════════════════════════════════════

class GPUDrawing:
    """GPU 描画ユーティリティ"""

    _shader: gpu.types.GPUShader = None

    @classmethod
    def get_shader(cls) -> gpu.types.GPUShader:
        """シェーダーを取得（キャッシュ）"""
        if cls._shader is None:
            cls._shader = gpu.shader.from_builtin(_SHADER_NAME)
        return cls._shader

    @classmethod
    def draw_rect(cls, x: float, y: float, width: float, height: float,
                  color: tuple[float, float, float, float]) -> None:
        """矩形を描画"""
        shader = cls.get_shader()
        vertices = (
            (x, y),
            (x + width, y),
            (x + width, y - height),
            (x, y - height),
        )
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_rounded_rect(cls, x: float, y: float, width: float, height: float,
                          radius: int, color: tuple[float, float, float, float],
                          corners: tuple[bool, bool, bool, bool] = (True, True, True, True)) -> None:
        """
        角丸矩形を描画

        Args:
            corners: (bottomLeft, topLeft, topRight, bottomRight)
        """
        shader = cls.get_shader()
        vertices = cls._calc_rounded_rect_vertices(x, y, width, height, radius, corners)
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_rounded_rect_outline(cls, x: float, y: float, width: float, height: float,
                                   radius: int, color: tuple[float, float, float, float],
                                   corners: tuple[bool, bool, bool, bool] = (True, True, True, True),
                                   line_width: float = 0.0) -> None:
        """
        角丸矩形のアウトラインを描画（ストローク方式）

        Args:
            line_width: ライン太さ（0.0 の場合は system.ui_line_width を使用）

        Note:
            GPU の LINE_LOOP は太い線で角が正しく接続されないため、
            内側と外側の 2 つのパスを TRIANGLE_STRIP で塗りつぶす方式を使用。
        """
        if line_width <= 0.0:
            line_width = bpy.context.preferences.system.ui_line_width

        # 細い線（1px 以下）の場合は従来の LINE_LOOP を使用
        if line_width <= 1.0:
            shader = cls.get_shader()
            vertices = cls._calc_rounded_rect_outline_vertices(x, y, width, height, radius, corners)
            batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": vertices})
            shader.bind()
            shader.uniform_float("color", color)
            gpu.state.blend_set('ALPHA')
            gpu.state.line_width_set(line_width)
            batch.draw(shader)
            gpu.state.blend_set('NONE')
            return

        # 太い線の場合はストローク描画（内外 2 パスの塗りつぶし）
        cls._draw_rounded_rect_stroke(x, y, width, height, radius, color, line_width, corners)

    @classmethod
    def _draw_rounded_rect_stroke(cls, x: float, y: float, width: float, height: float,
                                   radius: int, color: tuple[float, float, float, float],
                                   stroke_width: float,
                                   corners: tuple[bool, bool, bool, bool] = (True, True, True, True)) -> None:
        """
        ストローク方式で角丸矩形のアウトラインを描画

        内側と外側の頂点を交互に配置し、TRIANGLE_STRIP で描画することで
        均一な太さのストロークを実現。
        """
        shader = cls.get_shader()
        half = stroke_width / 2.0

        # 外側の頂点（元のサイズ + half）
        outer_verts = cls._calc_rounded_rect_outline_vertices(
            x - half, y + half,
            width + stroke_width, height + stroke_width,
            radius + int(half), corners
        )

        # 内側の頂点（元のサイズ - half）
        inner_radius = max(0, radius - int(half))
        inner_verts = cls._calc_rounded_rect_outline_vertices(
            x + half, y - half,
            width - stroke_width, height - stroke_width,
            inner_radius, corners
        )

        # 頂点数を揃える（少ない方に合わせる）
        min_len = min(len(outer_verts), len(inner_verts))
        outer_verts = outer_verts[:min_len]
        inner_verts = inner_verts[:min_len]

        # TRIANGLE_STRIP 用に交互に配置
        vertices = []
        for i in range(min_len):
            vertices.append(outer_verts[i])
            vertices.append(inner_verts[i])

        # 閉じる（最初の頂点ペアを追加）
        if min_len > 0:
            vertices.append(outer_verts[0])
            vertices.append(inner_verts[0])

        batch = batch_for_shader(shader, 'TRI_STRIP', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def _calc_rounded_rect_outline_vertices(cls, x: float, y: float, width: float, height: float,
                                             radius: int, corners: tuple[bool, bool, bool, bool]) -> list[tuple[float, float]]:
        """
        角丸矩形のアウトライン用頂点を計算（中心点なし、LINE_LOOP 用）
        """
        r = min(radius, int(height / 2), int(width / 2))

        # 角丸なしの場合
        if r <= 0:
            return [
                (x, y),                    # topLeft
                (x, y - height),           # bottomLeft
                (x + width, y - height),   # bottomRight
                (x + width, y),            # topRight
            ]

        vertices = []
        segments = max(4, r)

        # topLeft (corners[1]) - 角度 90° → 180°
        if corners[1]:
            cx, cy = x + r, y - r
            for j in range(segments + 1):
                angle = pi / 2 * (1 + j / segments)
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            vertices.append((x, y))

        # bottomLeft (corners[0]) - 角度 180° → 270°
        if corners[0]:
            cx, cy = x + r, y - height + r
            for j in range(segments + 1):
                angle = pi * (1 + 0.5 * j / segments)
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            vertices.append((x, y - height))

        # bottomRight (corners[3]) - 角度 270° → 360°
        if corners[3]:
            cx, cy = x + width - r, y - height + r
            for j in range(segments + 1):
                angle = pi * (1.5 + 0.5 * j / segments)
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            vertices.append((x + width, y - height))

        # topRight (corners[2]) - 角度 0° → 90°
        if corners[2]:
            cx, cy = x + width - r, y - r
            for j in range(segments + 1):
                angle = pi / 2 * j / segments
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            vertices.append((x + width, y))

        return vertices

    @classmethod
    def _calc_rounded_rect_vertices(cls, x: float, y: float, width: float, height: float,
                                     radius: int, corners: tuple[bool, bool, bool, bool]) -> list[tuple[float, float]]:
        """
        角丸矩形の頂点を計算

        座標系: 左下原点、Y は上が正
        corners: (bottomLeft, topLeft, topRight, bottomRight)

        頂点順序（TRI_FAN 用）:
        center → topLeft → topRight → bottomRight → bottomLeft → topLeft（閉じる）
        """
        r = min(radius, int(height / 2), int(width / 2))

        # 中心点（TRI_FAN の起点）
        center = (x + width / 2, y - height / 2)
        vertices = [center]

        # 角丸なしの場合
        if r <= 0:
            vertices.extend([
                (x, y),                    # topLeft
                (x + width, y),            # topRight
                (x + width, y - height),   # bottomRight
                (x, y - height),           # bottomLeft
                (x, y),                    # topLeft（閉じる）
            ])
            return vertices

        segments = max(4, r)  # 角の滑らかさ

        # topLeft (corners[1]) - 角度 90° → 180°
        if corners[1]:
            cx, cy = x + r, y - r
            for j in range(segments + 1):
                angle = pi / 2 * (1 + j / segments)  # 90° → 180°
                vx = cx + r * cos(angle)
                vy = cy + r * sin(angle)
                vertices.append((vx, vy))
        else:
            vertices.append((x, y))

        # bottomLeft (corners[0]) - 角度 180° → 270°
        if corners[0]:
            cx, cy = x + r, y - height + r
            for j in range(segments + 1):
                angle = pi * (1 + 0.5 * j / segments)  # 180° → 270°
                vx = cx + r * cos(angle)
                vy = cy + r * sin(angle)
                vertices.append((vx, vy))
        else:
            vertices.append((x, y - height))

        # bottomRight (corners[3]) - 角度 270° → 360°
        if corners[3]:
            cx, cy = x + width - r, y - height + r
            for j in range(segments + 1):
                angle = pi * (1.5 + 0.5 * j / segments)  # 270° → 360°
                vx = cx + r * cos(angle)
                vy = cy + r * sin(angle)
                vertices.append((vx, vy))
        else:
            vertices.append((x + width, y - height))

        # topRight (corners[2]) - 角度 0° → 90°
        if corners[2]:
            cx, cy = x + width - r, y - r
            for j in range(segments + 1):
                angle = pi / 2 * j / segments  # 0° → 90°
                vx = cx + r * cos(angle)
                vy = cy + r * sin(angle)
                vertices.append((vx, vy))
        else:
            vertices.append((x + width, y))

        # 閉じる（最初の外周頂点に戻る）
        if corners[1]:
            cx, cy = x + r, y - r
            vx = cx + r * cos(pi / 2)
            vy = cy + r * sin(pi / 2)
            vertices.append((vx, vy))
        else:
            vertices.append((x, y))

        return vertices

    @classmethod
    def draw_line(cls, x1: float, y1: float, x2: float, y2: float,
                  color: tuple[float, float, float, float], width: float = 0.0) -> None:
        """
        線を描画

        Args:
            width: ライン太さ（0.0 の場合は system.ui_line_width を使用）
        """
        shader = cls.get_shader()
        vertices = ((x1, y1), (x2, y2))
        batch = batch_for_shader(shader, 'LINES', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)

        # ライン太さを設定（0.0 の場合はシステム推奨値を使用）
        if width <= 0.0:
            width = bpy.context.preferences.system.ui_line_width
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(width)
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_circle(cls, cx: float, cy: float, radius: float,
                    color: tuple[float, float, float, float],
                    segments: int = 16) -> None:
        """
        塗りつぶし円を描画

        Args:
            cx, cy: 中心座標
            radius: 半径
            color: 色 (RGBA)
            segments: 分割数（滑らかさ）
        """
        shader = cls.get_shader()

        # 中心点 + 円周上の頂点
        vertices = [(cx, cy)]
        for i in range(segments + 1):
            angle = 2 * pi * i / segments
            vertices.append((cx + radius * cos(angle), cy + radius * sin(angle)))

        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_rounded_line(cls, x1: float, y1: float, x2: float, y2: float,
                          color: tuple[float, float, float, float],
                          width: float = 0.0, segments: int = 8) -> None:
        """
        先端が丸い線を描画

        GPU の線描画は先端が平らなので、両端に円を追加して丸みを表現。

        Args:
            x1, y1: 始点
            x2, y2: 終点
            color: 色 (RGBA)
            width: ライン太さ（0.0 の場合は system.ui_line_width を使用）
            segments: 円の分割数
        """
        if width <= 0.0:
            width = bpy.context.preferences.system.ui_line_width

        # 線を描画
        cls.draw_line(x1, y1, x2, y2, color, width)

        # 先端の円を描画（半径は線の太さの半分）
        radius = width / 2.0
        if radius >= 1.0:
            cls.draw_circle(x1, y1, radius, color, segments)
            cls.draw_circle(x2, y2, radius, color, segments)

    @classmethod
    def draw_drop_shadow(cls, x: float, y: float, width: float, height: float,
                         radius: int, color: tuple[float, float, float, float],
                         offset: tuple[int, int] = (4, -4),
                         blur: int = 8) -> None:
        """
        ドロップシャドウを描画

        複数の半透明レイヤーを重ねてぼかし効果を近似。

        Args:
            x, y: 左上座標
            width, height: サイズ
            radius: 角丸半径
            color: シャドウ色 (RGBA)
            offset: オフセット (x, y)
            blur: ぼかし半径
        """
        if blur <= 0:
            # ぼかしなし - 単純なシャドウ
            cls.draw_rounded_rect(
                x + offset[0], y + offset[1],
                width, height, radius, color
            )
            return

        # ぼかし効果を近似（複数レイヤー）
        layers = min(blur, 6)  # 最大6レイヤー
        base_alpha = color[3]

        for i in range(layers, 0, -1):
            # 外側のレイヤーほど大きく、透明に
            expand = i * (blur / layers)
            layer_alpha = base_alpha * (1.0 - i / (layers + 1)) * 0.5

            layer_color = (color[0], color[1], color[2], layer_alpha)
            cls.draw_rounded_rect(
                x + offset[0] - expand / 2,
                y + offset[1] + expand / 2,
                width + expand,
                height + expand,
                radius + int(expand / 2),
                layer_color
            )


class BLFDrawing:
    """BLF テキスト描画ユーティリティ"""

    @classmethod
    def draw_text(cls, x: float, y: float, text: str,
                  color: tuple[float, float, float, float],
                  size: int = 13, font_id: int = _FONT_ID) -> None:
        """テキストを描画"""
        blf.size(font_id, size)

        blf.color(font_id, *color)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, text)

    @classmethod
    def draw_text_with_shadow(cls, x: float, y: float, text: str,
                               color: tuple[float, float, float, float],
                               size: int = 13,
                               shadow_color: float = 0.0,
                               shadow_alpha: float = 0.5,
                               shadow_offset: tuple[int, int] = (1, -1),
                               font_id: int = _FONT_ID) -> None:
        """シャドウ付きテキストを描画"""
        blf.size(font_id, size)

        # シャドウ
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, shadow_color, shadow_color, shadow_color, shadow_alpha)
        blf.shadow_offset(font_id, shadow_offset[0], shadow_offset[1])

        blf.color(font_id, *color)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, text)

        blf.disable(font_id, blf.SHADOW)

    @classmethod
    def get_text_dimensions(cls, text: str, size: int = 13, font_id: int = _FONT_ID) -> tuple[float, float]:
        """テキストの幅と高さを取得"""
        blf.size(font_id, size)
        return blf.dimensions(font_id, text)

    @classmethod
    def wrap_text(cls, text: str, max_width: float, size: int = 13,
                  font_id: int = _FONT_ID) -> list[str]:
        """テキストを指定幅で折り返し"""
        blf.size(font_id, size)

        lines = []
        for paragraph in text.split('\n'):
            if not paragraph:
                lines.append('')
                continue

            words = paragraph.split(' ')
            current_line = ''

            for word in words:
                test_line = f"{current_line} {word}".strip()
                width, _ = blf.dimensions(font_id, test_line)

                if width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

        return lines


# ═══════════════════════════════════════════════════════════════════════════════
# Icon Drawing - アイコン描画
# ═══════════════════════════════════════════════════════════════════════════════

class IconDrawing:
    """
    Blender アイコン描画ユーティリティ

    機能:
    - PNG ファイルからテクスチャをロードして GPU 描画
    - PME カスタムアイコン（ユーザー PNG）のサポート
    - Blender 内蔵アイコンは UILayout 経由でのみ使用可能

    使用例:
        # PNG ファイルから直接描画
        IconDrawing.draw_texture_file("/path/to/icon.png", x, y, 20, 20)

        # PME カスタムアイコン名で描画（PreviewsHelper 経由）
        IconDrawing.draw_custom_icon("my_icon", x, y)
    """

    # アイコンサイズ（Blender 標準）
    ICON_SIZE = 20

    # シェーダーキャッシュ
    _image_shader: gpu.types.GPUShader = None

    # テクスチャキャッシュ: filepath -> (GPUTexture, width, height)
    _texture_cache: dict[str, tuple[gpu.types.GPUTexture, int, int]] = {}

    # PME カスタムアイコンのパスキャッシュ: icon_name -> filepath
    _icon_path_cache: dict[str, str] = {}

    @classmethod
    def get_image_shader(cls) -> gpu.types.GPUShader:
        """IMAGE_COLOR シェーダーを取得（キャッシュ）"""
        if cls._image_shader is None:
            cls._image_shader = gpu.shader.from_builtin('IMAGE_COLOR')
        return cls._image_shader

    @classmethod
    def get_icon_id(cls, icon_name: str) -> int:
        """Blender 内蔵アイコン名から ID を取得"""
        # TODO: Reserved for Blender built-in icons; currently unused.
        try:
            return bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items[icon_name].value
        except (KeyError, AttributeError):
            return 0

    @classmethod
    def load_texture(cls, filepath: str) -> Optional[tuple[gpu.types.GPUTexture, int, int]]:
        """
        PNG ファイルからテクスチャをロード

        Args:
            filepath: PNG ファイルのパス

        Returns:
            (GPUTexture, width, height) または None（失敗時）
        """
        # キャッシュをチェック
        if filepath in cls._texture_cache:
            return cls._texture_cache[filepath]

        try:
            import os
            if not os.path.exists(filepath):
                return None

            # Blender Image としてロード
            # 既存の同名イメージがあれば再利用
            img_name = f"_gpu_icon_{os.path.basename(filepath)}"
            if img_name in bpy.data.images:
                img = bpy.data.images[img_name]
                # ファイルパスが異なる場合は再読み込み
                if img.filepath != filepath:
                    img.filepath = filepath
                    img.reload()
            else:
                img = bpy.data.images.load(filepath)
                img.name = img_name

            # GPU テクスチャを作成
            texture = gpu.texture.from_image(img)
            result = (texture, img.size[0], img.size[1])

            # キャッシュに保存
            cls._texture_cache[filepath] = result
            return result

        except Exception as e:
            print(f"IconDrawing: Failed to load texture {filepath}: {e}")
            return None

    @classmethod
    def draw_texture(cls, texture: gpu.types.GPUTexture,
                     x: float, y: float, width: float, height: float,
                     alpha: float = 1.0) -> None:
        """
        テクスチャを描画

        Args:
            texture: GPUTexture オブジェクト
            x, y: 左上座標（Y は上から下へ減少）
            width, height: 描画サイズ
            alpha: 透明度 (0.0-1.0)
        """
        shader = cls.get_image_shader()

        # 頂点座標（左上から時計回り）
        # Blender の座標系: 左下原点、Y は上が正
        vertices = (
            (x, y),                    # 左上
            (x + width, y),            # 右上
            (x + width, y - height),   # 右下
            (x, y - height),           # 左下
        )

        # テクスチャ座標（左下原点）
        # 画像は左上原点なので Y を反転
        tex_coords = (
            (0.0, 1.0),  # 左上
            (1.0, 1.0),  # 右上
            (1.0, 0.0),  # 右下
            (0.0, 0.0),  # 左下
        )

        # インデックス（2つの三角形で矩形を構成）
        indices = ((0, 1, 2), (0, 2, 3))

        batch = batch_for_shader(
            shader, 'TRIS',
            {"pos": vertices, "texCoord": tex_coords},
            indices=indices
        )

        shader.bind()
        shader.uniform_float("color", (1.0, 1.0, 1.0, alpha))
        shader.uniform_sampler("image", texture)

        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_texture_file(cls, filepath: str,
                          x: float, y: float,
                          width: Optional[float] = None,
                          height: Optional[float] = None,
                          alpha: float = 1.0) -> bool:
        """
        PNG ファイルからテクスチャを描画

        Args:
            filepath: PNG ファイルのパス
            x, y: 左上座標
            width, height: 描画サイズ（None の場合は元画像サイズ）
            alpha: 透明度

        Returns:
            描画成功したかどうか
        """
        result = cls.load_texture(filepath)
        if result is None:
            return False

        texture, img_w, img_h = result
        draw_w = width if width is not None else img_w
        draw_h = height if height is not None else img_h

        cls.draw_texture(texture, x, y, draw_w, draw_h, alpha)
        return True

    @classmethod
    def draw_custom_icon(cls, icon_name: str,
                         x: float, y: float,
                         size: float = ICON_SIZE,
                         alpha: float = 1.0) -> bool:
        """
        PME カスタムアイコンを描画

        Args:
            icon_name: PME アイコン名（拡張子なし）
            x, y: 左上座標
            size: 描画サイズ（正方形）
            alpha: 透明度

        Returns:
            描画成功したかどうか
        """
        filepath = cls.find_custom_icon_path(icon_name)
        if not filepath:
            return False
        return cls.draw_texture_file(filepath, x, y, size, size, alpha)

    @classmethod
    def find_custom_icon_path(cls, icon_name: str) -> Optional[str]:
        """PME カスタムアイコンのパスを探す"""
        # パスキャッシュをチェック
        if icon_name in cls._icon_path_cache:
            return cls._icon_path_cache[icon_name]

        # PME の PreviewsHelper からパスを探す
        try:
            from ..infra.io import get_user_icons_dir, get_system_icons_dir
            import os

            # ユーザーアイコンを優先
            user_dir = get_user_icons_dir()
            user_path = os.path.join(user_dir, f"{icon_name}.png")
            if os.path.exists(user_path):
                cls._icon_path_cache[icon_name] = user_path
                return user_path

            # システムアイコンをチェック
            addon_root = os.path.dirname(os.path.dirname(__file__))
            system_dir = get_system_icons_dir(addon_root)
            system_path = os.path.join(system_dir, f"{icon_name}.png")
            if os.path.exists(system_path):
                cls._icon_path_cache[icon_name] = system_path
                return system_path

        except Exception as e:
            print(f"IconDrawing: Failed to find custom icon '{icon_name}': {e}")

        return None

    @classmethod
    def clear_cache(cls) -> None:
        """テクスチャキャッシュをクリア"""
        cls._texture_cache.clear()
        cls._icon_path_cache.clear()

    @classmethod
    def draw_icon(cls, x: float, y: float, icon: str,
                  alpha: float = 1.0, scale: float = 1.0) -> bool:
        """
        アイコンを描画

        まず PME カスタムアイコンを試み、なければ何もしない。
        Blender 内蔵アイコンは GPU では描画できないため、
        UILayout を使用するか、カスタムアイコンで代替する必要がある。

        Args:
            icon: アイコン名（PME カスタムアイコン名 or Blender アイコン名）
            x, y: 左上座標
            alpha: 透明度
            scale: サイズスケール

        Returns:
            描画成功したかどうか
        """
        size = cls.ICON_SIZE * scale

        # PME カスタムアイコンを試す
        if cls.draw_custom_icon(icon, x, y, size, alpha):
            return True

        # Blender 内蔵アイコンは GPU で描画できない
        # フォールバック: 何もしない（呼び出し側でテキストを表示するなど）
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Layout Items - レイアウトアイテム
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LayoutItem:
    """レイアウトアイテムの基底クラス"""
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    visible: bool = True
    enabled: bool = True

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """サイズを計算して返す (width, height)"""
        return (self.width, self.height)

    def draw(self, style: GPULayoutStyle) -> None:
        """描画"""
        pass

    def is_inside(self, x: float, y: float) -> bool:
        """座標がアイテム内かどうか"""
        return (self.x <= x <= self.x + self.width and
                self.y - self.height <= y <= self.y)

    def handle_event(self, event: Event, mouse_x: float, mouse_y: float) -> bool:
        """イベント処理"""
        return False


@dataclass
class LabelItem(LayoutItem):
    """ラベル（テキスト表示）"""
    text: str = ""
    icon: str = "NONE"
    alignment: Alignment = Alignment.LEFT
    text_color: Optional[tuple[float, float, float, float]] = None
    alert: bool = False

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, style.scaled_text_size())
        icon_w = IconDrawing.ICON_SIZE + style.scaled_spacing() if self.icon != "NONE" else 0
        return (text_w + icon_w, max(text_h, style.scaled_item_height()))

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        # 色の決定: alert > text_color > enabled/disabled
        if self.alert:
            color = style.alert_color
        elif self.text_color:
            color = self.text_color
        elif self.enabled:
            color = style.text_color
        else:
            color = style.text_color_disabled
        text_size = style.scaled_text_size()

        # コンテンツサイズを計算
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, text_size)
        icon_size = IconDrawing.ICON_SIZE if self.icon != "NONE" else 0
        icon_spacing = style.scaled_spacing() if self.icon != "NONE" else 0
        content_w = icon_size + icon_spacing + text_w

        # alignment に応じた X 位置を計算
        if self.alignment == Alignment.CENTER:
            content_x = self.x + (self.width - content_w) / 2
        elif self.alignment == Alignment.RIGHT:
            content_x = self.x + self.width - content_w
        else:  # LEFT or EXPAND
            content_x = self.x

        # テキスト位置（Y は baseline）
        text_y = self.y - (self.height + text_h) / 2

        # アイコン描画
        text_x = content_x
        if self.icon != "NONE":
            # アイコンを垂直方向に中央揃え
            icon_y = self.y - (self.height - icon_size) / 2
            alpha = 1.0 if self.enabled else 0.5
            IconDrawing.draw_icon(content_x, icon_y, self.icon, alpha=alpha)
            text_x += icon_size + icon_spacing

        # テキスト
        if style.text_shadow_enabled:
            BLFDrawing.draw_text_with_shadow(
                text_x, text_y, self.text, color, text_size,
                style.text_shadow_color, style.text_shadow_alpha,
                style.text_shadow_offset
            )
        else:
            BLFDrawing.draw_text(text_x, text_y, self.text, color, text_size)


@dataclass
class SeparatorItem(LayoutItem):
    """区切り線"""
    factor: float = 1.0

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        return (self.width, int(style.scaled_spacing() * self.factor * 2))

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        y = self.y - self.height / 2
        GPUDrawing.draw_line(
            self.x, y,
            self.x + self.width, y,
            style.separator_color, 1.0
        )


@dataclass
class ButtonItem(LayoutItem):
    """クリック可能なボタン"""
    text: str = ""
    icon: str = "NONE"
    on_click: Optional[Callable[[], None]] = None

    # 状態
    _hovered: bool = field(default=False, repr=False)
    _pressed: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, style.scaled_text_size())
        icon_w = IconDrawing.ICON_SIZE + style.scaled_spacing() if self.icon != "NONE" else 0
        padding = style.scaled_padding()
        return (text_w + icon_w + padding * 2, style.scaled_item_height())

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        # 背景色
        if self._pressed:
            bg_color = style.button_press_color
        elif self._hovered:
            bg_color = style.button_hover_color
        else:
            bg_color = style.button_color

        if not self.enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        # 背景
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            style.border_radius, bg_color
        )

        # テキスト
        text_color = style.button_text_color if self.enabled else style.text_color_disabled
        text_size = style.scaled_text_size()
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, text_size)

        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        BLFDrawing.draw_text(text_x, text_y, self.text, text_color, text_size)

    def handle_event(self, event: Event, mouse_x: float, mouse_y: float) -> bool:
        if not self.enabled:
            return False

        inside = self.is_inside(mouse_x, mouse_y)

        if event.type == 'MOUSEMOVE':
            self._hovered = inside
            return inside

        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and inside:
                self._pressed = True
                return True
            elif event.value == 'RELEASE':
                if self._pressed and inside and self.on_click:
                    self.on_click()
                self._pressed = False
                return inside

        return False


@dataclass
class ToggleItem(LayoutItem):
    """トグルボタン（ON/OFF）"""
    text: str = ""
    icon: str = "NONE"
    icon_on: str = "NONE"
    icon_off: str = "NONE"
    value: bool = False
    on_toggle: Optional[Callable[[bool], None]] = None

    _hovered: bool = field(default=False, repr=False)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, style.scaled_text_size())
        icon_w = IconDrawing.ICON_SIZE + style.scaled_spacing() if self.icon != "NONE" else 0
        padding = style.scaled_padding()
        return (text_w + icon_w + padding * 2, style.scaled_item_height())

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        # 背景色（ON 状態で強調）
        if self.value:
            bg_color = style.highlight_color if not self._hovered else tuple(
                min(1.0, c * 1.2) for c in style.highlight_color[:3]
            ) + (style.highlight_color[3],)
        else:
            bg_color = style.button_hover_color if self._hovered else style.button_color

        if not self.enabled:
            bg_color = tuple(c * 0.5 for c in bg_color[:3]) + (bg_color[3],)

        # 背景
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            style.border_radius, bg_color
        )

        # テキスト
        text_color = style.button_text_color if self.enabled else style.text_color_disabled
        text_size = style.scaled_text_size()
        text_w, text_h = BLFDrawing.get_text_dimensions(self.text, text_size)

        text_x = self.x + (self.width - text_w) / 2
        text_y = self.y - (self.height + text_h) / 2

        BLFDrawing.draw_text(text_x, text_y, self.text, text_color, text_size)

    def handle_event(self, event: Event, mouse_x: float, mouse_y: float) -> bool:
        if not self.enabled:
            return False

        inside = self.is_inside(mouse_x, mouse_y)

        if event.type == 'MOUSEMOVE':
            self._hovered = inside
            return inside

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and inside:
            self.value = not self.value
            if self.on_toggle:
                self.on_toggle(self.value)
            return True

        return False


@dataclass
class PropDisplayItem(LayoutItem):
    """プロパティ値の表示（読み取り専用）"""
    data: Any = None
    property: str = ""
    text: str = ""
    icon: str = "NONE"

    def _get_value(self) -> str:
        """プロパティ値を文字列で取得"""
        if self.data is None:
            return "N/A"
        try:
            value = getattr(self.data, self.property)
            if isinstance(value, float):
                return f"{value:.3f}"
            elif isinstance(value, (list, tuple)):
                return ", ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in value)
            return str(value)
        except AttributeError:
            return "N/A"

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        label = self.text or self.property
        value = self._get_value()
        display_text = f"{label}: {value}"
        text_w, text_h = BLFDrawing.get_text_dimensions(display_text, style.scaled_text_size())
        return (text_w, style.scaled_item_height())

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        label = self.text or self.property
        value = self._get_value()

        text_size = style.scaled_text_size()
        _, text_h = BLFDrawing.get_text_dimensions("Wg", text_size)
        text_y = self.y - (self.height + text_h) / 2

        # enabled 状態に応じた色
        label_color = style.text_color_secondary if self.enabled else style.text_color_disabled
        value_color = style.text_color if self.enabled else style.text_color_disabled

        # ラベル
        BLFDrawing.draw_text(self.x, text_y, f"{label}: ", label_color, text_size)

        # 値
        label_w, _ = BLFDrawing.get_text_dimensions(f"{label}: ", text_size)
        BLFDrawing.draw_text(self.x + label_w, text_y, value, value_color, text_size)


@dataclass
class BoxItem(LayoutItem):
    """ボックス（枠線付きコンテナ）"""
    items: list[LayoutItem] = field(default_factory=list)

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        if not self.items:
            return (self.width, style.scaled_padding() * 2)

        total_height = style.scaled_padding() * 2
        for item in self.items:
            _, h = item.calc_size(style)
            total_height += h + style.scaled_spacing()

        return (self.width, total_height)

    def draw(self, style: GPULayoutStyle) -> None:
        if not self.visible:
            return

        # 背景
        GPUDrawing.draw_rounded_rect(
            self.x, self.y, self.width, self.height,
            style.border_radius, style.bg_color
        )

        # アウトライン
        GPUDrawing.draw_rounded_rect_outline(
            self.x, self.y, self.width, self.height,
            style.border_radius, style.outline_color
        )

        # 子アイテム
        for item in self.items:
            item.draw(style)

    def handle_event(self, event: Event, mouse_x: float, mouse_y: float) -> bool:
        for item in self.items:
            if item.handle_event(event, mouse_x, mouse_y):
                return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# GPULayout - メインクラス
# ═══════════════════════════════════════════════════════════════════════════════

class GPULayout:
    """
    Blender UILayout を模した GPU 描画レイアウトシステム

    使用例:
        layout = GPULayout(x=100, y=500, width=300)
        layout.label(text="Title", icon='INFO')

        row = layout.row()
        row.label(text="Left")
        row.label(text="Right")

        layout.separator()
        layout.prop_display(context.object, "name", text="Object")

        layout.operator(text="Click Me", on_click=lambda: print("Clicked!"))

        # 描画
        layout.draw()

        # イベント処理（modal オペレーター内で）
        layout.handle_event(event)
    """

    def __init__(self, x: float, y: float, width: float,
                 style: Optional[GPULayoutStyle] = None,
                 direction: Direction = Direction.VERTICAL,
                 parent: Optional[GPULayout] = None):
        """
        Args:
            x: 左上 X 座標
            y: 左上 Y 座標（Blender は左下原点なので注意）
            width: 幅
            style: スタイル（None の場合は Blender テーマから自動取得）
            direction: レイアウト方向
            parent: 親レイアウト
        """
        self.x = x
        self.y = y
        self.width = width
        self.style = style or GPULayoutStyle.from_blender_theme()
        self.direction = direction
        self.parent = parent

        # アイテムと子レイアウト
        self._items: list[LayoutItem] = []
        self._children: list[GPULayout] = []

        # カーソル位置
        self._cursor_x = x + self.style.scaled_padding()
        self._cursor_y = y - self.style.scaled_padding()

        # 状態プロパティ（UILayout 互換）
        self.active: bool = True
        self.enabled: bool = True
        self.alert: bool = False
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.alignment: Alignment = Alignment.EXPAND

        # アイテム間スペースを制御（align=True で 0）
        self._align: bool = False

        # split 用（0.0 = 自動計算、0.0-1.0 = 最初の column の割合）
        self._split_factor: float = 0.0
        self._split_column_index: int = 0  # column() が呼ばれるたびにインクリメント

        # ボックス描画フラグ
        self._draw_background: bool = False
        self._draw_outline: bool = False

    # ─────────────────────────────────────────────────────────────────────────
    # コンテナメソッド（UILayout 互換）
    # ─────────────────────────────────────────────────────────────────────────

    def row(self, align: bool = False) -> GPULayout:
        """
        水平レイアウトを作成

        Args:
            align: True の場合、アイテム間のスペースをなくす
        """
        child = GPULayout(
            x=self._cursor_x,
            y=self._cursor_y,
            width=self._get_available_width(),
            style=self.style,
            direction=Direction.HORIZONTAL,
            parent=self
        )
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        child._align = align  # アイテム間スペースを制御
        self._children.append(child)
        return child

    def column(self, align: bool = False) -> GPULayout:
        """
        垂直レイアウトを作成

        Args:
            align: True の場合、アイテム間のスペースをなくす

        Note:
            split() 内で呼ばれた場合、factor に基づいて幅が計算される。
            - factor > 0: 最初の column が factor 割合、残りは均等分割
            - factor == 0: 全ての column を均等分割
        """
        available_width = self._get_available_width()

        # split の中で呼ばれた場合、factor に基づいて幅を計算
        if self._split_factor > 0.0 and self._split_column_index == 0:
            # 最初の column: factor 割合
            col_width = available_width * self._split_factor
        elif self._split_factor > 0.0 and self._split_column_index == 1:
            # 2番目の column: 残り全部（単純化のため 2 列のみサポート）
            col_width = available_width * (1.0 - self._split_factor)
        else:
            # 自動計算または 3 列目以降: 利用可能幅をそのまま使用
            col_width = available_width

        child = GPULayout(
            x=self._cursor_x,
            y=self._cursor_y,
            width=col_width,
            style=self.style,
            direction=Direction.VERTICAL,
            parent=self
        )
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        child._align = align
        self._children.append(child)

        # split 用インデックスをインクリメント
        self._split_column_index += 1

        return child

    def box(self) -> GPULayout:
        """ボックス付きレイアウトを作成"""
        child = self.column()
        child._draw_background = True
        child._draw_outline = True
        return child

    def split(self, *, factor: float = 0.0, align: bool = False) -> GPULayout:
        """
        分割レイアウトを作成

        Args:
            factor: 最初の column の幅の割合 (0.0-1.0)
                    0.0 の場合は自動計算（均等分割）
            align: True の場合、column 間のスペースをなくす

        使用例:
            split = layout.split(factor=0.3)
            col1 = split.column()
            col1.label(text="Left (30%)")
            col2 = split.column()
            col2.label(text="Right (70%)")
        """
        child = GPULayout(
            x=self._cursor_x,
            y=self._cursor_y,
            width=self._get_available_width(),
            style=self.style,
            direction=Direction.HORIZONTAL,
            parent=self
        )
        child._split_factor = factor
        child._align = align
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        self._children.append(child)
        return child

    # ─────────────────────────────────────────────────────────────────────────
    # 表示メソッド（UILayout 互換）
    # ─────────────────────────────────────────────────────────────────────────

    def label(self, *, text: str = "", icon: str = "NONE") -> None:
        """ラベルを追加"""
        item = LabelItem(
            text=text,
            icon=icon,
            enabled=self.enabled and self.active,
            alert=self.alert
        )
        self._add_item(item)

    def separator(self, factor: float = 1.0) -> None:
        """区切り線を追加"""
        item = SeparatorItem(factor=factor)
        self._add_item(item)

    def separator_spacer(self) -> None:
        """スペーサーを追加（separator のエイリアス）"""
        self.separator(factor=0.5)

    def operator(self, operator: str = "", *, text: str = "", icon: str = "NONE",
                 on_click: Optional[Callable[[], None]] = None) -> ButtonItem:
        """
        オペレーターボタンを追加

        Note: 実際の Blender オペレーターは呼び出せないため、
              on_click コールバックで代替する
        """
        item = ButtonItem(
            text=text or operator,
            icon=icon,
            on_click=on_click,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item

    # ─────────────────────────────────────────────────────────────────────────
    # プロパティメソッド
    # ─────────────────────────────────────────────────────────────────────────

    def prop(self, data: Any, property: str, *, text: str = "",
             icon: str = "NONE", expand: bool = False, slider: bool = False,
             toggle: int = -1, icon_only: bool = False) -> None:
        """
        プロパティを表示（読み取り専用）

        Note: GPU 版では編集不可。表示のみ。
              toggle=1 の場合は ToggleItem を使用。
        """
        if toggle == 1:
            # トグルボタン
            try:
                value = getattr(data, property)
            except AttributeError:
                value = False

            def on_toggle(new_value: bool):
                try:
                    setattr(data, property, new_value)
                except AttributeError:
                    pass

            item = ToggleItem(
                text=text or property,
                icon=icon,
                value=bool(value),
                on_toggle=on_toggle,
                enabled=self.enabled and self.active
            )
            self._add_item(item)
        else:
            # 読み取り専用表示
            self.prop_display(data, property, text=text, icon=icon)

    def prop_display(self, data: Any, property: str, *,
                     text: str = "", icon: str = "NONE") -> None:
        """プロパティ値を表示（明示的に読み取り専用）"""
        item = PropDisplayItem(
            data=data,
            property=property,
            text=text,
            icon=icon,
            enabled=self.enabled and self.active
        )
        self._add_item(item)

    def prop_enum(self, data: Any, property: str, value: str, *,
                  text: str = "", icon: str = "NONE") -> None:
        """Enum プロパティの特定値を表示"""
        try:
            current = getattr(data, property)
            is_active = current == value
        except AttributeError:
            is_active = False

        display_text = text or value
        if is_active:
            display_text = f"● {display_text}"
        else:
            display_text = f"○ {display_text}"

        self.label(text=display_text, icon=icon)

    # ─────────────────────────────────────────────────────────────────────────
    # ユーティリティメソッド
    # ─────────────────────────────────────────────────────────────────────────

    def _get_available_width(self) -> float:
        """利用可能な幅を取得"""
        return self.width - self.style.scaled_padding() * 2

    def _get_spacing(self) -> int:
        """アイテム間のスペースを取得（align=True で 0）"""
        return 0 if self._align else self.style.scaled_spacing()

    def _add_item(self, item: LayoutItem) -> None:
        """アイテムを追加"""
        item_width, item_height = item.calc_size(self.style)
        available_width = self._get_available_width()

        if self.direction == Direction.VERTICAL:
            # alignment に応じて幅と位置を計算
            if self.alignment == Alignment.EXPAND:
                # EXPAND: 利用可能幅いっぱいに拡張
                item.width = available_width * self.scale_x
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

        self._items.append(item)

    def calc_height(self) -> float:
        """合計高さを計算"""
        if not self._items and not self._children:
            return self.style.scaled_padding() * 2

        spacing = self._get_spacing()
        if self.direction == Direction.VERTICAL:
            height = self.style.scaled_padding() * 2
            for item in self._items:
                _, h = item.calc_size(self.style)
                height += h * self.scale_y + spacing
            for child in self._children:
                height += child.calc_height() + spacing
            return height
        else:
            # 水平レイアウト - 最大の高さ
            max_height = 0
            for item in self._items:
                _, h = item.calc_size(self.style)
                max_height = max(max_height, h * self.scale_y)
            for child in self._children:
                max_height = max(max_height, child.calc_height())
            return max_height + spacing

    def calc_width(self) -> float:
        """合計幅を計算"""
        if not self._items and not self._children:
            return self.width

        spacing = self._get_spacing()
        if self.direction == Direction.HORIZONTAL:
            width = self.style.scaled_padding() * 2
            for item in self._items:
                w, _ = item.calc_size(self.style)
                width += w * self.scale_x + spacing
            for child in self._children:
                width += child.calc_width() + spacing
            return width
        else:
            return self.width

    # ─────────────────────────────────────────────────────────────────────────
    # レイアウト計算
    # ─────────────────────────────────────────────────────────────────────────

    def layout(self) -> None:
        """レイアウトを計算（子レイアウトの位置を確定）"""
        # 自身のアイテムを再配置
        self._relayout_items()

        spacing = self._get_spacing()

        # 子レイアウトを配置
        cursor_y = self.y - self.style.scaled_padding()
        cursor_x = self.x + self.style.scaled_padding()

        # 既存アイテムの後からカーソル位置を取得
        if self._items:
            if self.direction == Direction.VERTICAL:
                last_item = self._items[-1]
                cursor_y = last_item.y - last_item.height - spacing
            else:
                last_item = self._items[-1]
                cursor_x = last_item.x + last_item.width + spacing

        for child in self._children:
            child.x = cursor_x
            child.y = cursor_y
            child.layout()

            if self.direction == Direction.VERTICAL:
                cursor_y -= child.calc_height() + spacing
            else:
                cursor_x += child.calc_width() + spacing

    def _relayout_items(self) -> None:
        """アイテムの位置を再計算"""
        cursor_x = self.x + self.style.scaled_padding()
        cursor_y = self.y - self.style.scaled_padding()
        available_width = self._get_available_width()
        spacing = self._get_spacing()

        for item in self._items:
            item_width, item_height = item.calc_size(self.style)

            if self.direction == Direction.VERTICAL:
                # alignment に応じて幅と位置を計算
                if self.alignment == Alignment.EXPAND:
                    item.width = available_width * self.scale_x
                    item.x = cursor_x
                else:
                    item.width = item_width * self.scale_x
                    if self.alignment == Alignment.CENTER:
                        item.x = cursor_x + (available_width - item.width) / 2
                    elif self.alignment == Alignment.RIGHT:
                        item.x = cursor_x + available_width - item.width
                    else:  # LEFT
                        item.x = cursor_x

                item.y = cursor_y
                item.height = item_height * self.scale_y
                cursor_y -= item.height + spacing
            else:
                # 水平レイアウト
                item.x = cursor_x
                item.y = cursor_y
                item.width = item_width * self.scale_x
                item.height = item_height * self.scale_y
                cursor_x += item.width + spacing

    # ─────────────────────────────────────────────────────────────────────────
    # 描画
    # ─────────────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        """GPU 描画を実行"""
        # レイアウト計算
        self.layout()
        height = self.calc_height()

        # 背景描画
        if self._draw_background:
            GPUDrawing.draw_rounded_rect(
                self.x, self.y, self.width, height,
                self.style.border_radius, self.style.bg_color
            )

        # アウトライン描画
        if self._draw_outline:
            GPUDrawing.draw_rounded_rect_outline(
                self.x, self.y, self.width, height,
                self.style.border_radius, self.style.outline_color
            )

        # アイテム描画
        for item in self._items:
            item.draw(self.style)

        # 子レイアウト描画
        for child in self._children:
            child.draw()

    # ─────────────────────────────────────────────────────────────────────────
    # イベント処理
    # ─────────────────────────────────────────────────────────────────────────

    def handle_event(self, event: Event) -> bool:
        """
        イベントを処理

        Args:
            event: Blender イベント

        Returns:
            イベントを消費したかどうか
        """
        # region 座標からマウス位置を取得
        # Note: 呼び出し側で region.x, region.y を引く必要がある場合あり
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        # 子レイアウトを先に処理
        for child in self._children:
            if child.handle_event(event):
                return True

        # アイテムを処理
        for item in self._items:
            if item.handle_event(event, mouse_x, mouse_y):
                return True

        return False

    def is_inside(self, x: float, y: float) -> bool:
        """座標がレイアウト内かどうか"""
        height = self.calc_height()
        return (self.x <= x <= self.x + self.width and
                self.y - height <= y <= self.y)


# ═══════════════════════════════════════════════════════════════════════════════
# Tooltip Builder - ツールチップ専用ビルダー
# ═══════════════════════════════════════════════════════════════════════════════

class GPUTooltip:
    """
    ツールチップ専用の簡易ビルダー

    使用例:
        tooltip = GPUTooltip()
        tooltip.title("Add Cube")
        tooltip.description("シーンに立方体プリミティブを追加します")
        tooltip.shortcut("Shift + A > M > C")
        tooltip.python("bpy.ops.mesh.primitive_cube_add()")

        # マウス位置の近くに描画
        tooltip.draw(mouse_x + 20, mouse_y - 10)
    """

    def __init__(self, max_width: float = 400):
        self.max_width = max_width
        self._title_text: str = ""
        self._description_text: str = ""
        self._shortcut_text: str = ""
        self._python_text: str = ""
        self._style = GPULayoutStyle.from_blender_theme('TOOLTIP')

    def title(self, text: str) -> GPUTooltip:
        """タイトルを設定"""
        self._title_text = text
        return self

    def description(self, text: str) -> GPUTooltip:
        """説明文を設定"""
        self._description_text = text
        return self

    def shortcut(self, text: str) -> GPUTooltip:
        """ショートカットを設定"""
        self._shortcut_text = text
        return self

    def python(self, text: str) -> GPUTooltip:
        """Python コマンドを設定"""
        self._python_text = text
        return self

    def _build_layout(self, x: float, y: float) -> Optional[GPULayout]:
        """内部でレイアウトを構築"""
        # Blender の show_tooltips_python 設定を確認
        show_python = bpy.context.preferences.view.show_tooltips_python

        # コンテンツがなければ None を返す
        if not any([self._title_text, self._description_text,
                    self._shortcut_text, self._python_text and show_python]):
            return None

        # 幅を計算
        width = self._calc_width()

        # レイアウト作成
        layout = GPULayout(x=x, y=y, width=width, style=self._style)
        layout._draw_background = True
        layout._draw_outline = True

        # タイトル
        if self._title_text:
            layout.label(text=self._title_text)

        # 説明文（折り返し）
        if self._description_text:
            if self._title_text:
                layout.separator(factor=0.5)

            lines = BLFDrawing.wrap_text(
                self._description_text,
                width - self._style.scaled_padding() * 2,
                self._style.scaled_text_size()
            )
            for line in lines:
                layout.label(text=line)

        # ショートカット
        if self._shortcut_text:
            layout.separator(factor=0.5)
            # グレー色で表示
            item = LabelItem(
                text=self._shortcut_text,
                text_color=self._style.text_color_secondary
            )
            layout._add_item(item)

        # Python コマンド
        if self._python_text and show_python:
            layout.separator(factor=0.5)
            # さらに暗いグレーで表示
            item = LabelItem(
                text=self._python_text,
                text_color=self._style.text_color_disabled
            )
            layout._add_item(item)

        return layout

    def calc_size(self, x: float = 0, y: float = 0) -> tuple[float, float]:
        """
        ツールチップのサイズを計算

        Returns:
            (width, height) タプル。コンテンツがなければ (0, 0)
        """
        layout = self._build_layout(x, y)
        if layout is None:
            return (0.0, 0.0)

        # レイアウト計算を実行
        layout.layout()
        return (layout.width, layout.calc_height())

    def draw(self, x: float, y: float) -> float:
        """
        ツールチップを描画

        Returns:
            描画した高さ（重ならないように次の要素を配置するため）
        """
        layout = self._build_layout(x, y)
        if layout is None:
            return 0.0

        layout.draw()
        return layout.calc_height()

    def _calc_width(self) -> float:
        """必要な幅を計算"""
        text_size = self._style.scaled_text_size()
        max_text_width = 0

        for text in [self._title_text, self._shortcut_text, self._python_text]:
            if text:
                w, _ = BLFDrawing.get_text_dimensions(text, text_size)
                max_text_width = max(max_text_width, w)

        # 説明文は折り返されるので max_width を超えない
        return min(max_text_width + self._style.scaled_padding() * 2, self.max_width)


# ═══════════════════════════════════════════════════════════════════════════════
# Example Usage - 使用例
# ═══════════════════════════════════════════════════════════════════════════════

def _example_draw_handler(self, context):
    """
    draw_handler での使用例

    登録:
        handler = bpy.types.SpaceView3D.draw_handler_add(
            _example_draw_handler, (None, None), 'WINDOW', 'POST_PIXEL'
        )
    """
    # ツールチップ
    tooltip = GPUTooltip(max_width=350)
    tooltip.title("Example Tooltip")
    tooltip.description("これはサンプルのツールチップです。長いテキストは自動的に折り返されます。")
    tooltip.shortcut("Ctrl + Shift + E")
    tooltip.python("bpy.ops.example.operator()")
    tooltip.draw(100, 500)

    # レイアウト
    layout = GPULayout(x=100, y=350, width=300)
    layout._draw_background = True
    layout._draw_outline = True

    layout.label(text="GPULayout Example", icon='INFO')
    layout.separator()

    row = layout.row()
    row.label(text="Left")
    row.label(text="Right")

    layout.separator()

    if context and context.object:
        layout.prop_display(context.object, "name", text="Object")
        layout.prop_display(context.object, "location", text="Location")

    layout.separator()
    layout.operator(text="Click Me", on_click=lambda: print("Button clicked!"))

    layout.draw()
