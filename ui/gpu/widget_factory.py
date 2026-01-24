# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Widget Factory

WidgetHint からウィジェットインスタンスを生成するファクトリ。
prop() メソッドのウィジェット生成ロジックを集約。
"""

from __future__ import annotations

import bpy
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .rna_utils import WidgetHint, PropertyInfo, PropType
from .items import (
    LayoutItem,
    LabelItem,
    CheckboxItem,
    ToggleItem,
    NumberItem,
    SliderItem,
    ColorItem,
    RadioGroupItem,
    RadioOption,
)


@dataclass
class WidgetContext:
    """
    ウィジェット生成に必要なコンテキスト情報

    Attributes:
        text: 表示テキスト
        icon: アイコン名
        key: LayoutKey 用のキー
        enabled: 有効/無効
        active: アクティブ状態
        set_value: 値変更時のコールバック（bpy.context を受け取る）
    """
    text: str = ""
    icon: str = "NONE"
    key: str = ""
    enabled: bool = True
    active: bool = True
    set_value: Optional[Callable[[Any, Any], None]] = None


class WidgetFactory:
    """
    WidgetHint に応じてウィジェットを生成するファクトリ

    Usage:
        info = get_property_info(data, property)
        ctx = WidgetContext(text="Label", enabled=True, set_value=setter)
        widget = WidgetFactory.create(info.widget_hint, info, value, ctx)
    """

    @classmethod
    def create(
        cls,
        hint: WidgetHint,
        info: PropertyInfo,
        value: Any,
        ctx: WidgetContext,
    ) -> Optional[LayoutItem]:
        """
        ウィジェットを生成

        Args:
            hint: ウィジェットタイプのヒント
            info: RNA プロパティ情報
            value: 現在の値
            ctx: 生成コンテキスト

        Returns:
            生成されたウィジェット、または None（未対応の場合）
        """
        creator = cls._creators.get(hint)
        if creator:
            return creator(info, value, ctx)
        return None

    @classmethod
    def register(cls, hint: WidgetHint, creator: Callable) -> None:
        """
        カスタムウィジェットクリエーターを登録

        新しいウィジェットタイプを追加する際に使用。
        """
        cls._creators[hint] = creator

    # ─────────────────────────────────────────────────────────────────────────
    # Private Creators
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _create_checkbox(info: PropertyInfo, value: Any, ctx: WidgetContext) -> CheckboxItem:
        def on_toggle(new_value: bool):
            if ctx.set_value:
                ctx.set_value(bpy.context, new_value)

        return CheckboxItem(
            text=ctx.text,
            value=bool(value),
            key=ctx.key,
            on_toggle=on_toggle,
            enabled=ctx.enabled and ctx.active,
        )

    @staticmethod
    def _create_toggle(info: PropertyInfo, value: Any, ctx: WidgetContext) -> ToggleItem:
        def on_toggle(new_value: bool):
            if ctx.set_value:
                ctx.set_value(bpy.context, new_value)

        return ToggleItem(
            text=ctx.text,
            icon=ctx.icon,
            value=bool(value),
            key=ctx.key,
            on_toggle=on_toggle,
            enabled=ctx.enabled and ctx.active,
        )

    @staticmethod
    def _create_number(info: PropertyInfo, value: Any, ctx: WidgetContext) -> NumberItem:
        def on_change(new_value: float):
            if info.prop_type == PropType.INT:
                new_value = int(new_value)
            if ctx.set_value:
                ctx.set_value(bpy.context, new_value)

        min_val = info.soft_min if info.soft_min is not None else (info.min_value or -1e9)
        max_val = info.soft_max if info.soft_max is not None else (info.max_value or 1e9)

        return NumberItem(
            value=float(value) if value is not None else 0.0,
            min_val=min_val,
            max_val=max_val,
            step=info.step,
            precision=info.precision if info.prop_type == PropType.FLOAT else 0,
            text=ctx.text,
            key=ctx.key,
            on_change=on_change,
            enabled=ctx.enabled and ctx.active,
        )

    @staticmethod
    def _create_slider(info: PropertyInfo, value: Any, ctx: WidgetContext) -> SliderItem:
        def on_change(new_value: float):
            if info.prop_type == PropType.INT:
                new_value = int(new_value)
            if ctx.set_value:
                ctx.set_value(bpy.context, new_value)

        min_val = info.soft_min if info.soft_min is not None else (info.min_value or 0.0)
        max_val = info.soft_max if info.soft_max is not None else (info.max_value or 1.0)

        return SliderItem(
            value=float(value) if value is not None else 0.0,
            min_val=min_val,
            max_val=max_val,
            precision=info.precision if info.prop_type == PropType.FLOAT else 0,
            text=ctx.text,
            key=ctx.key,
            on_change=on_change,
            enabled=ctx.enabled and ctx.active,
        )

    @staticmethod
    def _create_color(info: PropertyInfo, value: Any, ctx: WidgetContext) -> ColorItem:
        if isinstance(value, (list, tuple)):
            if len(value) == 3:
                color = (*value, 1.0)
            elif len(value) >= 4:
                color = tuple(value[:4])
            else:
                color = (1.0, 1.0, 1.0, 1.0)
        else:
            color = (1.0, 1.0, 1.0, 1.0)

        return ColorItem(
            color=color,
            text=ctx.text,
            key=ctx.key,
            enabled=ctx.enabled and ctx.active,
        )

    @staticmethod
    def _create_radio(info: PropertyInfo, value: Any, ctx: WidgetContext) -> Optional[LayoutItem]:
        # 動的 Enum はラベル表示にフォールバック
        if info.is_dynamic_enum:
            display_name = info.enum_items[0][1] if info.enum_items else str(value)
            return LabelItem(
                text=f"{ctx.text}: {display_name}",
                key=ctx.key,
                enabled=ctx.enabled and ctx.active,
            )

        def on_change(new_value: str):
            if ctx.set_value:
                ctx.set_value(bpy.context, new_value)

        options = [
            RadioOption(value=ident, label=name)
            for ident, name, _ in info.enum_items
        ]

        return RadioGroupItem(
            options=options,
            value=str(value) if value else "",
            key=ctx.key,
            on_change=on_change,
            enabled=ctx.enabled and ctx.active,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Creator Registry
    # ─────────────────────────────────────────────────────────────────────────

    _creators: dict[WidgetHint, Callable[[PropertyInfo, Any, WidgetContext], Optional[LayoutItem]]] = {}


# 初期登録
WidgetFactory._creators = {
    WidgetHint.CHECKBOX: WidgetFactory._create_checkbox,
    WidgetHint.TOGGLE: WidgetFactory._create_toggle,
    WidgetHint.NUMBER: WidgetFactory._create_number,
    WidgetHint.SLIDER: WidgetFactory._create_slider,
    WidgetHint.COLOR: WidgetFactory._create_color,
    WidgetHint.RADIO: WidgetFactory._create_radio,
    # MENU, VECTOR, TEXT は後で追加
}
