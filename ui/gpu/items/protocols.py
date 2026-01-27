# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Widget Protocols

ウィジェットの共通インターフェースを定義する Protocol。
既存クラスに対して structural subtyping で機能する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from ..style import GPULayoutStyle

T = TypeVar("T")


@runtime_checkable
class ValueWidget(Protocol[T]):
    """
    値を持つウィジェットのプロトコル

    Examples:
        - SliderItem: ValueWidget[float]
        - CheckboxItem: ValueWidget[bool]
        - NumberItem: ValueWidget[float]
        - RadioGroupItem: ValueWidget[str]
    """
    value: T

    def get_value(self) -> T:
        """現在の値を取得"""
        ...

    def set_value(self, value: T) -> None:
        """値を設定（UI も更新）"""
        ...


@runtime_checkable
class EditableWidget(ValueWidget[T], Protocol[T]):
    """
    編集可能なウィジェットのプロトコル

    ValueWidget に on_change コールバックを追加。
    """
    on_change: Callable[[T], None] | None


@runtime_checkable
class InteractiveWidget(Protocol):
    """
    インタラクティブなウィジェットのプロトコル

    ホバー・プレス状態を持つウィジェット用。
    """
    hovered: bool
    pressed: bool


@runtime_checkable
class DrawableItem(Protocol):
    """
    描画可能なアイテムのプロトコル

    LayoutItem の最小インターフェース。
    """
    x: float
    y: float
    width: float
    height: float
    visible: bool
    enabled: bool

    def draw(self, style: GPULayoutStyle) -> None:
        """描画"""
        ...

    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]:
        """サイズを計算"""
        ...
