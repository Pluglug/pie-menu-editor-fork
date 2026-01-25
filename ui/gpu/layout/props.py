# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Property Widgets
"""

from __future__ import annotations

import bpy
from typing import Any, Callable, Optional

from ..binding import PropertyBinding
from ..context import TrackedAccess
from ..style import Direction
from ..items import (
    LayoutItem,
    PropDisplayItem,
)
from ..rna_utils import (
    get_property_info,
    get_property_value,
    set_property_value,
    get_index_labels,
    WidgetHint,
    PropertyInfo,
)
from ....infra.debug import DBG_GPU, logi


class LayoutPropMixin:
    """Mixin methods."""


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


    def _make_indexed_setter(
        self,
        resolver: Optional[Callable[[Any], Any]],
        data: Any,
        prop_name: str,
        index: int,
    ) -> Callable[[Any, Any], None]:
        """
        配列プロパティの特定要素を設定する setter を作成

        Args:
            resolver: コンテキストからデータを解決する関数
            data: 静的データ（resolver が None の場合に使用）
            prop_name: プロパティ名
            index: 設定する配列インデックス

        Returns:
            setter 関数
        """
        def setter(context: Any, value: Any) -> None:
            target = resolver(context) if resolver else data
            if target is None:
                return
            # 現在の配列を取得してリストに変換
            current = get_property_value(target, prop_name)
            if current is None:
                return
            current_list = list(current)
            # 特定要素を更新
            if 0 <= index < len(current_list):
                current_list[index] = value
                set_property_value(target, prop_name, current_list)

        return setter


    def prop(self, data: Any, property: str, *, text: Optional[str] = None,
             icon: str = "NONE", expand: bool = False, slider: bool = False,
             toggle: int = -1, icon_only: bool = False, index: int = -1,
             key: str = "") -> Optional[LayoutItem]:
        """
        Blender プロパティを適切なウィジェットで表示・編集

        RNA introspection を使用して、プロパティタイプに応じた
        最適なウィジェットを自動選択します。

        Args:
            data: プロパティを持つオブジェクト（例: bpy.context.object）
            property: プロパティ名（例: "location"）
            text: 表示テキスト（None=プロパティ名を使用、""=ラベルなし）
            icon: アイコン名
            expand: Enum を展開表示（RadioGroup）するか
            slider: 数値をスライダー表示するか
            toggle: -1=自動, 0=チェックボックス, 1=トグルボタン
            icon_only: アイコンのみ表示
            index: 配列プロパティの特定要素のみ表示 (-1=全要素, 0+=特定要素)

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

            # 配列プロパティの特定要素
            layout.prop(C.object, "location", index=0)  # X のみ
            layout.prop(C.object, "location", index=1)  # Y のみ
            layout.prop(C.object, "location", index=2)  # Z のみ
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
        # text=None → プロパティ名を使用（Blender デフォルト）
        # text="" → ラベルなし（明示的に空を指定）
        # text="Custom" → その文字列を使用
        display_text = info.name if text is None else text

        # アイコンの決定: 明示的に指定されていなければ PropertyInfo から取得
        # (Blender の RNA_def_property_ui_icon で定義されたアイコン)
        effective_icon = icon if icon != "NONE" else info.icon

        # use_property_split 処理
        # icon_only や readonly の場合は通常処理にフォールスルー
        if self.use_property_split and not icon_only and not info.is_readonly:
            return self._prop_with_split(
                raw_data, property, info, display_text, effective_icon,
                expand, slider, toggle, index, key, resolver
            )

        # index が指定された場合、配列要素用のラベルを追加
        is_indexed = index >= 0 and info.is_array
        if is_indexed:
            index_labels = get_index_labels(info.subtype, info.array_length)
            if index < len(index_labels):
                index_label = index_labels[index]
            else:
                index_label = str(index)

            if text:
                display_text = f"{text} {index_label}"
            else:
                display_text = f"{info.name} {index_label}"

        # 読み取り専用の場合は表示のみ
        if info.is_readonly:
            self.prop_display(raw_data, property, text=display_text, icon=icon)
            return None

        # 現在値を取得
        current_value = get_property_value(raw_data, property)

        # index が指定された場合は配列の特定要素のみ取得
        if is_indexed:
            if isinstance(current_value, (list, tuple)) and index < len(current_value):
                current_value = current_value[index]
            else:
                current_value = 0  # フォールバック

        # ウィジェットヒントに応じてアイテムを作成
        hint = info.widget_hint

        # index 指定時は配列ウィジェットを単一値ウィジェットに変更
        if is_indexed:
            if hint == WidgetHint.VECTOR:
                hint = WidgetHint.SLIDER if slider else WidgetHint.NUMBER
            elif hint == WidgetHint.COLOR:
                # COLOR の特定チャンネルは NUMBER/SLIDER で編集
                hint = WidgetHint.SLIDER if slider else WidgetHint.NUMBER

        # スライダー/数値の強制切り替え
        if slider and hint == WidgetHint.NUMBER:
            hint = WidgetHint.SLIDER
        elif not slider and hint == WidgetHint.SLIDER:
            # slider=False は明示的に指定された場合のみ NUMBER に切り替え
            pass  # デフォルトは維持

        # Enum の expand 切り替え
        if expand and hint == WidgetHint.MENU:
            hint = WidgetHint.RADIO

        # トグル/チェックボックスの切り替え
        # toggle=-1 (自動): icon があれば TOGGLE、なければ CHECKBOX (Blender の動作)
        # toggle=0: 常に CHECKBOX
        # toggle=1: 常に TOGGLE
        if toggle == 1 and hint == WidgetHint.CHECKBOX:
            hint = WidgetHint.TOGGLE
        elif toggle == 0 and hint == WidgetHint.TOGGLE:
            hint = WidgetHint.CHECKBOX
        elif toggle == -1 and hint == WidgetHint.CHECKBOX and effective_icon != "NONE":
            # Blender の動作: icon があれば IconToggle を使用
            hint = WidgetHint.TOGGLE

        # setter の作成（index 指定時は indexed setter を使用）
        if is_indexed:
            set_value = self._make_indexed_setter(resolver, raw_data, property, index)
        else:
            set_value = self._make_setter(resolver, raw_data, property)
        item = self._create_prop_widget(
            raw_data, property, info, hint, display_text, effective_icon,
            current_value, set_value, key, icon_only=icon_only
        )
        if item:
            self._add_item(item)
            meta = {
                "is_dynamic_enum": info.is_dynamic_enum,
                "label_prefix": display_text,
                "index": index,  # 配列要素のインデックス (-1 は全要素)
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
        set_value: Callable[[Any, Any], None],
        key: str,
        icon_only: bool = False,
    ) -> Optional[LayoutItem]:
        """
        プロパティ用ウィジェットを作成

        WidgetFactory に委譲し、未対応の場合は prop_display() にフォールバック。
        """
        from ..widget_factory import WidgetFactory, WidgetContext

        # ベクトルは基本的に水平表示（Blender デフォルト）
        # 将来的に expand=True で垂直表示をサポート予定
        is_vertical = False

        ctx = WidgetContext(
            text=text,
            icon=icon,
            icon_only=icon_only,
            key=key,
            enabled=self.enabled,
            active=self.active,
            vertical=is_vertical,
            set_value=set_value,
        )

        item = WidgetFactory.create(hint, info, value, ctx)

        if item is None:
            # 未対応のウィジェットは表示のみ
            self.prop_display(data, property, text=text, icon=icon)
            return None

        return item


    def _prop_with_split(
        self, data: Any, property: str, info: PropertyInfo,
        text: str, icon: str,
        expand: bool, slider: bool, toggle: int,
        index: int, key: str,
        resolver: Optional[Callable[[Any], Any]],
    ) -> Optional[LayoutItem]:
        """
        use_property_split=True 時のプロパティ描画

        左カラム (40%): ラベル（右寄せ）
        右カラム (60%): ウィジェット（ラベルなし）

        ┌──────────────┬──────────────────────┐
        │ Location     │ [X][Y][Z]            │
        │ (40%, 右寄せ) │ (60%, ウィジェット)    │
        └──────────────┴──────────────────────┘

        VECTOR プロパティの場合は各要素を個別の split 行として表示:
        ┌────────────────┬────────────────────────┐
        │ Location X     │ [────────────]         │
        │          Y     │ [────────────]         │
        │          Z     │ [────────────]         │
        └────────────────┴────────────────────────┘
        """
        from ..widget_factory import WidgetFactory, WidgetContext
        from ..style import Alignment

        # index 処理（配列要素用ラベル）
        is_indexed = index >= 0 and info.is_array
        if is_indexed:
            index_labels = get_index_labels(info.subtype, info.array_length)
            if index < len(index_labels):
                index_label = index_labels[index]
            else:
                index_label = str(index)
            display_text = f"{text} {index_label}" if text else f"{info.name} {index_label}"
        else:
            display_text = text

        # 現在値を取得
        current_value = get_property_value(data, property)
        if is_indexed:
            if isinstance(current_value, (list, tuple)) and index < len(current_value):
                current_value = current_value[index]
            else:
                current_value = 0

        # ウィジェットヒントを決定
        hint = info.widget_hint

        # VECTOR ヒントかつ index 未指定の場合は特別処理（各要素を個別 split 行として表示）
        if hint == WidgetHint.VECTOR and not is_indexed:
            return self._prop_split_vector(
                data, property, info, display_text, icon,
                slider, key, resolver
            )

        # index 指定時は配列ウィジェットを単一値ウィジェットに変更
        if is_indexed:
            if hint == WidgetHint.VECTOR:
                hint = WidgetHint.SLIDER if slider else WidgetHint.NUMBER
            elif hint == WidgetHint.COLOR:
                hint = WidgetHint.SLIDER if slider else WidgetHint.NUMBER

        # スライダー/数値の強制切り替え
        if slider and hint == WidgetHint.NUMBER:
            hint = WidgetHint.SLIDER

        # Enum の expand 切り替え
        if expand and hint == WidgetHint.MENU:
            hint = WidgetHint.RADIO

        # トグル/チェックボックスの切り替え
        # toggle=-1 (自動): icon があれば TOGGLE、なければ CHECKBOX (Blender の動作)
        # toggle=0: 常に CHECKBOX
        # toggle=1: 常に TOGGLE
        if toggle == 1 and hint == WidgetHint.CHECKBOX:
            hint = WidgetHint.TOGGLE
        elif toggle == 0 and hint == WidgetHint.TOGGLE:
            hint = WidgetHint.CHECKBOX
        elif toggle == -1 and hint == WidgetHint.CHECKBOX and icon != "NONE":
            # Blender の動作: icon があれば IconToggle を使用
            hint = WidgetHint.TOGGLE

        # Split レイアウト作成
        split = self.split(factor=self.style.split_factor, align=True)

        # 左カラム: ラベル（右寄せ）
        # Blender 準拠: ラベル側にはアイコンを描画しない（ICON_NONE）
        col1 = split.column()
        col1.alignment = Alignment.RIGHT
        col1.use_property_split = False  # 再帰防止
        col1.label(text=display_text)

        # 右カラム: ウィジェット（ラベルなし）
        col2 = split.column()
        col2.use_property_split = False  # 再帰防止

        # setter の作成
        if is_indexed:
            set_value = self._make_indexed_setter(resolver, data, property, index)
        else:
            set_value = self._make_setter(resolver, data, property)

        # Blender 準拠: アイコンはウィジェット側（ボタン内）に描画
        ctx = WidgetContext(
            text="",  # ラベルなし（左カラムに表示済み）
            icon=icon,
            icon_only=False,
            key=key,
            enabled=self.enabled,
            active=self.active,
            vertical=False,
            set_value=set_value,
            use_property_split=True,
        )

        item = WidgetFactory.create(hint, info, current_value, ctx)

        if item is None:
            col2.prop_display(data, property, text="")
            return None

        col2._add_item(item)

        # バインディング登録
        meta = {
            "is_dynamic_enum": info.is_dynamic_enum,
            "label_prefix": display_text,
            "index": index,
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
            def resolve_static(_ctx, data=data):
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


    def _prop_split_vector(
        self, data: Any, property: str, info: PropertyInfo,
        text: str, icon: str,
        slider: bool, key: str,
        resolver: Optional[Callable[[Any], Any]],
    ) -> Optional[LayoutItem]:
        """
        use_property_split=True 時の Vector プロパティ描画

        各要素を個別の split 行として配置:
        ┌────────────────┬────────────────────────┐
        │ Location X     │ [────────────]         │
        │          Y     │ [────────────]         │
        │          Z     │ [────────────]         │
        └────────────────┴────────────────────────┘

        Blender の処理と同様に、最初の行のみフルラベルを表示し、
        以降の行はインデックスラベル（Y, Z）のみを表示する。
        """
        from ..widget_factory import WidgetFactory, WidgetContext
        from ..style import Alignment

        if DBG_GPU:
            logi(f"[_prop_split_vector] property={property}, text={text}")

        try:
            # 現在値を取得
            current_value = get_property_value(data, property)
            if current_value is None:
                if DBG_GPU:
                    logi(f"[_prop_split_vector] current_value is None")
                return None

            # シーケンスに変換（Vector, list, tuple など）
            # mathutils.Vector は list/tuple ではないが、イテラブルなので tuple() で変換
            try:
                current_value = tuple(current_value)
            except TypeError:
                if DBG_GPU:
                    logi(f"[_prop_split_vector] not iterable: {type(current_value)}")
                return None

            if len(current_value) == 0:
                return None

            # インデックスラベル取得 ("X", "Y", "Z" など)
            index_labels = get_index_labels(info.subtype, len(current_value))

            # 数値ウィジェットのヒント（slider オプションに基づく）
            number_hint = WidgetHint.SLIDER if slider else WidgetHint.NUMBER

            # 全行を column(align=True) で囲んでグループ化
            # Blender と同様に X, Y, Z が視覚的にまとまる
            outer_col = self.column(align=True)

            items = []
            num_elements = len(current_value)
            for i in range(num_elements):
                # ラベル決定: 最初の行のみフルラベル
                if i == 0:
                    label = f"{text} {index_labels[i]}" if text else f"{info.name} {index_labels[i]}"
                else:
                    label = index_labels[i]

                # Split 作成（outer_col 内に配置）
                split = outer_col.split(factor=self.style.split_factor, align=True)

                # 左カラム: ラベル（右寄せ）
                col1 = split.column()
                col1.alignment = Alignment.RIGHT
                col1.use_property_split = False  # 再帰防止
                col1.label(text=label)

                # 右カラム: NumberItem / SliderItem
                # align=True で縦方向の連結（Blender互換）
                col2 = split.column(align=True)
                col2.use_property_split = False  # 再帰防止

                # setter 作成（配列要素用）
                set_value = self._make_indexed_setter(resolver, data, property, i)

                # ウィジェット作成
                ctx = WidgetContext(
                    text="",  # ラベルなし（左カラムに表示済み）
                    icon="NONE",
                    enabled=self.enabled,
                    active=self.active,
                    set_value=set_value,
                    use_property_split=True,
                )

                item = WidgetFactory.create(number_hint, info, current_value[i], ctx)
                if item:
                    col2._add_item(item)
                    items.append(item)

                    # バインディング登録
                    meta = {
                        "is_dynamic_enum": False,
                        "label_prefix": label,
                        "index": i,
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
                        def resolve_static(_ctx, data=data):
                            return data
                        binding = PropertyBinding(
                            resolve_data=resolve_static,
                            set_value=set_value,
                            prop_name=property,
                            widget=item,
                            meta=meta,
                        )
                        self._static_bindings.append(binding)

                    if DBG_GPU:
                        logi(f"[_prop_split_vector] created item {i}: {item}")

            # 最初のアイテムを返す（互換性のため）
            return items[0] if items else None

        except Exception as e:
            import traceback
            logi(f"[_prop_split_vector] ERROR: {e}")
            logi(traceback.format_exc())
            return None


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

        for element in self._elements:
            if not isinstance(element, GPULayout):
                continue
            if element.sync_reactive(context, epoch):
                any_changed = True
            if element.dirty:
                needs_relayout = True

        if needs_relayout:
            self.mark_dirty()

        return any_changed


    def sync_props(self) -> None:
        self._epoch += 1
        self.sync_reactive(bpy.context, self._epoch)


    def prop_display(self, data: Any, property: str, *,
                     text: Optional[str] = None, icon: str = "NONE") -> None:
        """プロパティ値を表示（明示的に読み取り専用）

        Args:
            data: プロパティを持つオブジェクト
            property: プロパティ名
            text: 表示ラベル（None=プロパティ名を使用、""=ラベルなし）
            icon: アイコン名
        """
        item = PropDisplayItem(
            data=data,
            property=property,
            text=text,  # None はそのまま渡す（PropDisplayItem 側で処理）
            icon=icon,
            enabled=self.enabled and self.active
        )
        self._add_item(item)


    def prop_enum(self, data: Any, property: str, value: str, *,
                  text: Optional[str] = None, icon: str = "NONE") -> None:
        """Enum プロパティの特定値を表示

        Args:
            data: プロパティを持つオブジェクト
            property: プロパティ名
            value: 表示する Enum 値
            text: 表示ラベル（None=value を使用、""=ラベルなし）
            icon: アイコン名
        """
        try:
            current = getattr(data, property)
            is_active = current == value
        except AttributeError:
            is_active = False

        display_text = value if text is None else text
        if is_active:
            display_text = f"● {display_text}"
        else:
            display_text = f"○ {display_text}"

        self.label(text=display_text, icon=icon)

    # ─────────────────────────────────────────────────────────────────────────
    # ユーティリティメソッド
    # ─────────────────────────────────────────────────────────────────────────
