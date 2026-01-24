# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Property Widgets
"""

from __future__ import annotations

import bpy
from typing import Any, Callable, Optional

from ..binding import PropertyBinding
from ..context import TrackedAccess
from ..items import (
    LayoutItem,
    LabelItem,
    PropDisplayItem,
    ToggleItem,
    CheckboxItem,
    SliderItem,
    NumberItem,
    ColorItem,
    RadioGroupItem,
    RadioOption,
)
from ..rna_utils import (
    get_property_info,
    get_property_value,
    set_property_value,
    PropType,
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


    def prop(self, data: Any, property: str, *, text: str = "",
             icon: str = "NONE", expand: bool = False, slider: bool = False,
             toggle: int = -1, icon_only: bool = False, key: str = "") -> Optional[LayoutItem]:
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
            current_value, set_value, key
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
        set_value: Callable[[Any, Any], None],
        key: str,
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
                key=key,
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
                key=key,
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
                key=key,
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
                key=key,
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
                key=key,
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
                    key=key,
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
                    key=key,
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
                    key=key,
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
                    key=key,
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
