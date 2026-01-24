# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Layout Containers
"""

from __future__ import annotations

import bpy
from typing import Callable, Optional

from ..style import Direction, Alignment
from ..items import (
    LabelItem,
    SeparatorItem,
    ButtonItem,
    ToggleItem,
    SliderItem,
    NumberItem,
    CheckboxItem,
    ColorItem,
    RadioGroupItem,
    RadioOption,
)
from ..uilayout_stubs import OperatorProperties
from ....infra.debug import DBG_GPU, logi


class LayoutContainerMixin:
    """Mixin methods."""


    def row(self, align: bool = False, heading: str = "") -> GPULayout:
        """
        水平レイアウトを作成

        Args:
            align: True の場合、アイテム間のスペースをなくす
            heading: 見出しテキスト（最初のアイテム追加時にラベルとして表示）
        """
        child = GPULayout(
            x=self._cursor_x,
            y=self._cursor_y,
            width=self._get_available_width(),
            style=self.style,
            direction=Direction.HORIZONTAL,
            parent=self
        )
        self._assign_layout_path(child, "row")
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        child.operator_context = self.operator_context
        child.use_property_split = self.use_property_split
        child._align = align  # アイテム間スペースを制御
        child._heading = heading  # 見出しテキスト
        self._elements.append(child)  # Phase 1: _elements に統合
        return child


    def column(self, align: bool = False, heading: str = "") -> GPULayout:
        """
        垂直レイアウトを作成

        Args:
            align: True の場合、アイテム間のスペースをなくす
            heading: 見出しテキスト（最初のアイテム追加時にラベルとして表示）

        Note:
            split() 内で呼ばれた場合、factor に基づいて幅が計算される。
            - factor > 0: 最初の column が factor 割合、残りは均等分割
            - factor == 0: 全ての column を均等分割

            v3 アルゴリズム (3列以上対応):
            - 最初の列: factor 割合
            - 2番目以降: 残り幅を (n-1) で均等分割
            例: factor=0.25 で 3列 → 25% : 37.5% : 37.5%

            幅の確定は arrange フェーズで行われる。
            ここでは親の幅をプレースホルダとして設定。
        """
        available_width = self._get_available_width()

        # v3: 幅は arrange フェーズで確定する
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
        self._assign_layout_path(child, "column")
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        child.operator_context = self.operator_context
        child.use_property_split = self.use_property_split
        child._align = align
        child._heading = heading  # 見出しテキスト
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
        self._assign_layout_path(child, "split")
        child._split_factor = factor
        child._is_split = True
        child._align = align
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        child.operator_context = self.operator_context
        child.use_property_split = self.use_property_split
        self._elements.append(child)  # Phase 1: _elements に統合
        return child


    def column_flow(self, columns: int = 0, align: bool = False) -> GPULayout:
        """
        複数列フローレイアウトを作成

        アイテムは上から下に配置され、累積高さが閾値を超えると
        自動的に次の列へ移動します。

        Args:
            columns: 列数（0 = 自動計算）
            align: True の場合、アイテム間のスペースをなくす

        使用例:
            flow = layout.column_flow(columns=2)
            flow.label(text="A")
            flow.label(text="B")
            flow.label(text="C")
            flow.label(text="D")
            # 結果:
            # A  C
            # B  D
        """
        child = GPULayout(
            x=self._cursor_x,
            y=self._cursor_y,
            width=self._get_available_width(),
            style=self.style,
            direction=Direction.VERTICAL,  # 縦方向に積む（Blender と同じ）
            parent=self
        )
        self._assign_layout_path(child, "column_flow")
        child._is_column_flow = True
        child._flow_columns = columns
        child._align = align
        child.active = self.active
        child.enabled = self.enabled
        child.alert = self.alert
        child.operator_context = self.operator_context
        child.use_property_split = self.use_property_split
        self._elements.append(child)
        return child

    # ─────────────────────────────────────────────────────────────────────────
    # 表示メソッド（UILayout 互換）
    # ─────────────────────────────────────────────────────────────────────────


    def label(self, *, text: str = "", icon: str = "NONE", key: str = "", wrap: bool = False) -> LabelItem:
        """ラベルを追加"""
        item = LabelItem(
            text=text,
            icon=icon,
            wrap=wrap,
            key=key,
            enabled=self.enabled and self.active,
            alert=self.alert
        )
        self._add_item(item)
        return item


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
        key: str = "",
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
            key=key,
            enabled=self.enabled and self.active and enabled and active,
        )
        self._add_item(item)

        # OperatorProperties を返す（プロパティ代入を受け付ける）
        # ButtonItem への参照を保持（将来の拡張用）
        object.__setattr__(op_props, "_button_item", item)
        return op_props


    def slider(self, *, value: float = 0.0, min_val: float = 0.0, max_val: float = 1.0,
               precision: int = 2, text: str = "", key: str = "",
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
            key=key,
            on_change=on_change,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item


    def number(self, *, value: float = 0.0, min_val: float = -float('inf'),
               max_val: float = float('inf'), step: float = 0.01,
               precision: int = 2, text: str = "", show_buttons: bool = False,
               key: str = "",
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
            key=key,
            on_change=on_change,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item


    def checkbox(self, *, text: str = "", value: bool = False, key: str = "",
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
            key=key,
            on_toggle=on_toggle,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item


    def radio_group(self, *, options: list = None, value: str = "", key: str = "",
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
            key=key,
            on_change=on_change,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item


    def toggle(self, *, text: str = "", icon: str = "NONE",
               icon_on: str = "NONE", icon_off: str = "NONE",
               value: bool = False, key: str = "",
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
            key=key,
            on_toggle=on_toggle,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item


    def color(self, *, color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
              text: str = "", key: str = "",
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
            key=key,
            on_click=on_click,
            enabled=self.enabled and self.active
        )
        self._add_item(item)
        return item

    # ─────────────────────────────────────────────────────────────────────────
    # プロパティメソッド
    # ─────────────────────────────────────────────────────────────────────────
