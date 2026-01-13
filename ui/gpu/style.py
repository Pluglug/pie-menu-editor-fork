# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Style System

Blender テーマ統合とスタイル定義。
"""

from __future__ import annotations

import bpy
from dataclasses import dataclass
from enum import Enum, auto


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

# Blender 4.0+ でシェーダー名が変更
SHADER_NAME = 'UNIFORM_COLOR' if bpy.app.version >= (4, 0, 0) else '2D_UNIFORM_COLOR'

# デフォルトフォント ID
FONT_ID = 0


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

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
