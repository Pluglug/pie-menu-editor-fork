# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - RNA Property Utilities

Blender の RNA プロパティを解析し、適切なウィジェットを選択するためのユーティリティ。
"""

from __future__ import annotations

import bpy
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Optional, Sequence

if TYPE_CHECKING:
    from bpy.types import bpy_struct


_ICON_ID_TO_NAME: Optional[dict[int, str]] = None


def _get_icon_id_map() -> dict[int, str]:
    """UILayout の icon enum から ID→名前のマップを構築（キャッシュ）"""
    global _ICON_ID_TO_NAME
    if _ICON_ID_TO_NAME is None:
        try:
            enum_items = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items
            _ICON_ID_TO_NAME = {item.value: item.identifier for item in enum_items}
        except Exception:
            _ICON_ID_TO_NAME = {}
    return _ICON_ID_TO_NAME


def _normalize_icon_name(icon_value: Any) -> str:
    """RNA の icon 値を icon 名に正規化（未対応は NONE）"""
    if not icon_value or icon_value == "NONE":
        return "NONE"
    if isinstance(icon_value, str):
        return icon_value
    # bool は int の派生なので除外
    if isinstance(icon_value, int) and not isinstance(icon_value, bool):
        return _get_icon_id_map().get(icon_value, "NONE")
    return "NONE"


# ═══════════════════════════════════════════════════════════════════════════════
# Property Type Enums
# ═══════════════════════════════════════════════════════════════════════════════

class PropType(Enum):
    """RNA プロパティタイプ"""
    BOOLEAN = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    ENUM = auto()
    POINTER = auto()
    COLLECTION = auto()
    UNKNOWN = auto()


class WidgetHint(Enum):
    """推奨ウィジェットタイプ"""
    CHECKBOX = auto()      # Boolean (no icon)
    TOGGLE = auto()        # Boolean (with icon)
    NUMBER = auto()        # Int/Float (normal)
    SLIDER = auto()        # Int/Float (PERCENTAGE/FACTOR)
    COLOR = auto()         # Float array (COLOR/COLOR_GAMMA)
    TEXT = auto()          # String
    MENU = auto()          # Enum (dropdown)
    RADIO = auto()         # Enum (expanded)
    VECTOR = auto()        # Numeric array (XYZ, etc.)
    UNSUPPORTED = auto()   # Pointer, Collection, etc.


# ═══════════════════════════════════════════════════════════════════════════════
# Property Info Dataclass
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PropertyInfo:
    """
    RNA プロパティの解析結果

    Attributes:
        name: プロパティ名
        description: 説明文
        prop_type: プロパティタイプ
        subtype: サブタイプ（'PERCENTAGE', 'COLOR' など）
        is_array: 配列プロパティかどうか
        array_length: 配列の長さ（配列でない場合は 0）
        min_value: 最小値（数値の場合）
        max_value: 最大値（数値の場合）
        soft_min: ソフト最小値
        soft_max: ソフト最大値
        step: ステップ値
        precision: 小数点以下の桁数（Float の場合）
        enum_items: Enum アイテムのリスト
        default: デフォルト値
        widget_hint: 推奨ウィジェットタイプ
        is_readonly: 読み取り専用かどうか
        is_dynamic_enum: 動的 Enum かどうか（render.engine など）
        icon: RNA プロパティに紐づくアイコン名（'NONE' = なし）
    """
    name: str
    description: str
    prop_type: PropType
    subtype: str
    is_array: bool
    array_length: int
    min_value: Optional[float]
    max_value: Optional[float]
    soft_min: Optional[float]
    soft_max: Optional[float]
    step: float
    precision: int
    enum_items: list[tuple[str, str, str]]  # (identifier, name, description)
    default: Any
    widget_hint: WidgetHint
    is_readonly: bool
    is_dynamic_enum: bool = False
    icon: str = "NONE"


# ═══════════════════════════════════════════════════════════════════════════════
# Main Functions
# ═══════════════════════════════════════════════════════════════════════════════

def get_property_info(data: bpy_struct, prop_name: str) -> Optional[PropertyInfo]:
    """
    RNA プロパティの情報を取得

    Args:
        data: プロパティを持つオブジェクト（例: bpy.context.object）
        prop_name: プロパティ名（例: "location"）

    Returns:
        PropertyInfo: プロパティ情報（存在しない場合は None）

    Example:
        >>> info = get_property_info(C.object, "hide_viewport")
        >>> info.prop_type
        PropType.BOOLEAN
        >>> info.widget_hint
        WidgetHint.CHECKBOX
    """
    try:
        # bl_rna からプロパティ定義を取得
        rna_prop = data.bl_rna.properties.get(prop_name)
        if rna_prop is None:
            return None

        # 基本情報
        name = rna_prop.name or prop_name
        description = rna_prop.description or ""
        is_readonly = rna_prop.is_readonly

        # プロパティに紐づくアイコン（RNA_def_property_ui_icon で定義されたもの）
        prop_icon = _normalize_icon_name(getattr(rna_prop, 'icon', 'NONE'))

        # プロパティタイプの判定
        prop_type = _get_prop_type(rna_prop)
        subtype = getattr(rna_prop, 'subtype', 'NONE')

        # 配列情報
        is_array = getattr(rna_prop, 'is_array', False)
        array_length = getattr(rna_prop, 'array_length', 0) if is_array else 0

        # 数値の範囲
        min_value = getattr(rna_prop, 'hard_min', None)
        max_value = getattr(rna_prop, 'hard_max', None)
        soft_min = getattr(rna_prop, 'soft_min', None)
        soft_max = getattr(rna_prop, 'soft_max', None)
        step = getattr(rna_prop, 'step', 1.0)
        precision = getattr(rna_prop, 'precision', 2)

        # Enum アイテム
        # 動的 Enum（render.engine など）に対応するため、複数の方法を試す
        enum_items = []
        is_dynamic_enum = False
        if prop_type == PropType.ENUM:
            # 方法 1: rna_type 経由（動的 enum で機能することが多い）
            try:
                rna_type_prop = data.rna_type.properties.get(prop_name)
                if rna_type_prop and hasattr(rna_type_prop, 'enum_items'):
                    for item in rna_type_prop.enum_items:
                        enum_items.append((item.identifier, item.name, item.description))
            except Exception:
                pass

            # 方法 2: 方法 1 で取得できなかった場合、bl_rna 経由
            if not enum_items:
                try:
                    for item in rna_prop.enum_items:
                        enum_items.append((item.identifier, item.name, item.description))
                except Exception:
                    pass

            # 動的 Enum の検出:
            # Python の enum_items は動的 Enum で正しく機能しない場合がある
            # (現在の値のみ返される)。この場合、現在値の表示名を取得して
            # フォールバックする
            if len(enum_items) <= 1:
                is_dynamic_enum = _detect_dynamic_enum(data, prop_name, enum_items)
                if is_dynamic_enum:
                    # 現在値の表示名を取得して enum_items を再構築
                    current_value = getattr(data, prop_name, None)
                    if current_value:
                        display_name = get_enum_display_name(
                            data, prop_name, current_value
                        )
                        # 既存の enum_items をクリアして現在値のみにする
                        enum_items = [(current_value, display_name, "")]

        # デフォルト値
        default = _get_default_value(rna_prop, prop_type, is_array)

        # 推奨ウィジェット
        widget_hint = _determine_widget_hint(
            prop_type, subtype, is_array, array_length
        )

        return PropertyInfo(
            name=name,
            description=description,
            prop_type=prop_type,
            subtype=subtype,
            is_array=is_array,
            array_length=array_length,
            min_value=min_value,
            max_value=max_value,
            soft_min=soft_min,
            soft_max=soft_max,
            step=step,
            precision=precision,
            enum_items=enum_items,
            default=default,
            widget_hint=widget_hint,
            is_readonly=is_readonly,
            is_dynamic_enum=is_dynamic_enum,
            icon=prop_icon,
        )

    except Exception:
        return None


def get_property_value(data: bpy_struct, prop_name: str) -> Any:
    """
    プロパティの現在値を取得

    Args:
        data: プロパティを持つオブジェクト
        prop_name: プロパティ名

    Returns:
        現在値（配列の場合はタプル）
    """
    value = getattr(data, prop_name, None)
    # 配列の場合はタプルに変換
    if hasattr(value, '__iter__') and not isinstance(value, str):
        return tuple(value)
    return value


def set_property_value(data: bpy_struct, prop_name: str, value: Any) -> bool:
    """
    プロパティの値を設定

    Args:
        data: プロパティを持つオブジェクト
        prop_name: プロパティ名
        value: 設定する値

    Returns:
        成功したかどうか
    """
    try:
        setattr(data, prop_name, value)
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════

def _get_prop_type(rna_prop) -> PropType:
    """RNA プロパティタイプを判定"""
    type_name = rna_prop.type
    mapping = {
        'BOOLEAN': PropType.BOOLEAN,
        'INT': PropType.INT,
        'FLOAT': PropType.FLOAT,
        'STRING': PropType.STRING,
        'ENUM': PropType.ENUM,
        'POINTER': PropType.POINTER,
        'COLLECTION': PropType.COLLECTION,
    }
    return mapping.get(type_name, PropType.UNKNOWN)


def _get_default_value(rna_prop, prop_type: PropType, is_array: bool) -> Any:
    """デフォルト値を取得"""
    try:
        if is_array:
            return tuple(rna_prop.default_array)
        elif prop_type == PropType.ENUM:
            return rna_prop.default
        else:
            return rna_prop.default
    except Exception:
        return None


def _detect_dynamic_enum(
    data: bpy_struct,
    prop_name: str,
    enum_items: list
) -> bool:
    """
    動的 Enum かどうかを検出

    Python の enum_items が正しく機能しない動的 Enum（render.engine など）を検出する。
    検出方法:
    1. enum_items が 1 個以下
    2. 現在値が enum_items に含まれていない、または
    3. データオブジェクトに関連する複数値ヒント（has_multiple_* など）がある
    """
    if len(enum_items) > 1:
        return False

    current_value = getattr(data, prop_name, None)
    if current_value is None:
        return False

    # 現在値が enum_items に含まれていない場合は動的
    if enum_items and current_value not in [item[0] for item in enum_items]:
        return True

    # 既知の動的 Enum プロパティパターン
    # render.engine は has_multiple_engines を持つ
    if prop_name == 'engine' and hasattr(data, 'has_multiple_engines'):
        return True

    return False


def get_enum_display_name(
    data: bpy_struct,
    prop_name: str,
    identifier: str
) -> str:
    """
    動的 Enum の表示名を取得

    UILayout.enum_item_name() を使用して、動的 Enum のアイテム表示名を取得する。
    Python の enum_items では取得できない動的 Enum に対応。

    Args:
        data: プロパティを持つオブジェクト
        prop_name: プロパティ名
        identifier: Enum アイテムの identifier

    Returns:
        表示名（取得できない場合は identifier をそのまま返す）
    """
    try:
        return bpy.types.UILayout.enum_item_name(data, prop_name, identifier)
    except Exception:
        return identifier


def _determine_widget_hint(
    prop_type: PropType,
    subtype: str,
    is_array: bool,
    array_length: int
) -> WidgetHint:
    """
    プロパティタイプとサブタイプから推奨ウィジェットを決定

    Blender の uiDefAutoButR() のロジックに基づく
    """
    # Boolean
    if prop_type == PropType.BOOLEAN:
        # 配列の場合は各要素が独立したチェックボックス
        return WidgetHint.CHECKBOX

    # Int / Float
    elif prop_type in (PropType.INT, PropType.FLOAT):
        # カラー配列
        if is_array and subtype in ('COLOR', 'COLOR_GAMMA'):
            return WidgetHint.COLOR

        # ベクトル配列（XYZ, TRANSLATION など）
        if is_array and array_length > 1:
            return WidgetHint.VECTOR

        # スライダー表示されるサブタイプ
        if subtype in ('PERCENTAGE', 'FACTOR'):
            return WidgetHint.SLIDER

        # 通常の数値
        return WidgetHint.NUMBER

    # String
    elif prop_type == PropType.STRING:
        return WidgetHint.TEXT

    # Enum
    elif prop_type == PropType.ENUM:
        # 展開表示かドロップダウンかは呼び出し側で決める
        # デフォルトはドロップダウン
        return WidgetHint.MENU

    # Pointer / Collection
    elif prop_type in (PropType.POINTER, PropType.COLLECTION):
        return WidgetHint.UNSUPPORTED

    return WidgetHint.UNSUPPORTED


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════════════════

def is_slider_subtype(subtype: str) -> bool:
    """スライダー表示されるサブタイプかどうか"""
    return subtype in ('PERCENTAGE', 'FACTOR')


def is_color_subtype(subtype: str) -> bool:
    """カラー表示されるサブタイプかどうか"""
    return subtype in ('COLOR', 'COLOR_GAMMA')


# サブタイプに基づくインデックスラベルのマッピング
_SUBTYPE_INDEX_LABELS: dict[str, tuple[str, ...]] = {
    'TRANSLATION': ('X', 'Y', 'Z'),
    'XYZ': ('X', 'Y', 'Z'),
    'XYZ_LENGTH': ('X', 'Y', 'Z'),
    'DIRECTION': ('X', 'Y', 'Z'),
    'VELOCITY': ('X', 'Y', 'Z'),
    'ACCELERATION': ('X', 'Y', 'Z'),
    'COLOR': ('R', 'G', 'B', 'A'),
    'COLOR_GAMMA': ('R', 'G', 'B', 'A'),
    'QUATERNION': ('W', 'X', 'Y', 'Z'),
    'EULER': ('X', 'Y', 'Z'),
    'AXISANGLE': ('W', 'X', 'Y', 'Z'),
    'LAYER': tuple(str(i) for i in range(32)),  # Layer は 0-31
    'LAYER_MEMBER': tuple(str(i) for i in range(32)),
}


def get_index_labels(subtype: str, array_length: int) -> tuple[str, ...]:
    """
    サブタイプに基づいてインデックスラベルを取得

    Args:
        subtype: プロパティのサブタイプ ('TRANSLATION', 'COLOR' など)
        array_length: 配列の長さ

    Returns:
        インデックスラベルのタプル
        例: ('X', 'Y', 'Z') for TRANSLATION
            ('R', 'G', 'B', 'A') for COLOR
            ('0', '1', '2', ...) for others

    Example:
        >>> get_index_labels('TRANSLATION', 3)
        ('X', 'Y', 'Z')
        >>> get_index_labels('COLOR', 4)
        ('R', 'G', 'B', 'A')
        >>> get_index_labels('NONE', 5)
        ('0', '1', '2', '3', '4')
    """
    labels = _SUBTYPE_INDEX_LABELS.get(subtype)
    if labels:
        # 配列長さに合わせてトリム（COLOR は RGB/RGBA 両方ある）
        return labels[:array_length] if len(labels) >= array_length else labels

    # デフォルト: 数字インデックス
    return tuple(str(i) for i in range(array_length))


def format_value(value: Any, precision: int = 2) -> str:
    """値を表示用にフォーマット"""
    if isinstance(value, float):
        return f"{value:.{precision}f}"
    elif isinstance(value, bool):
        return "On" if value else "Off"
    elif isinstance(value, (list, tuple)):
        return ", ".join(format_value(v, precision) for v in value)
    else:
        return str(value)
