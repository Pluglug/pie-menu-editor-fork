# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Main Layout Class

Blender UILayout API を模した GPU 描画レイアウトシステム。
"""

from __future__ import annotations

import bpy
import sys
from typing import TYPE_CHECKING, Any, Callable, Optional

from .style import GPULayoutStyle, Direction, Alignment, Size, BoxConstraints
from .drawing import GPUDrawing, BLFDrawing
from .items import (
    LayoutItem, LabelItem, SeparatorItem, ButtonItem, ToggleItem,
    PropDisplayItem, BoxItem, SliderItem, NumberItem, CheckboxItem,
    ColorItem, RadioGroupItem, RadioOption
)
from .interactive import HitTestManager, HitRect
from .rna_utils import (
    get_property_info, get_property_value, set_property_value,
    PropType, WidgetHint, PropertyInfo
)
from .binding import ContextResolverCache, PropertyBinding
from .context import TrackedAccess
from .uilayout_stubs import UILayoutStubMixin, OperatorProperties
from ...infra.debug import DBG_GPU, logi

if TYPE_CHECKING:
    from bpy.types import Event

# プラットフォーム検出
IS_MAC = sys.platform == 'darwin'

# パネルリサイズ定数
MIN_PANEL_WIDTH = 200
MIN_PANEL_HEIGHT = 100  # 将来用（高さリサイズ時）
RESIZE_HANDLE_SIZE = 16  # UI スケーリング前のピクセル

# パネル境界クランプ定数
CLAMP_MARGIN = 20  # エリア端からの最小マージン（ピクセル）


class GPULayout(UILayoutStubMixin):
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

        # 統合要素リスト（追加順序を保持）
        # Phase 1: _items と _children を _elements に統合
        self._elements: list[LayoutItem | GPULayout] = []

        # 2-pass レイアウト用の測定結果
        self._measured_widths: list[float] = []
        self.height: float = 0.0  # estimate() で計算される

        # Phase 1 v3: 推定サイズ（estimate フェーズで自然サイズを記録）
        # resolve フェーズで幅配分アルゴリズムの入力として使用
        self.estimated_width: float = 0.0
        self.estimated_height: float = 0.0

        # カーソル位置
        self._cursor_x = x + self.style.scaled_padding_x()
        self._cursor_y = y - self.style.scaled_padding_y()

        # 状態プロパティ（UILayout 互換）
        self.active: bool = True
        self.active_default: bool = False  # Return key activates operator button
        self.activate_init: bool = False   # Auto-activate buttons in popups
        self.enabled: bool = True
        self.alert: bool = False
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.alignment: Alignment = Alignment.EXPAND
        # emboss: 'NORMAL', 'NONE', 'PULLDOWN_MENU', 'PIE_MENU', 'NONE_OR_STATUS'
        self.emboss: str = "NORMAL"
        # ui_units for fixed sizing
        self.ui_units_x: float = 0.0
        self.ui_units_y: float = 0.0
        # Property layout options
        self.use_property_split: bool = False
        self.use_property_decorate: bool = False
        self.operator_context: str = "INVOKE_DEFAULT"

        # アイテム間スペースを制御（align=True で 0）
        self._align: bool = False

        # split 用（0.0 = 自動計算、0.0-1.0 = 最初の column の割合）
        self._split_factor: float = 0.0
        self._is_split: bool = False
        self._split_column_index: int = 0  # column() が呼ばれるたびにインクリメント

        # ボックス描画フラグ
        self._draw_background: bool = False
        self._draw_outline: bool = False

        # タイトルバー
        self._show_title_bar: bool = False
        self._title: str = ""
        self._show_close_button: bool = False
        self._on_close: Optional[Callable[[], None]] = None
        self._title_bar_rect: Optional[HitRect] = None
        self._close_button_rect: Optional[HitRect] = None
        self._close_button_hovered: bool = False

        self._hit_manager: Optional[HitTestManager] = None

        # Dirty Flag: レイアウト再計算が必要かどうか
        self._dirty: bool = True

        # リサイズハンドル
        self._show_resize_handle: bool = False
        self._resize_handle_rect: Optional[HitRect] = None
        self._resize_handle_hovered: bool = False
        self._panel_uid: Optional[str] = None
        self._min_width: float = MIN_PANEL_WIDTH

        # 境界クランプ用のリージョンサイズ（None = クランプ無効）
        self._region_width: Optional[float] = None
        self._region_height: Optional[float] = None

        # prop() reactive bindings (context-resolved) and static fallback
        self._context_tracker: Optional[Any] = None
        self._context_cache = ContextResolverCache()
        self._bindings: list[PropertyBinding] = []
        self._static_bindings: list[PropertyBinding] = []
        self._epoch = 0

    # ─────────────────────────────────────────────────────────────────────────
    # コンテナメソッド（UILayout 互換）
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def hit_manager(self) -> Optional[HitTestManager]:
        """HitTestManager（未使用なら None）"""
        return self._hit_manager

    @property
    def dirty(self) -> bool:
        """レイアウト再計算が必要かどうか"""
        return self._dirty

    # ─────────────────────────────────────────────────────────────────────────
    # 後方互換プロパティ（_items, _children）
    # Phase 1 で _elements に統合したが、既存コードとの互換性のため提供
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def _items(self) -> list[LayoutItem]:
        """LayoutItem のみをフィルタして返す（後方互換）"""
        return [e for e in self._elements if isinstance(e, LayoutItem)]

    @property
    def _children(self) -> list['GPULayout']:
        """GPULayout のみをフィルタして返す（後方互換）"""
        return [e for e in self._elements if isinstance(e, GPULayout)]

    def mark_dirty(self) -> None:
        """レイアウトの再計算が必要であることをマーク"""
        self._dirty = True
        for element in self._elements:
            if isinstance(element, GPULayout):
                element.mark_dirty()

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
        child.operator_context = self.operator_context
        child._align = align  # アイテム間スペースを制御
        self._elements.append(child)  # Phase 1: _elements に統合
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

            v3 アルゴリズム (3列以上対応):
            - 最初の列: factor 割合
            - 2番目以降: 残り幅を (n-1) で均等分割
            例: factor=0.25 で 3列 → 25% : 37.5% : 37.5%

            幅の確定は resolve フェーズで行われる。
            ここでは親の幅をプレースホルダとして設定。
        """
        available_width = self._get_available_width()

        # v3: 幅は resolve フェーズで確定する
        # ここでは親の幅をプレースホルダとして使用
        # split レイアウトかどうかは _is_split で判定
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
        child.operator_context = self.operator_context
        child._align = align
        self._elements.append(child)  # Phase 1: _elements に統合

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
        child._is_split = True
        child._align = align
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        child.operator_context = self.operator_context
        self._elements.append(child)  # Phase 1: _elements に統合
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

    def separator(self, *, factor: float = 1.0, type: str = "AUTO") -> None:
        """
        区切り線を追加

        Args:
            factor: スペースの倍率（デフォルト 1.0）
            type: 'AUTO', 'SPACE', 'LINE' (現在は LINE として描画)
        """
        # Note: type パラメータは UILayout 互換のため受け取るが、
        # 現在は常に LINE スタイルで描画される
        item = SeparatorItem(factor=factor)
        self._add_item(item)

    def separator_spacer(self) -> None:
        """スペーサーを追加（separator のエイリアス）"""
        self.separator(factor=0.5)

    def operator(
        self,
        operator: str = "",
        *,
        text: str = "",
        icon: str = "NONE",
        icon_value: int = 0,
        emboss: bool = True,
        depress: Optional[bool] = None,
        enabled: bool = True,
        active: bool = True,
        on_click: Optional[Callable[[], None]] = None,
        **props,
    ) -> OperatorProperties:
        """
        オペレーターボタンを追加

        Args:
            operator: オペレーター bl_idname（例: "mesh.primitive_cube_add"）
            text: ボタンラベル（空の場合は operator 名を使用）
            icon: アイコン名
            icon_value: カスタムアイコン ID（GPU 描画では未対応）
            emboss: Blender 互換のフラグ（GPU 描画では未対応）
            depress: Blender 互換のフラグ（GPU 描画では未対応）
            enabled: ボタンの有効/無効
            active: ボタンのアクティブ状態
            on_click: クリック時のコールバック（指定時は operator を実行しない）
            **props: オペレーターに渡すプロパティ

        Returns:
            OperatorProperties - プロパティ代入を受け付けるダミーオブジェクト

        Note:
            on_click が未指定の場合は bpy.ops を呼び出します。
            operator が空の場合はクリックしても何もしません。
            operator_context は layout.operator_context を使用します。

            返り値の OperatorProperties は UILayout.operator() 互換のため、
            以下のような典型的な書き方が動作します：
                op = layout.operator("mesh.primitive_cube_add")
                op.size = 2.0  # AttributeError にならない（PME 互換）

            **props と後続の属性代入は結合され、クリック時に bpy.ops に渡されます。
        """
        if icon_value and DBG_GPU:
            logi("[GPULayout] operator() icon_value ignored:", icon_value)

        op_props = OperatorProperties(operator, props)

        def invoke_operator() -> None:
            if on_click is not None:
                on_click()
                return

            if not operator:
                return

            try:
                module_name, op_name = operator.split(".", 1)
            except ValueError:
                if DBG_GPU:
                    logi("[GPULayout] Invalid operator idname:", operator)
                return

            try:
                module = getattr(bpy.ops, module_name)
                op_fn = getattr(module, op_name)
            except AttributeError:
                if DBG_GPU:
                    logi("[GPULayout] Operator not found:", operator)
                return

            context_mode = self.operator_context or "INVOKE_DEFAULT"
            try:
                op_fn(context_mode, **op_props.props)
            except Exception as exc:
                if DBG_GPU:
                    logi("[GPULayout] Operator invoke failed:", operator, exc)
                try:
                    op_fn(**op_props.props)
                except Exception as exc2:
                    if DBG_GPU:
                        logi("[GPULayout] Operator exec failed:", operator, exc2)

        click_handler = invoke_operator if (on_click is not None or operator) else None

        item = ButtonItem(
            text=text or operator,
            icon=icon,
            on_click=click_handler,
            enabled=self.enabled and self.active and enabled and active,
        )
        self._add_item(item)

        # OperatorProperties を返す（プロパティ代入を受け付ける）
        # ButtonItem への参照を保持（将来の拡張用）
        object.__setattr__(op_props, "_button_item", item)
        return op_props

    def slider(self, *, value: float = 0.0, min_val: float = 0.0, max_val: float = 1.0,
               precision: int = 2, text: str = "",
               on_change: Optional[Callable[[float], None]] = None) -> SliderItem:
        """
        スライダーを追加

        Args:
            value: 初期値
            min_val: 最小値
            max_val: 最大値
            precision: 表示精度（小数点以下の桁数）
            text: ラベルテキスト（空の場合は値のみ表示）
            on_change: 値変更時のコールバック

        Returns:
            作成された SliderItem（外部から値を取得/設定可能）

        使用例:
            # 基本的な使い方
            layout.slider(value=0.5, text="Opacity")

            # コールバック付き
            def on_value_change(value):
                print(f"Value: {value}")
            layout.slider(value=50, min_val=0, max_val=100, text="Size", on_change=on_value_change)
        """
        item = SliderItem(
            value=value,
            min_val=min_val,
            max_val=max_val,
            precision=precision,
            text=text,
            on_change=on_change,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item

    def number(self, *, value: float = 0.0, min_val: float = -float('inf'),
               max_val: float = float('inf'), step: float = 0.01,
               precision: int = 2, text: str = "", show_buttons: bool = False,
               on_change: Optional[Callable[[float], None]] = None) -> NumberItem:
        """
        数値フィールドを追加

        Args:
            value: 初期値
            min_val: 最小値（デフォルト: 無制限）
            max_val: 最大値（デフォルト: 無制限）
            step: ドラッグ時の変化量（ピクセルあたり）
            precision: 表示精度（小数点以下の桁数）
            text: ラベルテキスト（空の場合は値のみ表示）
            show_buttons: 増減ボタン（◀ ▶）を表示するか
            on_change: 値変更時のコールバック

        Returns:
            作成された NumberItem（外部から値を取得/設定可能）

        使用例:
            # 基本的な使い方
            layout.number(value=10.0, text="Count")

            # 範囲とボタン付き
            layout.number(value=5, min_val=0, max_val=100, show_buttons=True, text="Level")

            # コールバック付き
            def on_value_change(value):
                print(f"Value: {value}")
            layout.number(value=0.5, step=0.1, text="Factor", on_change=on_value_change)
        """
        item = NumberItem(
            value=value,
            min_val=min_val,
            max_val=max_val,
            step=step,
            precision=precision,
            text=text,
            show_buttons=show_buttons,
            on_change=on_change,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item

    def checkbox(self, *, text: str = "", value: bool = False,
                 on_toggle: Optional[Callable[[bool], None]] = None) -> CheckboxItem:
        """
        チェックボックスを追加

        Args:
            text: ラベルテキスト
            value: 初期値
            on_toggle: 値変更時のコールバック

        Returns:
            作成された CheckboxItem（外部から値を取得/設定可能）

        使用例:
            # 基本的な使い方
            layout.checkbox(text="Enable Feature", value=True)

            # コールバック付き
            def on_toggle(value):
                print(f"Checkbox: {value}")
            layout.checkbox(text="Auto Save", on_toggle=on_toggle)
        """
        item = CheckboxItem(
            text=text,
            value=value,
            on_toggle=on_toggle,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item

    def radio_group(self, *, options: list = None, value: str = "",
                    on_change: Optional[Callable[[str], None]] = None) -> RadioGroupItem:
        """
        ラジオボタングループを追加

        Args:
            options: 選択肢のリスト。以下の形式をサポート:
                - RadioOption オブジェクト
                - (value, label, icon) タプル
                - (value, label) タプル
                - (value,) タプル
                - 文字列（value として使用）
            value: 初期選択値
            on_change: 値変更時のコールバック

        Returns:
            作成された RadioGroupItem（外部から値を取得/設定可能）

        使用例:
            # 基本的な使い方
            layout.radio_group(
                options=[("A", "Option A"), ("B", "Option B"), ("C", "Option C")],
                value="A"
            )

            # アイコン付き
            layout.radio_group(
                options=[
                    ("OBJECT", "Object", "OBJECT_DATA"),
                    ("EDIT", "Edit", "EDITMODE_HLT"),
                    ("SCULPT", "Sculpt", "SCULPTMODE_HLT"),
                ],
                value="OBJECT"
            )

            # コールバック付き
            def on_mode_change(value):
                print(f"Mode: {value}")
            layout.radio_group(options=["A", "B", "C"], on_change=on_mode_change)
        """
        item = RadioGroupItem(
            options=options or [],
            value=value,
            on_change=on_change,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item

    def toggle(self, *, text: str = "", icon: str = "NONE",
               icon_on: str = "NONE", icon_off: str = "NONE",
               value: bool = False,
               on_toggle: Optional[Callable[[bool], None]] = None) -> ToggleItem:
        """
        トグルボタンを追加

        Args:
            text: ボタンラベル
            icon: デフォルトアイコン
            icon_on: ON 状態のアイコン（指定時のみ）
            icon_off: OFF 状態のアイコン（指定時のみ）
            value: 初期値
            on_toggle: 値変更時のコールバック

        Returns:
            作成された ToggleItem（外部から値を取得/設定可能）

        使用例:
            # 基本的な使い方
            layout.toggle(text="Preview", value=True)

            # アイコン切り替え
            layout.toggle(text="Visible", icon_on='RESTRICT_VIEW_OFF', icon_off='RESTRICT_VIEW_ON')

            # コールバック付き
            def on_toggle(value):
                print(f"Toggle: {value}")
            layout.toggle(text="Active", icon='BLENDER', on_toggle=on_toggle)
        """
        item = ToggleItem(
            text=text,
            icon=icon,
            icon_on=icon_on,
            icon_off=icon_off,
            value=value,
            on_toggle=on_toggle,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item

    def color(self, *, color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
              text: str = "",
              on_click: Optional[Callable[[], None]] = None) -> ColorItem:
        """
        カラースウォッチを追加

        Blender スタイルの横長カラーバー。左=RGB、右=RGBA(チェッカー)。

        Args:
            color: 表示する色 (R, G, B, A) - 各値は 0.0-1.0
            text: ラベルテキスト（空の場合はカラーバーのみ）
            on_click: クリック時のコールバック

        Returns:
            作成された ColorItem（外部から色を取得/設定可能）

        TODO(layout.prop統合):
            - use_property_split=True: ラベルをレイアウト側で左に配置
            - use_property_split=False: text+":"を上の行、カラーバーを下の行（2行構成）
            - text="": カラーバーのみ
            - HitRect をカラーバー部分のみに設定（get_bar_rect() 使用）

        使用例:
            # 基本的な使い方（row 全体に広がる）
            layout.color(color=(1.0, 0.0, 0.0, 1.0))

            # ラベル付き
            layout.color(color=(0.2, 0.5, 1.0, 1.0), text="Diffuse")

            # 半透明（右側にチェッカーが表示される）
            layout.color(color=(1.0, 1.0, 0.0, 0.5), text="Alpha 50%")
        """
        item = ColorItem(
            color=color,
            text=text,
            on_click=on_click,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item

    # ─────────────────────────────────────────────────────────────────────────
    # プロパティメソッド
    # ─────────────────────────────────────────────────────────────────────────

    def _unwrap_data(self, data: Any) -> Any:
        if isinstance(data, TrackedAccess):
            return data.unwrapped
        return data

    def _infer_resolver(self, data: Any) -> Optional[Callable[[Any], Any]]:
        path = None
        if isinstance(data, TrackedAccess):
            path = getattr(data, "_path", None)
            if self._context_tracker:
                self._context_tracker.last_access = None
        elif self._context_tracker and self._context_tracker.last_access:
            path = self._context_tracker.last_access
            self._context_tracker.last_access = None

        if not path:
            if DBG_GPU:
                logi("[GPU] Resolver inference failed for", type(data).__name__)
            return None

        if DBG_GPU:
            logi("[GPU] Inferred path:", path)
        return lambda ctx: self._context_cache.resolve(ctx, path)

    def _make_setter(
        self,
        resolver: Optional[Callable[[Any], Any]],
        data: Any,
        prop_name: str,
    ) -> Callable[[Any, Any], None]:
        def setter(context: Any, value: Any) -> None:
            target = resolver(context) if resolver else data
            if target is None:
                return
            set_property_value(target, prop_name, value)

        return setter

    def prop(self, data: Any, property: str, *, text: str = "",
             icon: str = "NONE", expand: bool = False, slider: bool = False,
             toggle: int = -1, icon_only: bool = False) -> Optional[LayoutItem]:
        """
        Blender プロパティを適切なウィジェットで表示・編集

        RNA introspection を使用して、プロパティタイプに応じた
        最適なウィジェットを自動選択します。

        Args:
            data: プロパティを持つオブジェクト（例: bpy.context.object）
            property: プロパティ名（例: "location"）
            text: 表示テキスト（空の場合はプロパティ名を使用）
            icon: アイコン名
            expand: Enum を展開表示（RadioGroup）するか
            slider: 数値をスライダー表示するか
            toggle: -1=自動, 0=チェックボックス, 1=トグルボタン
            icon_only: アイコンのみ表示

        Returns:
            作成された LayoutItem（外部から値を取得/設定可能）

        対応プロパティタイプ:
            - Boolean → CheckboxItem / ToggleItem
            - Int/Float → NumberItem / SliderItem
            - Float[3-4] (COLOR) → ColorItem
            - Enum → RadioGroupItem (expand=True) / ラベル表示
            - String → ラベル表示（TextInputItem は未実装）

        使用例:
            # Boolean プロパティ
            layout.prop(C.object, "hide_viewport")

            # 数値プロパティ（スライダー）
            layout.prop(C.scene.render, "resolution_percentage", slider=True)

            # Enum プロパティ（展開）
            layout.prop(C.scene.render, "engine", expand=True)

            # カラープロパティ
            layout.prop(C.object.active_material, "diffuse_color")
        """
        # プロパティ情報を取得
        resolver = self._infer_resolver(data)
        raw_data = self._unwrap_data(data)

        info = get_property_info(raw_data, property) if raw_data is not None else None
        if info is None:
            # プロパティが存在しない場合はフォールバック
            self.prop_display(raw_data, property, text=text, icon=icon)
            return None

        # 表示テキストの決定
        display_text = text if text else info.name

        # 読み取り専用の場合は表示のみ
        if info.is_readonly:
            self.prop_display(raw_data, property, text=display_text, icon=icon)
            return None

        # 現在値を取得
        current_value = get_property_value(raw_data, property)

        # ウィジェットヒントに応じてアイテムを作成
        hint = info.widget_hint

        # スライダー/数値の強制切り替え
        if slider and hint == WidgetHint.NUMBER:
            hint = WidgetHint.SLIDER
        elif not slider and hint == WidgetHint.SLIDER:
            # slider=False は明示的に指定された場合のみ NUMBER に切り替え
            pass  # デフォルトは維持

        # Enum の expand 切り替え
        if expand and hint == WidgetHint.MENU:
            hint = WidgetHint.RADIO

        # トグル/チェックボックスの明示的切り替え
        if toggle == 1 and hint == WidgetHint.CHECKBOX:
            hint = WidgetHint.TOGGLE
        elif toggle == 0 and hint == WidgetHint.TOGGLE:
            hint = WidgetHint.CHECKBOX

        set_value = self._make_setter(resolver, raw_data, property)
        item = self._create_prop_widget(
            raw_data, property, info, hint, display_text, icon,
            current_value, set_value
        )
        if item:
            self._add_item(item)
            meta = {
                "is_dynamic_enum": info.is_dynamic_enum,
                "label_prefix": display_text,
            }
            if resolver:
                binding = PropertyBinding(
                    resolve_data=resolver,
                    set_value=set_value,
                    prop_name=property,
                    widget=item,
                    meta=meta,
                )
                self._bindings.append(binding)
            else:
                def resolve_static(_ctx, data=raw_data):
                    return data
                binding = PropertyBinding(
                    resolve_data=resolve_static,
                    set_value=set_value,
                    prop_name=property,
                    widget=item,
                    meta=meta,
                )
                self._static_bindings.append(binding)

        return item

    def _create_prop_widget(
        self, data: Any, property: str, info: PropertyInfo,
        hint: WidgetHint, text: str, icon: str, value: Any,
        set_value: Callable[[Any, Any], None]
    ) -> Optional[LayoutItem]:
        """
        プロパティ用ウィジェットを作成

        内部メソッド。hint に応じて適切なウィジェットを生成。
        """
        item: Optional[LayoutItem] = None

        # Boolean → Checkbox
        if hint == WidgetHint.CHECKBOX:
            def on_toggle(new_value: bool):
                set_value(bpy.context, new_value)

            item = CheckboxItem(
                text=text,
                value=bool(value),
                on_toggle=on_toggle,
                enabled=self.enabled and self.active
            )

        # Boolean → Toggle
        elif hint == WidgetHint.TOGGLE:
            def on_toggle(new_value: bool):
                set_value(bpy.context, new_value)

            item = ToggleItem(
                text=text,
                icon=icon,
                value=bool(value),
                on_toggle=on_toggle,
                enabled=self.enabled and self.active
            )

        # Number (Int/Float)
        elif hint == WidgetHint.NUMBER:
            def on_change(new_value: float):
                # Int の場合は整数に変換
                if info.prop_type == PropType.INT:
                    new_value = int(new_value)
                set_value(bpy.context, new_value)

            # soft_min/soft_max を使用（より自然な範囲）
            min_val = info.soft_min if info.soft_min is not None else (info.min_value or -1e9)
            max_val = info.soft_max if info.soft_max is not None else (info.max_value or 1e9)

            item = NumberItem(
                value=float(value) if value is not None else 0.0,
                min_val=min_val,
                max_val=max_val,
                step=info.step,
                precision=info.precision if info.prop_type == PropType.FLOAT else 0,
                text=text,
                on_change=on_change,
                enabled=self.enabled and self.active
            )

        # Slider (Int/Float with PERCENTAGE/FACTOR)
        elif hint == WidgetHint.SLIDER:
            def on_change(new_value: float):
                if info.prop_type == PropType.INT:
                    new_value = int(new_value)
                set_value(bpy.context, new_value)

            min_val = info.soft_min if info.soft_min is not None else (info.min_value or 0.0)
            max_val = info.soft_max if info.soft_max is not None else (info.max_value or 1.0)

            # SliderItem には step パラメータがない（位置ベースで値を決定）
            item = SliderItem(
                value=float(value) if value is not None else 0.0,
                min_val=min_val,
                max_val=max_val,
                precision=info.precision if info.prop_type == PropType.FLOAT else 0,
                text=text,
                on_change=on_change,
                enabled=self.enabled and self.active
            )

        # Color (Float array with COLOR subtype)
        elif hint == WidgetHint.COLOR:
            # 4要素に正規化
            if isinstance(value, (list, tuple)):
                if len(value) == 3:
                    color = (*value, 1.0)
                elif len(value) >= 4:
                    color = tuple(value[:4])
                else:
                    color = (1.0, 1.0, 1.0, 1.0)
            else:
                color = (1.0, 1.0, 1.0, 1.0)

            # TODO: on_click でカラーピッカーを開く
            item = ColorItem(
                color=color,
                text=text,
                enabled=self.enabled and self.active
            )

        # Radio (Enum expanded)
        elif hint == WidgetHint.RADIO:
            # 動的 Enum の場合は全アイテムを取得できないため、
            # 現在値のみをラベルとして表示
            if info.is_dynamic_enum:
                # 動的 Enum: 現在値の表示名を取得してラベル表示
                display_name = info.enum_items[0][1] if info.enum_items else str(value)
                item = LabelItem(
                    text=f"{text}: {display_name}",
                    enabled=self.enabled and self.active
                )
            else:
                def on_change(new_value: str):
                    set_value(bpy.context, new_value)

                options = [
                    RadioOption(value=ident, label=name)
                    for ident, name, _ in info.enum_items
                ]

                item = RadioGroupItem(
                    options=options,
                    value=str(value) if value else "",
                    on_change=on_change,
                    enabled=self.enabled and self.active
                )

        # Vector (Numeric array like XYZ)
        elif hint == WidgetHint.VECTOR:
            # TODO: 各要素を NumberItem で表示
            # 現在は読み取り専用表示にフォールバック
            self.prop_display(data, property, text=text, icon=icon)
            return None

        # Text (String) - 未実装
        elif hint == WidgetHint.TEXT:
            # TODO: TextInputItem 実装後に対応
            self.prop_display(data, property, text=text, icon=icon)
            return None

        # Menu (Enum dropdown) - 未実装
        elif hint == WidgetHint.MENU:
            # TODO: MenuButtonItem 実装後に対応
            # 動的 Enum の場合はラベル表示
            if info.is_dynamic_enum:
                display_name = info.enum_items[0][1] if info.enum_items else str(value)
                item = LabelItem(
                    text=f"{text}: {display_name}",
                    enabled=self.enabled and self.active
                )
            # 通常 Enum は RadioGroup にフォールバック
            elif info.enum_items:
                def on_change(new_value: str):
                    set_value(bpy.context, new_value)

                options = [
                    RadioOption(value=ident, label=name)
                    for ident, name, _ in info.enum_items
                ]

                item = RadioGroupItem(
                    options=options,
                    value=str(value) if value else "",
                    on_change=on_change,
                    enabled=self.enabled and self.active
                )
            else:
                self.prop_display(data, property, text=text, icon=icon)
                return None

        # Unsupported
        else:
            self.prop_display(data, property, text=text, icon=icon)
            return None

        return item

    def sync_reactive(self, context, epoch: int) -> bool:
        self._context_cache.begin_tick(epoch)
        any_changed = False
        needs_relayout = False

        for binding in self._bindings:
            try:
                changed, relayout = binding.sync(context)
            except Exception:
                continue
            any_changed |= changed
            needs_relayout = needs_relayout or relayout

        for binding in self._static_bindings:
            try:
                changed, relayout = binding.sync(context)
            except Exception:
                continue
            any_changed |= changed
            needs_relayout = needs_relayout or relayout

        for child in self._children:
            if child.sync_reactive(context, epoch):
                any_changed = True
            if child.dirty:
                needs_relayout = True

        if needs_relayout:
            self.mark_dirty()

        return any_changed

    def sync_props(self) -> None:
        self._epoch += 1
        self.sync_reactive(bpy.context, self._epoch)

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
        return self.width - self.style.scaled_padding_x() * 2

    def _get_spacing(self) -> int:
        """アイテム間のスペースを取得（align=True で 0）"""
        return 0 if self._align else self.style.scaled_spacing()

    def _add_item(self, item: LayoutItem) -> None:
        """アイテムを追加"""
        self._dirty = True  # アイテム追加でレイアウト再計算が必要
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

        self._register_interactive_item(item)
        self._elements.append(item)  # Phase 1: _elements に統合

    def calc_height(self) -> float:
        """
        合計高さを計算

        Note:
            Phase 1 では estimate() で self.height が計算されるため、
            layout() 実行後はそちらの値が使用される。
            このメソッドは estimate() 前の互換性のために残置。
        """
        # P1-5 修正: estimate() 実行後かつ dirty でなければ計算済みの height を返す
        # dirty=True の場合は再計算が必要（アイテム追加・変更後）
        if self.height > 0 and not self._dirty:
            return self.height

        if not self._elements:
            return self.style.scaled_padding_y() * 2

        spacing = self._get_spacing()
        if self.direction == Direction.VERTICAL:
            height = self.style.scaled_padding_y() * 2
            n_elements = 0
            for element in self._elements:
                if isinstance(element, GPULayout):
                    height += element.calc_height()
                else:
                    _, h = element.calc_size(self.style)
                    height += h * self.scale_y
                n_elements += 1
            # スペーシング
            if n_elements > 1:
                height += spacing * (n_elements - 1)
            return height
        else:
            # 水平レイアウト - 最大の高さ
            max_height = 0
            for element in self._elements:
                if isinstance(element, GPULayout):
                    max_height = max(max_height, element.calc_height())
                else:
                    _, h = element.calc_size(self.style)
                    max_height = max(max_height, h * self.scale_y)
            return max_height + self.style.scaled_padding_y() * 2

    def calc_width(self) -> float:
        """
        合計幅を計算

        Note:
            Phase 1 では estimate() で self.width が計算される。
            このメソッドは水平レイアウトの自然幅計算に使用。
        """
        if not self._elements:
            return self.width

        spacing = self._get_spacing()
        if self.direction == Direction.HORIZONTAL:
            width = self.style.scaled_padding_x() * 2
            n_elements = 0
            for element in self._elements:
                if isinstance(element, GPULayout):
                    width += element.calc_width()
                else:
                    w, _ = element.calc_size(self.style)
                    width += w * self.scale_x
                n_elements += 1
            # スペーシング
            if n_elements > 1:
                width += spacing * (n_elements - 1)
            return width
        else:
            return self.width

    # ─────────────────────────────────────────────────────────────────────────
    # タイトルバー設定
    # ─────────────────────────────────────────────────────────────────────────

    def set_title_bar(self, title: str = "", show_close: bool = True,
                      on_close: Optional[Callable[[], None]] = None) -> None:
        """
        タイトルバーを有効化

        Args:
            title: タイトル文字列
            show_close: クローズボタンを表示するか
            on_close: クローズボタンのコールバック
        """
        self._show_title_bar = True
        self._title = title
        self._show_close_button = show_close
        self._on_close = on_close

    def set_panel_config(self, uid: str = None,
                         resizable: bool = False,
                         min_width: float = MIN_PANEL_WIDTH) -> None:
        """
        パネルのリサイズと永続化を設定

        Args:
            uid: 永続化用の一意識別子（pm.uid）
            resizable: 右下コーナーでリサイズ可能にする
            min_width: 最小幅の制約

        Note:
            重複起動防止は GPUPanelManager が担当します。
            このメソッドは位置・サイズの永続化とリサイズ機能のみを設定します。
        """
        self._panel_uid = uid
        self._show_resize_handle = resizable
        self._min_width = min_width

        if uid:
            self._restore_panel_state()

    def _restore_panel_state(self) -> None:
        """window_manager から位置・サイズを復元"""
        if not self._panel_uid:
            return
        try:
            wm = bpy.context.window_manager
            states = wm.get('_gpu_layout_states', {})
            if self._panel_uid in states:
                state = states[self._panel_uid]
                self.x = state.get('x', self.x)
                self.y = state.get('y', self.y)
                self.width = max(state.get('width', self.width), self._min_width)
                self.mark_dirty()
        except Exception:
            pass

    def _save_panel_state(self) -> None:
        """window_manager に位置・サイズを保存"""
        if not self._panel_uid:
            return
        try:
            wm = bpy.context.window_manager
            states = wm.get('_gpu_layout_states', None)
            if states is None:
                states = {}
                wm['_gpu_layout_states'] = states
            states[self._panel_uid] = {
                'x': self.x,
                'y': self.y,
                'width': self.width,
            }
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # 境界クランプ
    # ─────────────────────────────────────────────────────────────────────────

    def set_region_bounds(self, width: float, height: float) -> None:
        """
        境界クランプ用のリージョンサイズを設定

        Args:
            width: リージョンの幅
            height: リージョンの高さ

        Note:
            この設定後、パネルは自動的にリージョン内にクランプされます。
            - タイトルバーは常にリージョン内に表示
            - ドラッグ終了時に位置を補正
            - リージョンリサイズ時も位置を維持
        """
        old_width = self._region_width
        old_height = self._region_height

        self._region_width = width
        self._region_height = height

        # リージョンサイズが変わった場合はクランプを実行
        if old_width != width or old_height != height:
            self._clamp_position()

    def _clamp_position(self) -> None:
        """
        パネル位置をリージョン境界内にクランプ

        タイトルバー全体（閉じるボタン含む）が常に見えるように位置を調整します。
        コンテンツ部分は下側にはみ出すことを許容します。

        座標系:
            - Blender は左下原点、Y 上向き
            - self.y はコンテンツ領域の上端
            - title_bar_y = self.y + title_bar_height（タイトルバー上端）
        """
        if self._region_width is None or self._region_height is None:
            return

        margin = int(self.style.ui_scale(CLAMP_MARGIN))
        title_bar_height = self._get_title_bar_height() if self._show_title_bar else 0

        # X 座標のクランプ（タイトルバー全体が見える範囲）
        # 左端: パネル左端がマージン以上
        min_x = margin
        # 右端: パネル右端がリージョン幅 - マージン以下
        max_x = self._region_width - margin - self.width

        # パネル幅がリージョン幅より大きい場合は左寄せ
        if max_x < min_x:
            max_x = min_x

        # Y 座標のクランプ（タイトルバー基準）
        # 下端: タイトルバー上端がマージン以上（title_bar_y >= margin）
        min_y = margin - title_bar_height if self._show_title_bar else margin
        # 上端: タイトルバー上端がリージョン高さ - マージン以下
        max_y = self._region_height - margin - title_bar_height if self._show_title_bar else self._region_height - margin

        # クランプを適用
        clamped = False
        old_x, old_y = self.x, self.y

        self.x = max(min_x, min(self.x, max_x))
        self.y = max(min_y, min(self.y, max_y))

        if self.x != old_x or self.y != old_y:
            clamped = True

        if clamped:
            self._save_panel_state()
            self.mark_dirty()

    def _get_title_bar_height(self) -> int:
        """スケーリングされたタイトルバーの高さを取得"""
        return self.style.scaled_title_bar_height()

    def _get_close_button_size(self) -> int:
        """スケーリングされたクローズボタンのサイズを取得"""
        return int(self.style.ui_scale(16))

    def _get_title_bar_y(self) -> float:
        """タイトルバーの Y 座標（上端）を取得"""
        return self.y + self._get_title_bar_height()

    def _get_content_y(self) -> float:
        """コンテンツ領域の Y 座標（上端）を取得"""
        if self._show_title_bar:
            return self.y  # タイトルバーの下
        return self.y

    def contains_point(self, x: float, y: float) -> bool:
        """
        指定した点がパネル境界内（タイトルバー含む）にあるかどうか

        Args:
            x: X 座標（リージョン座標系）
            y: Y 座標（リージョン座標系）

        Returns:
            境界内なら True

        Note:
            リサイズハンドルやドロップシャドウ領域は含みません。
            タイトルバーがある場合はタイトルバーも含みます。
        """
        # 上端: タイトルバーがあればその上端、なければコンテンツ上端
        if self._show_title_bar:
            top_y = self._get_title_bar_y()
            total_height = self.calc_height() + self._get_title_bar_height()
        else:
            top_y = self.y
            total_height = self.calc_height()

        # 下端
        bottom_y = top_y - total_height

        # 境界判定
        return (self.x <= x <= self.x + self.width and
                bottom_y <= y <= top_y)

    def _register_title_bar(self) -> None:
        """タイトルバーの HitRect を登録"""
        if not self._show_title_bar:
            return

        manager = self._ensure_hit_manager()
        title_bar_y = self._get_title_bar_y()
        title_bar_height = self._get_title_bar_height()

        # クローズボタン領域を除いたタイトルバー
        close_btn_size = self._get_close_button_size()
        close_btn_margin = int(self.style.ui_scale(6))

        if self._show_close_button:
            if IS_MAC:
                # Mac: 左側にクローズボタン
                drag_x = self.x + close_btn_size + close_btn_margin * 2
                drag_width = self.width - close_btn_size - close_btn_margin * 2
            else:
                # Windows/Linux: 右側にクローズボタン
                drag_x = self.x
                drag_width = self.width - close_btn_size - close_btn_margin * 2
        else:
            drag_x = self.x
            drag_width = self.width

        # タイトルバーのドラッグ領域
        if self._title_bar_rect is None:
            def on_drag(dx: float, dy: float, abs_x: float, abs_y: float):
                self.x += dx
                self.y += dy
                self._save_panel_state()
                self.mark_dirty()

            def on_drag_end(inside: bool):
                # ドラッグ終了時に境界内にクランプ
                self._clamp_position()

            self._title_bar_rect = HitRect(
                x=drag_x,
                y=title_bar_y,
                width=drag_width,
                height=title_bar_height,
                tag="title_bar",
                draggable=True,
                on_drag=on_drag,
                on_release=on_drag_end,
                z_index=100  # 他の要素より優先
            )
            manager.register(self._title_bar_rect)
        else:
            # 位置とサイズを更新
            self._title_bar_rect.x = drag_x
            self._title_bar_rect.y = title_bar_y
            self._title_bar_rect.width = drag_width
            self._title_bar_rect.height = title_bar_height

        # クローズボタン
        if self._show_close_button and self._close_button_rect is None:
            if IS_MAC:
                close_x = self.x + close_btn_margin
            else:
                close_x = self.x + self.width - close_btn_size - close_btn_margin

            close_y = title_bar_y - (title_bar_height - close_btn_size) / 2

            def on_close_hover_enter():
                self._close_button_hovered = True

            def on_close_hover_leave():
                self._close_button_hovered = False

            def on_close_click():
                if self._on_close:
                    self._on_close()

            self._close_button_rect = HitRect(
                x=close_x,
                y=close_y,
                width=close_btn_size,
                height=close_btn_size,
                tag="close_button",
                on_hover_enter=on_close_hover_enter,
                on_hover_leave=on_close_hover_leave,
                on_click=on_close_click,
                z_index=101  # タイトルバーより優先
            )
            manager.register(self._close_button_rect)
        elif self._close_button_rect is not None:
            # 位置とサイズを更新
            if IS_MAC:
                self._close_button_rect.x = self.x + close_btn_margin
            else:
                self._close_button_rect.x = self.x + self.width - close_btn_size - close_btn_margin
            self._close_button_rect.y = title_bar_y - (title_bar_height - close_btn_size) / 2
            self._close_button_rect.width = close_btn_size
            self._close_button_rect.height = close_btn_size

    def _register_resize_handle(self) -> None:
        """リサイズハンドルの HitRect を右下コーナーに登録"""
        if not self._show_resize_handle:
            return

        manager = self._ensure_hit_manager()
        content_height = self.calc_height()
        handle_size = int(self.style.ui_scale(RESIZE_HANDLE_SIZE))

        # タイトルバーを含む全体高さを計算
        if self._show_title_bar:
            base_y = self._get_title_bar_y()
            total_height = content_height + self._get_title_bar_height()
        else:
            base_y = self.y
            total_height = content_height

        # 右下コーナーの位置（アウトライン内に収めるためマージンを追加）
        margin = 4
        handle_x = self.x + self.width - handle_size - margin
        handle_y = base_y - total_height + handle_size + margin

        if self._resize_handle_rect is None:
            def on_resize_drag(dx: float, dy: float, abs_x: float, abs_y: float):
                new_width = self.width + dx
                self.width = max(new_width, self._min_width)
                self._save_panel_state()
                self.mark_dirty()

            def on_hover_enter():
                self._resize_handle_hovered = True

            def on_hover_leave():
                self._resize_handle_hovered = False

            self._resize_handle_rect = HitRect(
                x=handle_x,
                y=handle_y,
                width=handle_size,
                height=handle_size,
                tag="resize_handle",
                draggable=True,
                on_drag=on_resize_drag,
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                z_index=102  # タイトルバー(100)、クローズボタン(101)より上
            )
            manager.register(self._resize_handle_rect)
        else:
            # 位置更新
            self._resize_handle_rect.x = handle_x
            self._resize_handle_rect.y = handle_y
            self._resize_handle_rect.width = handle_size
            self._resize_handle_rect.height = handle_size

    # ─────────────────────────────────────────────────────────────────────────
    # 2-pass レイアウトアルゴリズム（Phase 1）
    # ─────────────────────────────────────────────────────────────────────────

    def estimate(self, constraints: BoxConstraints) -> Size:
        """
        Pass 1: サイズを推定（子から親へ積み上げ）

        Args:
            constraints: 親から渡されるサイズ制約

        Returns:
            このレイアウトの推定サイズ

        Note:
            この段階では位置（x, y）は確定しません。
            サイズのみを計算し、self.width / self.height に保存します。
        """
        if self.direction == Direction.VERTICAL:
            return self._estimate_vertical(constraints)
        else:
            return self._estimate_horizontal(constraints)

    def _estimate_vertical(self, constraints: BoxConstraints) -> Size:
        """
        垂直レイアウトのサイズ推定（v3 準拠）

        Changes (P1-3):
            - scale_y を estimate で適用しない（resolve で適用）
            - 自然サイズを estimated_* に保存
        """
        spacing = self._get_spacing()
        padding_x = self.style.scaled_padding_x()
        padding_y = self.style.scaled_padding_y()

        # パディングを差し引いた内部制約
        inner_constraints = constraints.deflate(padding_x * 2, padding_y * 2)

        total_height = padding_y * 2
        max_width = 0.0
        n_elements = 0

        for element in self._elements:
            if isinstance(element, GPULayout):
                # 子レイアウトは再帰的に estimate
                child_constraints = BoxConstraints(
                    min_width=inner_constraints.min_width,
                    max_width=inner_constraints.max_width,
                    min_height=0,
                    max_height=float('inf')
                )
                size = element.estimate(child_constraints)
                element.estimated_width = size.width
                element.estimated_height = size.height
            else:
                # LayoutItem は calc_size で自然サイズを取得
                w, h = element.calc_size(self.style)
                element.estimated_width = w
                element.estimated_height = h

            max_width = max(max_width, element.estimated_width)
            # P1-3: scale_y は estimate で適用しない（resolve で適用）
            total_height += element.estimated_height
            n_elements += 1

        # スペーシングを加算
        if n_elements > 1:
            total_height += spacing * (n_elements - 1)

        # 自身の推定サイズを記録
        self.estimated_width = max_width + padding_x * 2
        self.estimated_height = total_height

        # 制約に従ってクランプ
        self.width = constraints.clamp_width(self.estimated_width)
        self.height = constraints.clamp_height(self.estimated_height)

        return Size(self.width, self.height)

    def _estimate_horizontal(self, constraints: BoxConstraints) -> Size:
        """
        水平レイアウトのサイズ推定（v3 準拠）

        各子の自然サイズを取得し、estimated_width/height に保存。
        resolve フェーズで _distribute_width() を使って実際の幅を配分。

        Changes (P1-1, P1-3, P1-4):
            - 均等分配 → 自然幅を取得して estimated_width に保存
            - scale_y の適用を削除（resolve で適用）
            - constraints.clamp_height() を適用
        """
        n = len(self._elements)
        if n == 0:
            self.width = constraints.clamp_width(self.style.scaled_padding_x() * 2)
            self.height = constraints.clamp_height(self.style.scaled_padding_y() * 2)
            self.estimated_width = self.width
            self.estimated_height = self.height
            return Size(self.width, self.height)

        spacing = self._get_spacing()
        padding_x = self.style.scaled_padding_x()
        padding_y = self.style.scaled_padding_y()

        # 利用可能な幅を計算（制約の max_width を使用）
        # 負の幅を防ぐため max(0, ...) でクランプ
        available_width = constraints.max_width - padding_x * 2
        if available_width == float('inf'):
            # 制約がない場合は現在の width を使用
            available_width = self.width - padding_x * 2
        available_width = max(0, available_width)

        total_estimated_width = 0.0
        max_height = 0.0
        self._measured_widths = []

        for element in self._elements:
            if isinstance(element, GPULayout):
                # 子レイアウトは loose constraints で estimate（自然サイズを取得）
                child_constraints = BoxConstraints(
                    min_width=0,
                    max_width=max(0, available_width),  # 最大幅は親から継承、負にならないようクランプ
                    min_height=0,
                    max_height=float('inf')
                )
                size = element.estimate(child_constraints)
                element.estimated_width = size.width
                element.estimated_height = size.height
            else:
                # LayoutItem は calc_size で自然サイズを取得
                w, h = element.calc_size(self.style)
                element.estimated_width = w
                element.estimated_height = h

            total_estimated_width += element.estimated_width
            # P1-3: scale_y は estimate で適用しない（resolve で適用）
            max_height = max(max_height, element.estimated_height)

        # 自身の推定サイズを記録
        total_spacing = spacing * (n - 1)
        self.estimated_width = total_estimated_width + total_spacing + padding_x * 2
        self.estimated_height = max_height + padding_y * 2

        # 制約でクランプ（P1-4 修正: height も制約でクランプ）
        self.width = constraints.clamp_width(available_width + padding_x * 2)
        self.height = constraints.clamp_height(self.estimated_height)

        return Size(self.width, self.height)

    def _distribute_width(
        self,
        elements: list,
        available_width: float,
        gap: float,
    ) -> tuple[list[float], float]:
        """
        Row の幅配分（v3 / Blender UILayout 準拠）

        Args:
            elements: 配分対象の要素リスト（LayoutItem または GPULayout）
            available_width: 利用可能な幅（ギャップ含む）
            gap: 要素間のギャップ

        Returns:
            (各要素に割り当てる幅のリスト, 実際のギャップ)

        Note:
            - 縮小が必要な場合: 比例縮小、ギャップは固定
            - EXPAND:
              - expand_width=True の要素: 比例拡大
              - expand_width=False の要素 (ラベル等): 自然幅を維持
              - 余白は間隔に均等分配
            - LEFT/CENTER/RIGHT: 元サイズ維持、ギャップは固定
        """
        n = len(elements)
        if n == 0:
            return [], gap

        gaps_total = gap * (n - 1)
        # 負の幅を防ぐため max(0, ...) でクランプ
        available = max(0, available_width - gaps_total)
        total_estimated = sum(e.estimated_width for e in elements)

        if total_estimated == 0:
            # フォールバック: 均等分配（available が 0 の場合も安全）
            if available > 0 and n > 0:
                return [available / n] * n, gap
            return [0] * n, gap

        result = []
        actual_gap = gap

        if total_estimated > available:
            # 比例縮小（コンテンツがはみ出す）
            for element in elements:
                width = (element.estimated_width * available) / total_estimated
                result.append(width)
        elif self.alignment == Alignment.EXPAND:
            # EXPAND: 要素タイプに応じて幅を決定
            # - expand_width=True (ボタン等): 比例拡大
            # - expand_width=False (ラベル等): 自然幅を維持、余白は間隔に分配

            # 拡張可能な要素と固定幅要素を分離
            expandable_width = sum(
                e.estimated_width for e in elements
                if getattr(e, 'expand_width', True)
            )
            fixed_width = sum(
                e.estimated_width for e in elements
                if not getattr(e, 'expand_width', True)
            )

            # 拡張可能な要素に分配する幅
            expand_available = available - fixed_width

            if expandable_width > 0 and expand_available > 0:
                # 拡張可能な要素がある場合: 比例拡大
                for element in elements:
                    if getattr(element, 'expand_width', True):
                        width = (element.estimated_width * expand_available) / expandable_width
                    else:
                        width = element.estimated_width
                    result.append(width)
            else:
                # 全て固定幅要素の場合: 間隔を均等分配
                extra_space = available - total_estimated
                if n > 1 and extra_space > 0:
                    actual_gap = gap + extra_space / (n - 1)
                for element in elements:
                    result.append(element.estimated_width)
        else:
            # LEFT/CENTER/RIGHT: 元サイズ維持
            for element in elements:
                result.append(element.estimated_width)

        return result, actual_gap

    def _distribute_split_widths(
        self,
        n: int,
        available_width: float,
        gap: float
    ) -> list[float]:
        """
        Split レイアウト専用の幅配分（v3 アルゴリズム）

        Args:
            n: 列の総数（resolve 時点で確定）
            available_width: 利用可能な幅
            gap: 列間のギャップ

        Returns:
            各列に割り当てる幅のリスト

        Note:
            factor > 0 の場合:
            - 最初の列: factor 割合
            - 2番目以降: 残り幅を (n-1) で均等分割
            例: factor=0.25 で 3列 → 25% : 37.5% : 37.5%

            factor == 0 の場合:
            - 全列を均等分割
        """
        if n == 0:
            return []

        gaps_total = gap * (n - 1)
        content_width = max(0, available_width - gaps_total)

        if self._split_factor > 0:
            # factor が指定されている場合
            first_width = content_width * self._split_factor
            remaining_width = content_width - first_width

            if n == 1:
                # 1列のみ: factor 無視で全幅
                return [content_width]
            else:
                # 2列以上: 最初は factor、残りを均等分割
                other_width = remaining_width / (n - 1)
                return [first_width] + [other_width] * (n - 1)
        else:
            # factor == 0: 全列均等分割
            if n > 0:
                equal_width = content_width / n
                return [equal_width] * n
            return []

    def resolve(self, x: float, y: float) -> None:
        """
        Pass 2: 位置を確定（親から子へ伝播）

        Args:
            x: このレイアウトの左上 X 座標
            y: このレイアウトの左上 Y 座標

        Note:
            estimate() で計算されたサイズを基に、
            各要素の最終的な位置を確定します。
        """
        self.x = x
        self.y = y

        if self.direction == Direction.VERTICAL:
            self._resolve_vertical()
        else:
            self._resolve_horizontal()

    def _resolve_vertical(self) -> None:
        """
        垂直レイアウトの位置確定（v3 準拠）

        Changes (P1-2, P1-3):
            - scale_x/y を estimated_* に適用してから配置
            - 重複する scale_y 適用を削除
        """
        spacing = self._get_spacing()
        padding_x = self.style.scaled_padding_x()
        padding_y = self.style.scaled_padding_y()
        # 負の幅を防ぐため max(0, ...) でクランプ
        available_width = max(0, self.width - padding_x * 2)

        cursor_x = self.x + padding_x
        cursor_y = self.y - padding_y

        n = len(self._elements)
        if n == 0:
            return

        # v3: scale_x/y を estimated_* に適用（配置前）
        for element in self._elements:
            element.estimated_width *= self.scale_x
            element.estimated_height *= self.scale_y

        for i, element in enumerate(self._elements):
            if isinstance(element, GPULayout):
                # 子レイアウトは親の幅に合わせる
                element.width = available_width
                element.resolve(cursor_x, cursor_y)
                cursor_y -= element.height + spacing
            else:
                # LayoutItem の配置
                # alignment に応じて幅と位置を計算
                if self.alignment == Alignment.EXPAND:
                    # EXPAND: 利用可能幅全体を使用（scale_x は既に estimated_* に適用済み）
                    element.width = available_width
                    element.x = cursor_x
                else:
                    # 自然サイズを維持（scale_x 適用済みの estimated_width を使用）
                    element.width = element.estimated_width
                    if self.alignment == Alignment.CENTER:
                        element.x = cursor_x + (available_width - element.width) / 2
                    elif self.alignment == Alignment.RIGHT:
                        element.x = cursor_x + available_width - element.width
                    else:  # LEFT
                        element.x = cursor_x

                element.y = cursor_y
                # P1-3: scale_y 適用済みの estimated_height を使用（二重適用を防ぐ）
                element.height = element.estimated_height

                # LabelItem に alignment を継承
                if hasattr(element, 'alignment'):
                    element.alignment = self.alignment

                # Phase 2: corners 計算（縦方向）
                if hasattr(element, 'corners'):
                    if self._align:
                        # align=True: 隣接ボタンの境界で角丸を無効化
                        is_first = (i == 0)
                        is_last = (i == n - 1)
                        # corners: (bottomLeft, topLeft, topRight, bottomRight)
                        # 最上: 上側のみ角丸、最下: 下側のみ角丸
                        element.corners = (is_last, is_first, is_first, is_last)
                    else:
                        # align=False: デフォルト（全角丸）にリセット
                        element.corners = (True, True, True, True)

                cursor_y -= element.height + spacing

    def _resolve_horizontal(self) -> None:
        """
        水平レイアウトの位置確定（v3 準拠）

        Changes (P1-2, P1-3):
            - _distribute_width() を使用して幅を配分
            - scale_x/y を estimated_* に適用してから配分
            - 重複する scale_y 適用を削除
            - split レイアウトは専用の配分ロジックを使用
        """
        spacing = self._get_spacing()
        padding_x = self.style.scaled_padding_x()
        padding_y = self.style.scaled_padding_y()

        n = len(self._elements)
        if n == 0:
            return

        cursor_y = self.y - padding_y
        available_width = max(0, self.width - padding_x * 2)

        # v3: scale_x/y を estimated_* に適用（幅配分前）
        for element in self._elements:
            element.estimated_width *= self.scale_x
            element.estimated_height *= self.scale_y

        # Split レイアウトの場合は専用の配分ロジック
        if self._is_split and n > 0:
            widths = self._distribute_split_widths(n, available_width, spacing)
            actual_spacing = spacing
        else:
            # v3 アルゴリズムで幅配分（EXPAND 時は間隔も調整される）
            widths, actual_spacing = self._distribute_width(self._elements, available_width, spacing)

        # alignment による開始位置計算
        total_content_width = sum(widths) + actual_spacing * max(0, n - 1)
        min_cursor_x = self.x + padding_x

        if self.alignment == Alignment.CENTER:
            cursor_x = self.x + padding_x + (available_width - total_content_width) / 2
            cursor_x = max(cursor_x, min_cursor_x)  # 左外へのはみ出しを防止
        elif self.alignment == Alignment.RIGHT:
            cursor_x = self.x + padding_x + available_width - total_content_width
            cursor_x = max(cursor_x, min_cursor_x)  # 左外へのはみ出しを防止
        else:  # LEFT or EXPAND
            cursor_x = min_cursor_x

        # 各要素の配置
        for i, element in enumerate(self._elements):
            width = widths[i] if i < len(widths) else 0

            if isinstance(element, GPULayout):
                element.width = width
                element.resolve(cursor_x, cursor_y)
            else:
                element.x = cursor_x
                element.y = cursor_y
                element.width = width
                # P1-3: scale_y 適用済みの estimated_height を使用（二重適用を防ぐ）
                element.height = element.estimated_height

                # Phase 2: corners 計算（水平方向）
                if hasattr(element, 'corners'):
                    if self._align:
                        # align=True: 隣接ボタンの境界で角丸を無効化
                        is_first = (i == 0)
                        is_last = (i == n - 1)
                        # corners: (bottomLeft, topLeft, topRight, bottomRight)
                        # 左端のみ左側角丸、右端のみ右側角丸
                        element.corners = (is_first, is_first, is_last, is_last)
                    else:
                        # align=False: デフォルト（全角丸）にリセット
                        element.corners = (True, True, True, True)

            cursor_x += width + actual_spacing

    # ─────────────────────────────────────────────────────────────────────────
    # レイアウト計算（レガシー互換 + 新アルゴリズム統合）
    # ─────────────────────────────────────────────────────────────────────────

    def layout(self, *, force: bool = False, constraints: Optional[BoxConstraints] = None) -> None:
        """
        レイアウトを計算（2-pass: estimate → resolve）

        Args:
            force: True の場合、Dirty Flag に関係なく再計算
            constraints: サイズ制約（None の場合は現在の width から生成）

        Note:
            Phase 1 で導入された 2-pass アルゴリズム:
            1. estimate(): 子から親へサイズを積み上げ
            2. resolve(): 親から子へ位置を確定
        """
        if not self._dirty and not force:
            return  # 変更がなければスキップ

        # 制約が指定されていない場合は、現在の幅から制約を生成
        if constraints is None:
            constraints = BoxConstraints.tight_width(self.width)

        # Pass 1: サイズ推定
        self.estimate(constraints)

        # Pass 2: 位置確定
        self.resolve(self.x, self.y)

        # タイトルバーの HitRect を登録
        self._register_title_bar()
        self._register_resize_handle()

        # HitRect の位置を更新
        if self._hit_manager:
            self._hit_manager.update_positions(self.style)

        self._dirty = False  # レイアウト完了

    def _relayout_items(self) -> None:
        """
        アイテムの位置を再計算（Deprecated）

        Warning:
            Phase 1 で resolve() に機能が統合されたため、
            このメソッドは layout() から呼び出されなくなりました。
            外部から呼び出している箇所がある場合のために残置していますが、
            将来のバージョンで削除される可能性があります。
        """
        cursor_x = self.x + self.style.scaled_padding_x()
        cursor_y = self.y - self.style.scaled_padding_y()
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
        """
        GPU 描画を実行

        Note:
            この関数は描画のみを行います。レイアウト計算が必要な場合は
            事前に layout() を呼び出すか、update_and_draw() を使用してください。
        """
        content_height = self.calc_height()
        total_height = content_height
        if self._show_title_bar:
            total_height += self._get_title_bar_height()

        # 描画の基準 Y 座標
        draw_y = self._get_title_bar_y() if self._show_title_bar else self.y

        # スケーリングされた値を取得
        border_radius = self.style.scaled_border_radius()

        # パネルシャドウ描画（背景の前に描画、3辺: 左、下、右）
        if self.style.shadow_enabled and self._draw_background:
            GPUDrawing.draw_panel_shadow(
                self.x, draw_y, self.width, total_height,
                border_radius,
                self.style.scaled_shadow_width(),
                self.style.shadow_alpha
            )

        # 背景描画（タイトルバー含む）
        if self._draw_background:
            GPUDrawing.draw_rounded_rect(
                self.x, draw_y, self.width, total_height,
                border_radius, self.style.bg_color
            )

        # アウトライン描画
        if self._draw_outline:
            GPUDrawing.draw_rounded_rect_outline(
                self.x, draw_y, self.width, total_height,
                border_radius, self.style.outline_color
            )

        # タイトルバー描画
        if self._show_title_bar:
            self._draw_title_bar()

        # リサイズハンドル描画
        self._draw_resize_handle()

        # 要素描画（追加順序を保持）
        # Phase 1: _elements を使用して item と child を正しい順序で描画
        for element in self._elements:
            if isinstance(element, GPULayout):
                # 子レイアウト
                element.draw()
            else:
                # LayoutItem
                if self._hit_manager and isinstance(element, (ButtonItem, ToggleItem, SliderItem, NumberItem, CheckboxItem, ColorItem)):
                    # インタラクティブなアイテムには状態を渡す
                    item_id = str(id(element))
                    state = self._hit_manager.get_render_state(item_id, element.enabled)
                    element.draw(self.style, state)
                else:
                    element.draw(self.style)

    def update_and_draw(self) -> None:
        """
        レイアウト計算と描画を一度に実行

        便利メソッド。layout() + draw() と同等。
        """
        self.layout()
        self.draw()

    def _draw_title_bar(self) -> None:
        """タイトルバーを描画"""
        title_bar_y = self._get_title_bar_y()
        title_bar_height = self._get_title_bar_height()
        close_btn_size = self._get_close_button_size()
        close_btn_margin = int(self.style.ui_scale(6))
        border_radius = self.style.scaled_border_radius()

        # タイトルバー背景（少し暗め）
        title_bg = tuple(c * 0.8 for c in self.style.bg_color[:3]) + (self.style.bg_color[3],)
        # corners: (bottomLeft, topLeft, topRight, bottomRight)
        # タイトルバーは上の角だけ丸める
        GPUDrawing.draw_rounded_rect(
            self.x, title_bar_y, self.width, title_bar_height,
            border_radius, title_bg,
            corners=(False, True, True, False)
        )

        # タイトルバーのアウトライン（上と左右、パネルアウトラインと同じ太さ）
        # タイトルバー背景がパネルのアウトラインを上書きするため再描画
        GPUDrawing.draw_rounded_rect_outline(
            self.x, title_bar_y, self.width, title_bar_height,
            border_radius, self.style.outline_color,
            corners=(False, True, True, False)
        )

        # タイトルバー下部の境界線（パネルアウトラインと同じ太さ）
        line_y = title_bar_y - title_bar_height
        line_width = self.style.line_width()
        # 矩形として描画（ストローク方式のアウトラインと見た目を統一）
        GPUDrawing.draw_rect(
            self.x + 1, line_y + line_width / 2,
            self.width - 2, line_width,
            self.style.outline_color
        )

        # タイトルテキスト
        if self._title:
            text_x = self.x + self.style.scaled_padding_x()
            if IS_MAC and self._show_close_button:
                text_x = self.x + close_btn_size + close_btn_margin * 2 + int(self.style.ui_scale(4))
            text_y = title_bar_y - title_bar_height / 2 - int(self.style.ui_scale(4))
            text_size = self.style.scaled_text_size()

            # 利用可能なテキスト幅を計算（パディングとクローズボタンを考慮）
            padding_x = self.style.scaled_padding_x()
            if self._show_close_button:
                available_width = self.width - close_btn_size - close_btn_margin * 2 - padding_x * 2
            else:
                available_width = self.width - padding_x * 2

            # テキストが利用可能幅を超える場合は省略記号を追加
            display_title = BLFDrawing.get_text_with_ellipsis(self._title, available_width, text_size)

            # クリップ矩形を計算（タイトルバー領域内）
            clip_rect = BLFDrawing.calc_clip_rect(
                self.x + padding_x, title_bar_y,
                self.width - padding_x * 2, title_bar_height
            )

            BLFDrawing.draw_text_clipped(
                text_x, text_y, display_title,
                self.style.text_color, text_size, clip_rect
            )

        # クローズボタン
        if self._show_close_button:
            if IS_MAC:
                btn_x = self.x + close_btn_margin + close_btn_size / 2
            else:
                btn_x = self.x + self.width - close_btn_margin - close_btn_size / 2
            btn_y = title_bar_y - title_bar_height / 2

            # ホバー時は明るく
            if self._close_button_hovered:
                btn_color = (0.9, 0.3, 0.3, 1.0)  # 明るい赤
            else:
                btn_color = (0.7, 0.25, 0.25, 1.0)  # 暗めの赤

            GPUDrawing.draw_circle(btn_x, btn_y, close_btn_size / 2, btn_color)

    def _draw_resize_handle(self) -> None:
        """リサイズグリップハンドルを右下コーナーに描画"""
        if not self._show_resize_handle:
            return

        content_height = self.calc_height()
        handle_size = int(self.style.ui_scale(RESIZE_HANDLE_SIZE))

        if self._show_title_bar:
            base_y = self._get_title_bar_y()
            total_height = content_height + self._get_title_bar_height()
        else:
            base_y = self.y
            total_height = content_height

        # 右下コーナー（アウトライン内に収めるためマージンを追加）
        margin = 4
        handle_x = self.x + self.width - handle_size - margin
        handle_y = base_y - total_height + handle_size + margin

        # テーマカラーから派生（通常: 暗め、ホバー: 明るめ）
        if self._resize_handle_hovered:
            # ホバー時: text_color_secondary
            line_color = self.style.text_color_secondary
        else:
            # 通常時: text_color_secondary を暗く
            base = self.style.text_color_secondary
            line_color = (base[0] * 0.6, base[1] * 0.6, base[2] * 0.6, base[3])
        line_width = 0.8  # 細め

        # 3本の斜め線（右下から左上への対角線パターン）
        for i, factor in enumerate([0.3, 0.55, 0.8]):
            offset = int(handle_size * factor)
            GPUDrawing.draw_rounded_line(
                handle_x + handle_size - offset, handle_y - handle_size,
                handle_x + handle_size, handle_y - handle_size + offset,
                line_color, line_width
            )

    # ─────────────────────────────────────────────────────────────────────────
    # イベント処理
    # ─────────────────────────────────────────────────────────────────────────

    def handle_event(self, event: Event, region=None) -> bool:
        """
        イベントを処理

        Args:
            event: Blender イベント
            region: Blender region（オプション）

        Returns:
            イベントを消費したかどうか
        """
        self.layout()
        return self._handle_event(event, region)

    def _handle_event(self, event: Event, region=None) -> bool:
        # 子レイアウトを先に処理
        for child in self._children:
            if child._handle_event(event, region):
                return True

        if self._hit_manager:
            return self._hit_manager.handle_event(event, region)

        # region 座標からマウス位置を取得
        # Note: 呼び出し側で region.x, region.y を引く必要がある場合あり
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

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

    def _ensure_hit_manager(self) -> HitTestManager:
        if self._hit_manager is None:
            self._hit_manager = HitTestManager()
        return self._hit_manager

    def _register_interactive_item(self, item: LayoutItem) -> None:
        if not isinstance(item, (ButtonItem, ToggleItem, SliderItem, NumberItem, CheckboxItem, ColorItem, RadioGroupItem)):
            return

        manager = self._ensure_hit_manager()

        if isinstance(item, ColorItem):
            # カラースウォッチ: カラーバー部分のみをヒット領域に設定
            bar_x, bar_y, bar_width, bar_height = item.get_bar_rect(self.style)

            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_click():
                item.click()

            rect = HitRect(
                x=bar_x,
                y=bar_y,
                width=bar_width,
                height=bar_height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "color",
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_click=on_click,
            )
            manager.register(rect)
            rect.item_id = str(id(item))
            # ColorItem用のフラグを設定（update_positions()で使用）
            rect._is_color_bar = True
        elif isinstance(item, RadioGroupItem):
            # ラジオボタングループ: ホバーとクリックで個々のボタンを判定
            # style への参照をクロージャでキャプチャ
            style = self.style

            def on_hover_enter():
                pass  # on_move で詳細な処理

            def on_hover_leave():
                item._hovered_index = -1

            def on_move(x: float, y: float):
                # ホバー中のボタンを判定
                item._hovered_index = item.get_button_at(x, y, style)

            def on_click():
                # クリックされたボタンを選択
                # 最後のホバーインデックスを使用
                if item._hovered_index >= 0:
                    item.select_by_index(item._hovered_index)

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag="radio_group",
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_move=on_move,
                on_click=on_click,
            )
            manager.register(rect)
            rect.item_id = str(id(item))
        elif isinstance(item, CheckboxItem):
            # チェックボックス: クリックでトグル
            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_click():
                item.toggle()

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "checkbox",
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_click=on_click,
            )
            manager.register(rect)
            rect.item_id = str(id(item))
        elif isinstance(item, ToggleItem):
            # トグルボタン: クリックでトグル
            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_click():
                item.toggle()

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "toggle",
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_click=on_click,
            )
            manager.register(rect)
            rect.item_id = str(id(item))
        elif isinstance(item, SliderItem):
            # スライダー: ドラッグで値を変更
            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_drag_start(mouse_x: float, mouse_y: float):
                item._dragging = True
                # ドラッグ開始時にクリック位置から値を設定
                item.set_value_from_position(mouse_x)

            def on_drag(dx: float, dy: float, mouse_x: float, mouse_y: float):
                # ドラッグ中は絶対位置から値を更新
                item.set_value_from_position(mouse_x)

            def on_drag_end(inside: bool):
                item._dragging = False

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "slider",
                draggable=True,
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_press=on_drag_start,
                on_drag=on_drag,
                on_release=on_drag_end,
            )
            manager.register(rect)
            # item_id を保存（状態取得用）
            rect.item_id = str(id(item))
        elif isinstance(item, NumberItem):
            # 数値フィールド: ドラッグで値を変更（dx に応じて）
            def on_hover_enter():
                item._hovered = True

            def on_hover_leave():
                item._hovered = False

            def on_drag_start(mouse_x: float, mouse_y: float):
                item._dragging = True

            def on_drag(dx: float, dy: float, mouse_x: float, mouse_y: float):
                # ドラッグ移動量から値を更新
                item.set_value_from_delta(dx)

            def on_drag_end(inside: bool):
                item._dragging = False

            rect = HitRect(
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                item=item,  # update_positions() で位置同期するため必須
                tag=item.text or "number",
                draggable=True,
                on_hover_enter=on_hover_enter,
                on_hover_leave=on_hover_leave,
                on_press=on_drag_start,
                on_drag=on_drag,
                on_release=on_drag_end,
            )
            manager.register(rect)
            rect.item_id = str(id(item))
        else:
            rect = manager.register_item(item)

        if hasattr(item, 'text') and item.text:
            rect.tag = item.text
