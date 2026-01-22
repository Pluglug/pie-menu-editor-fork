# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Style System

Blender テーマ統合とスタイル定義。
"""

from __future__ import annotations

import bpy
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


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
# Size / BoxConstraints - 2-pass レイアウト用
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Size:
    """
    サイズ（measure 結果）

    レイアウトアルゴリズムの Pass 1 (measure) で計算されるサイズ。
    """
    width: float = 0.0
    height: float = 0.0

    def __iter__(self):
        """(width, height) タプルとしてアンパック可能"""
        yield self.width
        yield self.height


@dataclass
class SizingPolicy:
    """Width sizing policy for measure/arrange."""
    estimated_width: float = 0.0
    fixed_width: Optional[float] = None
    is_fixed: bool = False
    min_width: float = 0.0
    max_width: float = float("inf")

@dataclass
class BoxConstraints:
    """
    親から子へ渡されるサイズ制約

    Flutter の BoxConstraints に相当。
    子要素は min_* 以上 max_* 以下のサイズに収まる必要がある。

    使用例:
        # 幅が固定、高さは無制限
        constraints = BoxConstraints.tight_width(300)

        # ゆるい制約（最大値のみ指定）
        constraints = BoxConstraints.loose(max_width=400, max_height=600)
    """
    min_width: float = 0.0
    max_width: float = float('inf')
    min_height: float = 0.0
    max_height: float = float('inf')

    @classmethod
    def tight(cls, width: float, height: float) -> 'BoxConstraints':
        """幅と高さを固定（min=max）"""
        return cls(min_width=width, max_width=width,
                   min_height=height, max_height=height)

    @classmethod
    def tight_width(cls, width: float) -> 'BoxConstraints':
        """幅のみ固定、高さは無制限"""
        return cls(min_width=width, max_width=width)

    @classmethod
    def loose(cls, max_width: float = float('inf'),
              max_height: float = float('inf')) -> 'BoxConstraints':
        """ゆるい制約（最大値のみ指定）"""
        return cls(max_width=max_width, max_height=max_height)

    def clamp_width(self, width: float) -> float:
        """幅を制約内にクランプ"""
        return max(self.min_width, min(width, self.max_width))

    def clamp_height(self, height: float) -> float:
        """高さを制約内にクランプ"""
        return max(self.min_height, min(height, self.max_height))

    def clamp_size(self, size: Size) -> Size:
        """サイズを制約内にクランプ"""
        return Size(
            self.clamp_width(size.width),
            self.clamp_height(size.height)
        )

    def deflate(self, horizontal: float, vertical: float) -> 'BoxConstraints':
        """
        パディングを差し引いた内部制約を作成

        Args:
            horizontal: 左右のパディング合計
            vertical: 上下のパディング合計
        """
        return BoxConstraints(
            min_width=max(0, self.min_width - horizontal),
            max_width=max(0, self.max_width - horizontal),
            min_height=max(0, self.min_height - vertical),
            max_height=max(0, self.max_height - vertical),
        )

    @property
    def has_tight_width(self) -> bool:
        """幅が固定されているか"""
        return self.min_width == self.max_width

    @property
    def has_tight_height(self) -> bool:
        """高さが固定されているか"""
        return self.min_height == self.max_height


class WidgetType(Enum):
    """
    ウィジェットタイプ（Blender の uiWidgetTypeEnum に対応）

    layout.prop() で使用するウィジェットの種類を指定。
    """
    REGULAR = auto()      # 通常ボタン（デフォルト）
    TOGGLE = auto()       # トグルボタン（Boolean with icon）
    OPTION = auto()       # チェックボックス（Boolean without icon）
    RADIO = auto()        # ラジオボタン（Enum expanded）
    NUMBER = auto()       # 数値フィールド（Int/Float）
    SLIDER = auto()       # スライダー（Int/Float with PERCENTAGE/FACTOR）
    TEXT = auto()         # テキスト入力（String）
    MENU = auto()         # メニューボタン（Enum dropdown）
    TOOL = auto()         # ツールボタン


# ═══════════════════════════════════════════════════════════════════════════════
# ThemeWidgetColors - Blender ウィジェットテーマ
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ThemeWidgetColors:
    """
    Blender の ThemeWidgetColors に対応するデータクラス

    各ウィジェットタイプ（スライダー、チェックボックス等）の
    カラー定義を保持する。

    Attributes:
        inner: 内部塗りつぶし（通常状態）- RGBA
        inner_sel: 内部塗りつぶし（選択状態）- RGBA
        item: アイテム色（スライダーつまみ、チェックマーク等）- RGBA
        outline: アウトライン（通常状態）- RGBA
        outline_sel: アウトライン（選択状態、存在しない場合は outline と同じ）- RGBA
        text: テキスト色（通常状態）- RGBA
        text_sel: テキスト色（選択状態）- RGBA
        roundness: 角丸係数 [0.0-1.0]
        shadetop: 上部シェーディング [-100, 100]（グラデーション用）
        shadedown: 下部シェーディング [-100, 100]（グラデーション用）
        show_shaded: シェーディング有効化フラグ

    Note:
        - Blender テーマの wcol_* 属性から直接読み込むことを想定。
        - GPU 描画では shadetop/shadedown を使わず inner を直接使用することが多い。
        - **重要**: Blender API では text/text_sel は RGB (3要素) だが、
          このクラスでは GPU 描画の便宜上 RGBA (4要素) で保持する。
          from_blender_wcol() で自動的に alpha=1.0 を追加。
    """
    inner: tuple[float, float, float, float] = (0.3, 0.3, 0.3, 1.0)
    inner_sel: tuple[float, float, float, float] = (0.4, 0.5, 0.7, 1.0)
    item: tuple[float, float, float, float] = (0.5, 0.5, 0.5, 1.0)
    outline: tuple[float, float, float, float] = (0.1, 0.1, 0.1, 1.0)
    outline_sel: tuple[float, float, float, float] = (0.2, 0.3, 0.5, 1.0)
    text: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    text_sel: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    roundness: float = 0.4
    shadetop: int = 0
    shadedown: int = 0
    show_shaded: bool = False

    @classmethod
    def from_blender_wcol(cls, wcol) -> ThemeWidgetColors:
        """
        Blender の wcol_* 属性から ThemeWidgetColors を作成

        Args:
            wcol: bpy.context.preferences.themes[0].user_interface.wcol_*

        Returns:
            ThemeWidgetColors インスタンス
        """
        def to_rgba(color, alpha: float = 1.0) -> tuple[float, float, float, float]:
            """色を RGBA タプルに変換"""
            c = tuple(color)
            if len(c) == 3:
                return c + (alpha,)
            return c

        return cls(
            inner=to_rgba(wcol.inner),
            inner_sel=to_rgba(wcol.inner_sel),
            item=to_rgba(wcol.item),
            outline=to_rgba(wcol.outline),
            # outline_sel は一部のテーマにしか存在しない
            outline_sel=to_rgba(wcol.outline) if not hasattr(wcol, 'outline_sel') else to_rgba(wcol.outline_sel),
            text=to_rgba(wcol.text),
            text_sel=to_rgba(wcol.text_sel),
            roundness=wcol.roundness,
            shadetop=wcol.shadetop,
            shadedown=wcol.shadedown,
            show_shaded=wcol.show_shaded,
        )


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

    # ═══════════════════════════════════════════════════════════════════════════
    # レイアウト調整用パラメータ（Blender 標準 UI 準拠）
    # ═══════════════════════════════════════════════════════════════════════════

    # パディング: パネル内側の余白（ピクセル、UI スケール前）
    padding_x: int = 7   # 左右パディング [推奨: 4-10]
    padding_y: int = 5   # 上下パディング [推奨: 3-8]

    # スペーシング: 要素間の間隔（ピクセル、UI スケール前）
    spacing: int = 2     # 縦方向スペース [推奨: 1-4, Blender標準≈2]
    spacing_x: Optional[int] = None  # 横方向スペース（None の場合は spacing を使用）

    # アイテムサイズ
    item_height: int = 20  # 各アイテムの高さ [推奨: 18-24, Blender標準≈20]

    # 角丸
    border_radius: int = 4  # パネル/ボタンの角丸 [推奨: 2-8, Blender標準≈4]
    roundness: float = 0.4  # テーマから取得する角丸係数 [0.0-1.0]

    # プロパティスプリット (use_property_split=True 時のラベル/ウィジェット分割)
    # Blender 標準では約 0.4 (40%) がラベル領域
    split_factor: float = 0.4  # ラベル領域の幅比率 [0.2-0.5, Blender標準≈0.4]

    # タイトルバー
    title_bar_height: int = 22  # タイトルバー高さ [推奨: 20-26, Blender標準≈22]

    # ═══════════════════════════════════════════════════════════════════════════
    # ドロップシャドウ（パネル/メニュー用）
    # ═══════════════════════════════════════════════════════════════════════════

    shadow_enabled: bool = True  # シャドウ有効/無効
    shadow_width: int = 6        # 影の幅 [menu_shadow_width から取得]
    shadow_alpha: float = 0.2    # 影の透明度 [menu_shadow_fac から取得]

    # ═══════════════════════════════════════════════════════════════════════════
    # テキストシャドウ
    # ═══════════════════════════════════════════════════════════════════════════

    text_shadow_enabled: bool = True  # テキストシャドウ有効/無効
    text_shadow_color: float = 0.0    # シャドウ色 [0.0=黒, 1.0=白]
    text_shadow_alpha: float = 0.5    # シャドウ透明度 [0.0-1.0]
    text_shadow_offset: tuple[int, int] = (1, -1)  # (x, y) オフセット [推奨: 1-2]

    # ═══════════════════════════════════════════════════════════════════════════
    # ウィジェットテーマ（layout.prop() 用）
    # ═══════════════════════════════════════════════════════════════════════════
    #
    # 各ウィジェットタイプに対応したテーマカラー。
    # Blender の wcol_* 属性から読み込む。
    #
    # 対応マッピング（gpu_theme_widget_mapping.md 参照）:
    #   wcol_numslider → スライダー (PERCENTAGE/FACTOR)
    #   wcol_num       → 数値フィールド (Int/Float)
    #   wcol_option    → チェックボックス (Boolean without icon)
    #   wcol_toggle    → トグルボタン (Boolean with icon)
    #   wcol_text      → テキスト入力 (String)
    #   wcol_menu      → メニューボタン (Enum dropdown)
    #   wcol_menu_back → メニューパネル背景
    #   wcol_menu_item → メニューアイテム
    #   wcol_pulldown  → プルダウンメニュー（ヘッダー）
    #   wcol_pie_menu  → パイメニュー
    #   wcol_radio     → ラジオボタン (Enum expanded)
    #   wcol_regular   → 通常ボタン (デフォルト)
    #   wcol_tool      → ツールボタン
    #

    wcol_regular: Optional[ThemeWidgetColors] = field(default=None)
    wcol_numslider: Optional[ThemeWidgetColors] = field(default=None)
    wcol_num: Optional[ThemeWidgetColors] = field(default=None)
    wcol_option: Optional[ThemeWidgetColors] = field(default=None)
    wcol_toggle: Optional[ThemeWidgetColors] = field(default=None)
    wcol_text: Optional[ThemeWidgetColors] = field(default=None)
    wcol_menu: Optional[ThemeWidgetColors] = field(default=None)
    wcol_menu_back: Optional[ThemeWidgetColors] = field(default=None)
    wcol_menu_item: Optional[ThemeWidgetColors] = field(default=None)
    wcol_pulldown: Optional[ThemeWidgetColors] = field(default=None)
    wcol_pie_menu: Optional[ThemeWidgetColors] = field(default=None)
    wcol_radio: Optional[ThemeWidgetColors] = field(default=None)
    wcol_tool: Optional[ThemeWidgetColors] = field(default=None)

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
            - PANEL スタイルは panel_* 専用フィールドを使用（wcol_* ではない）
        """
        try:
            prefs = bpy.context.preferences
            theme = prefs.themes[0]
            ui = theme.user_interface
            ui_styles = prefs.ui_styles[0]
            default_style = cls()

            # ヘルパー関数: 色を RGBA に変換
            def to_rgba(color, alpha: float = 1.0) -> tuple[float, float, float, float]:
                """色を RGBA タプルに変換"""
                c = tuple(color)
                if len(c) == 3:
                    return c + (alpha,)
                return c

            # ボタン用のカラーを取得（wcol_tool を使用）
            wcol_button = ui.wcol_tool

            # ThemeFontStyle からシャドウ設定を取得
            font_style = ui_styles.widget
            shadow_type = font_style.shadow  # 0=none, 3=shadow, 5=blur, 6=outline
            shadow_enabled = shadow_type > 0

            spacing_x = getattr(ui_styles, "buttonspacex", default_style.spacing_x)
            spacing_y = getattr(ui_styles, "buttonspacey", default_style.spacing)

            # ウィジェットテーマを読み込み（layout.prop() 用）
            # 各 wcol_* から ThemeWidgetColors を作成
            widget_themes = {}
            for wcol_attr in ['wcol_regular', 'wcol_numslider', 'wcol_num',
                              'wcol_option', 'wcol_toggle', 'wcol_text',
                              'wcol_menu', 'wcol_menu_back', 'wcol_menu_item',
                              'wcol_pulldown', 'wcol_pie_menu',
                              'wcol_radio', 'wcol_tool']:
                try:
                    widget_themes[wcol_attr] = ThemeWidgetColors.from_blender_wcol(
                        getattr(ui, wcol_attr)
                    )
                except Exception:
                    widget_themes[wcol_attr] = None

            # ═══════════════════════════════════════════════════════════════════════
            # PANEL スタイル: 専用の panel_* フィールドを使用
            # ═══════════════════════════════════════════════════════════════════════
            #
            # Blender には Panel 専用のテーマフィールドがある:
            #   - panel_back: パネル背景
            #   - panel_header: ヘッダー背景（ホバー/選択時に使用）
            #   - panel_sub_back: サブパネル背景
            #   - panel_outline: 非アクティブ時ボーダー
            #   - panel_active: アクティブ時ボーダー
            #   - panel_roundness: 角丸係数 [0.0-1.0]
            #   - panel_title: タイトルテキスト色
            #   - panel_text: 一般テキスト色
            #
            if style_name == 'PANEL':
                roundness_val = ui.panel_roundness
                base_radius = int(roundness_val * 10)

                # TODO: panel_outline/panel_active はアルファが低く設定されていることが多い。
                #       将来的に panel_* を使用する場合はアルファ補正を検討。
                #       現時点では wcol_regular のアウトラインを使用。
                wcol_regular = ui.wcol_regular

                return cls(
                    # 背景（通常状態）
                    bg_color=to_rgba(ui.panel_back),
                    outline_color=to_rgba(wcol_regular.outline),

                    # 背景（選択/ホバー状態）
                    bg_color_sel=to_rgba(ui.panel_header),
                    outline_color_sel=to_rgba(wcol_regular.outline),

                    # アイテム色（wcol_regular から取得）
                    item_color=to_rgba(ui.wcol_regular.item),

                    # テキスト（通常状態）
                    text_color=to_rgba(ui.panel_text),
                    text_color_secondary=to_rgba(ui.panel_text, 0.7),
                    text_color_disabled=to_rgba(ui.panel_text, 0.4),

                    # テキスト（選択状態）
                    text_color_sel=to_rgba(ui.panel_title),

                    text_size=int(font_style.points),

                    # ボタン（wcol_tool から取得）
                    button_color=to_rgba(wcol_button.inner),
                    button_hover_color=to_rgba(wcol_button.inner_sel),
                    button_press_color=to_rgba(wcol_button.item),
                    button_text_color=to_rgba(wcol_button.text),

                    # 特殊色
                    alert_color=(0.8, 0.2, 0.2, 1.0),
                    highlight_color=to_rgba(ui.panel_header),

                    # 区切り線（アウトラインより少し暗く）
                    separator_color=to_rgba(ui.panel_outline, 0.5),

                    # レイアウト
                    border_radius=base_radius,
                    roundness=roundness_val,
                    spacing=spacing_y,
                    spacing_x=spacing_x,

                    # ドロップシャドウ
                    # 【調整可能】影の濃さ: ui.menu_shadow_fac * 係数 (例: * 1.2 で濃く, * 0.8 で薄く)
                    shadow_width=ui.menu_shadow_width,
                    shadow_alpha=ui.menu_shadow_fac,

                    # テキストシャドウ
                    text_shadow_enabled=shadow_enabled,
                    text_shadow_color=font_style.shadow_value,
                    text_shadow_alpha=font_style.shadow_alpha,
                    text_shadow_offset=(font_style.shadow_offset_x, font_style.shadow_offset_y),

                    # ウィジェットテーマ
                    wcol_regular=widget_themes.get('wcol_regular'),
                    wcol_numslider=widget_themes.get('wcol_numslider'),
                    wcol_num=widget_themes.get('wcol_num'),
                    wcol_option=widget_themes.get('wcol_option'),
                    wcol_toggle=widget_themes.get('wcol_toggle'),
                    wcol_text=widget_themes.get('wcol_text'),
                    wcol_menu=widget_themes.get('wcol_menu'),
                    wcol_menu_back=widget_themes.get('wcol_menu_back'),
                    wcol_menu_item=widget_themes.get('wcol_menu_item'),
                    wcol_pulldown=widget_themes.get('wcol_pulldown'),
                    wcol_pie_menu=widget_themes.get('wcol_pie_menu'),
                    wcol_radio=widget_themes.get('wcol_radio'),
                    wcol_tool=widget_themes.get('wcol_tool'),
                )

            # ═══════════════════════════════════════════════════════════════════════
            # その他のスタイル: wcol_* から取得
            # ═══════════════════════════════════════════════════════════════════════

            # スタイル名からテーマ属性を取得
            # Note: MENU は「ドロップダウンボタン」、MENU_BACK は「メニューパネル背景」
            style_map = {
                'TOOLTIP': 'wcol_tooltip',
                'BOX': 'wcol_box',
                'REGULAR': 'wcol_regular',
                'TOOL': 'wcol_tool',
                'RADIO': 'wcol_radio',
                'PIE_MENU': 'wcol_pie_menu',
                'MENU': 'wcol_menu',           # ドロップダウンボタン
                'MENU_BACK': 'wcol_menu_back', # メニューパネル背景
                'MENU_ITEM': 'wcol_menu_item',
                'PULLDOWN': 'wcol_pulldown',   # プルダウンメニュー（ヘッダー）
                'TOGGLE': 'wcol_toggle',
                'OPTION': 'wcol_option',
                'NUM': 'wcol_num',
                'NUMSLIDER': 'wcol_numslider',
            }
            wcol_name = style_map.get(style_name, 'wcol_tooltip')
            wcol = getattr(ui, wcol_name)

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
                border_radius=base_radius,  # roundness を忠実に反映
                roundness=roundness_val,
                spacing=spacing_y,
                spacing_x=spacing_x,

                # ドロップシャドウ（Blender テーマから取得）
                # 【調整可能】影の濃さ: ui.menu_shadow_fac * 係数 (例: * 1.2 で濃く, * 0.8 で薄く)
                shadow_width=ui.menu_shadow_width,
                shadow_alpha=ui.menu_shadow_fac,

                # テキストシャドウ（ThemeFontStyle から取得）
                text_shadow_enabled=shadow_enabled,
                text_shadow_color=font_style.shadow_value,  # 0.0=黒, 1.0=白
                text_shadow_alpha=font_style.shadow_alpha,
                text_shadow_offset=(font_style.shadow_offset_x, font_style.shadow_offset_y),

                # ウィジェットテーマ（layout.prop() 用）
                wcol_regular=widget_themes.get('wcol_regular'),
                wcol_numslider=widget_themes.get('wcol_numslider'),
                wcol_num=widget_themes.get('wcol_num'),
                wcol_option=widget_themes.get('wcol_option'),
                wcol_toggle=widget_themes.get('wcol_toggle'),
                wcol_text=widget_themes.get('wcol_text'),
                wcol_menu=widget_themes.get('wcol_menu'),
                wcol_menu_back=widget_themes.get('wcol_menu_back'),
                wcol_menu_item=widget_themes.get('wcol_menu_item'),
                wcol_pulldown=widget_themes.get('wcol_pulldown'),
                wcol_pie_menu=widget_themes.get('wcol_pie_menu'),
                wcol_radio=widget_themes.get('wcol_radio'),
                wcol_tool=widget_themes.get('wcol_tool'),
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

    def scaled_padding_x(self) -> int:
        """スケーリングされた左右パディング"""
        return int(self.ui_scale(self.padding_x))

    def scaled_padding_y(self) -> int:
        """スケーリングされた上下パディング"""
        return int(self.ui_scale(self.padding_y))

    def scaled_padding(self) -> int:
        """後方互換用（左右パディングを返す）"""
        return self.scaled_padding_x()

    def scaled_spacing(self) -> int:
        """後方互換用（縦方向スペーシング）"""
        return int(self.ui_scale(self.spacing))

    def scaled_spacing_x(self) -> int:
        """スケーリングされた横方向スペーシング"""
        spacing_x = self.spacing_x if self.spacing_x is not None else self.spacing
        return int(self.ui_scale(spacing_x))

    def scaled_item_height(self) -> int:
        return int(self.ui_scale(self.item_height))

    def scaled_text_size(self) -> int:
        return int(self.ui_scale(self.text_size))

    def scaled_border_radius(self) -> int:
        return int(self.ui_scale(self.border_radius))

    def scaled_shadow_width(self) -> int:
        """スケーリングされた影の幅"""
        return int(self.ui_scale(self.shadow_width))

    def scaled_text_shadow_offset(self) -> tuple[int, int]:
        """スケーリングされたテキストシャドウオフセット"""
        return (
            int(self.ui_scale(self.text_shadow_offset[0])),
            int(self.ui_scale(self.text_shadow_offset[1]))
        )

    def scaled_title_bar_height(self) -> int:
        """スケーリングされたタイトルバー高さ"""
        return int(self.ui_scale(self.title_bar_height))

    def scaled_icon_size(self) -> int:
        """スケーリングされたアイコンサイズ"""
        return int(self.ui_scale(20))  # base: 20px (Blender standard)

    # ═══════════════════════════════════════════════════════════════════════════
    # ウィジェットテーマ取得
    # ═══════════════════════════════════════════════════════════════════════════

    def get_widget_colors(self, widget_type: WidgetType) -> ThemeWidgetColors:
        """
        ウィジェットタイプに応じたテーマカラーを取得

        Args:
            widget_type: ウィジェットの種類 (WidgetType 列挙)

        Returns:
            対応する ThemeWidgetColors。
            見つからない場合は wcol_regular、それもなければデフォルト値。

        Example:
            style = GPULayoutStyle.from_blender_theme('TOOLTIP')
            slider_colors = style.get_widget_colors(WidgetType.SLIDER)
            # slider_colors.inner, slider_colors.item などで描画
        """
        # WidgetType → wcol_* 属性マッピング
        mapping = {
            WidgetType.REGULAR: self.wcol_regular,
            WidgetType.TOGGLE: self.wcol_toggle,
            WidgetType.OPTION: self.wcol_option,
            WidgetType.RADIO: self.wcol_radio,
            WidgetType.NUMBER: self.wcol_num,
            WidgetType.SLIDER: self.wcol_numslider,
            WidgetType.TEXT: self.wcol_text,
            WidgetType.MENU: self.wcol_menu,
            WidgetType.TOOL: self.wcol_tool,
        }

        colors = mapping.get(widget_type)

        # フォールバック: wcol_regular → デフォルト
        if colors is None:
            colors = self.wcol_regular
        if colors is None:
            colors = ThemeWidgetColors()

        return colors

    def get_widget_colors_by_name(self, wcol_name: str) -> ThemeWidgetColors:
        """
        テーマ属性名から直接テーマカラーを取得

        Args:
            wcol_name: 'wcol_numslider', 'wcol_num' など

        Returns:
            対応する ThemeWidgetColors。
            見つからない場合はデフォルト値。
        """
        attr_map = {
            'wcol_regular': self.wcol_regular,
            'wcol_numslider': self.wcol_numslider,
            'wcol_num': self.wcol_num,
            'wcol_option': self.wcol_option,
            'wcol_toggle': self.wcol_toggle,
            'wcol_text': self.wcol_text,
            'wcol_menu': self.wcol_menu,
            'wcol_menu_back': self.wcol_menu_back,
            'wcol_menu_item': self.wcol_menu_item,
            'wcol_pulldown': self.wcol_pulldown,
            'wcol_pie_menu': self.wcol_pie_menu,
            'wcol_radio': self.wcol_radio,
            'wcol_tool': self.wcol_tool,
        }

        colors = attr_map.get(wcol_name)
        if colors is None:
            colors = self.wcol_regular
        if colors is None:
            colors = ThemeWidgetColors()

        return colors
