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


UI_PRECISION_FLOAT_MAX = 6
UI_PRECISION_FLOAT_SCALE = 0.01


@dataclass(frozen=True)
class _PreferredUnitDef:
    scalar: float
    bias: float
    suffix: str
    no_space: bool = False


_SUBTYPE_UNIT_CATEGORY: dict[str, str] = {
    "ANGLE": "ROTATION",
    "TRANSLATION": "LENGTH",
    "DISTANCE": "LENGTH",
    "DISTANCE_DIAMETER": "LENGTH",
    "DISTANCE_CAMERA": "CAMERA",
    "LENGTH": "LENGTH",
    "XYZ_LENGTH": "LENGTH",
    "VELOCITY": "VELOCITY",
    "ACCELERATION": "ACCELERATION",
    "AREA": "AREA",
    "VOLUME": "VOLUME",
    "MASS": "MASS",
    "CAMERA": "CAMERA",
    "POWER": "POWER",
    "TEMPERATURE": "TEMPERATURE",
    "COLOR_TEMPERATURE": "COLOR_TEMPERATURE",
    "WAVELENGTH": "WAVELENGTH",
    "FREQUENCY": "FREQUENCY",
    "TIME": "TIME",
    "TIME_ABSOLUTE": "TIME_ABSOLUTE",
    "ROTATION": "ROTATION",
    "ANGLE": "ROTATION",
    "EULER": "ROTATION",
    "AXISANGLE": "ROTATION",
}


_PREFERRED_LENGTH_UNITS: dict[str, _PreferredUnitDef] = {
    "KILOMETERS": _PreferredUnitDef(1000.0, 0.0, "km"),
    "HECTOMETERS": _PreferredUnitDef(100.0, 0.0, "hm"),
    "DEKAMETERS": _PreferredUnitDef(10.0, 0.0, "dam"),
    "METERS": _PreferredUnitDef(1.0, 0.0, "m"),
    "DECIMETERS": _PreferredUnitDef(0.1, 0.0, "dm"),
    "CENTIMETERS": _PreferredUnitDef(0.01, 0.0, "cm"),
    "MILLIMETERS": _PreferredUnitDef(0.001, 0.0, "mm"),
    "MICROMETERS": _PreferredUnitDef(1e-6, 0.0, "um"),
    "NANOMETERS": _PreferredUnitDef(1e-9, 0.0, "nm"),
    "PICOMETERS": _PreferredUnitDef(1e-12, 0.0, "pm"),
    "MILES": _PreferredUnitDef(1609.344, 0.0, "mi"),
    "FURLONGS": _PreferredUnitDef(201.168, 0.0, "fur"),
    "CHAINS": _PreferredUnitDef(20.1168, 0.0, "ch"),
    "YARDS": _PreferredUnitDef(0.9144, 0.0, "yd"),
    "FEET": _PreferredUnitDef(0.3048, 0.0, "ft"),
    "INCHES": _PreferredUnitDef(0.0254, 0.0, "in"),
    "THOU": _PreferredUnitDef(0.0000254, 0.0, "thou"),
}

_PREFERRED_MASS_UNITS: dict[str, _PreferredUnitDef] = {
    "TONNES": _PreferredUnitDef(1000.0, 0.0, "t"),
    "QUINTALS": _PreferredUnitDef(100.0, 0.0, "ql"),
    "KILOGRAMS": _PreferredUnitDef(1.0, 0.0, "kg"),
    "HECTOGRAMS": _PreferredUnitDef(0.1, 0.0, "hg"),
    "DEKAGRAMS": _PreferredUnitDef(0.01, 0.0, "dag"),
    "GRAMS": _PreferredUnitDef(0.001, 0.0, "g"),
    "MILLIGRAMS": _PreferredUnitDef(1e-6, 0.0, "mg"),
    "CENTUM_WEIGHTS": _PreferredUnitDef(45.359237, 0.0, "cwt"),
    "STONES": _PreferredUnitDef(6.35029318, 0.0, "st"),
    "POUNDS": _PreferredUnitDef(0.45359237, 0.0, "lb"),
    "OUNCES": _PreferredUnitDef(0.028349523125, 0.0, "oz"),
}

_PREFERRED_TIME_UNITS: dict[str, _PreferredUnitDef] = {
    "DAYS": _PreferredUnitDef(86400.0, 0.0, "d"),
    "HOURS": _PreferredUnitDef(3600.0, 0.0, "h"),
    "MINUTES": _PreferredUnitDef(60.0, 0.0, "min"),
    "SECONDS": _PreferredUnitDef(1.0, 0.0, "s"),
    "MILLISECONDS": _PreferredUnitDef(0.001, 0.0, "ms"),
    "MICROSECONDS": _PreferredUnitDef(0.000001, 0.0, "us"),
}

_PREFERRED_TEMPERATURE_UNITS: dict[str, _PreferredUnitDef] = {
    "KELVIN": _PreferredUnitDef(1.0, 0.0, "K", no_space=True),
    "CELSIUS": _PreferredUnitDef(1.0, 273.15, "C", no_space=True),
    "FAHRENHEIT": _PreferredUnitDef(0.555555555555, 459.67, "F", no_space=True),
}


def _get_preferred_unit(unit_settings, unit_category: str | None) -> Optional[_PreferredUnitDef]:
    if unit_settings is None or unit_category is None:
        return None

    unit_id = None
    if unit_category == "LENGTH":
        unit_id = getattr(unit_settings, "length_unit", None)
    elif unit_category == "MASS":
        unit_id = getattr(unit_settings, "mass_unit", None)
    elif unit_category in {"TIME", "TIME_ABSOLUTE"}:
        unit_id = getattr(unit_settings, "time_unit", None)
    elif unit_category in {"TEMPERATURE", "COLOR_TEMPERATURE"}:
        unit_id = getattr(unit_settings, "temperature_unit", None)

    if not isinstance(unit_id, str) or unit_id == "ADAPTIVE":
        return None

    if unit_category == "LENGTH":
        return _PREFERRED_LENGTH_UNITS.get(unit_id)
    if unit_category == "MASS":
        return _PREFERRED_MASS_UNITS.get(unit_id)
    if unit_category in {"TIME", "TIME_ABSOLUTE"}:
        return _PREFERRED_TIME_UNITS.get(unit_id)
    if unit_category in {"TEMPERATURE", "COLOR_TEMPERATURE"}:
        return _PREFERRED_TEMPERATURE_UNITS.get(unit_id)
    return None


def _format_preferred_unit(value: float, prec: int, unit_def: _PreferredUnitDef) -> str:
    value_conv = (value / unit_def.scalar) - unit_def.bias
    text = f"{value_conv:.{prec}f}"
    if prec > 0:
        text = text.rstrip("0").rstrip(".")
    if unit_def.no_space:
        return f"{text}{unit_def.suffix}"
    return f"{text} {unit_def.suffix}"


def _integer_digits(value: float) -> int:
    if value == 0.0:
        return 0
    from math import floor, log10, fabs
    return int(floor(log10(fabs(value)))) + 1


def _calc_float_precision(prec: int, value: float) -> int:
    from math import fabs, pow

    pow10_neg = [1e0, 1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6]
    max_pow = 10000000.0

    value = fabs(value)
    if (value < pow10_neg[prec]) and (value > (1.0 / max_pow)):
        value_i = int(round(value * max_pow))
        if value_i != 0:
            prec_span = 3
            test_prec = 0
            prec_min = -1
            dec_flag = 0
            i = UI_PRECISION_FLOAT_MAX
            while i and value_i:
                if value_i % 10:
                    dec_flag |= 1 << i
                    prec_min = i
                value_i //= 10
                i -= 1

            test_prec = prec_min
            dec_flag = (dec_flag >> (prec_min + 1)) & ((1 << prec_span) - 1)
            while dec_flag:
                test_prec += 1
                dec_flag >>= 1
            prec = max(test_prec, prec)

    return max(0, min(UI_PRECISION_FLOAT_MAX, prec))


def _unit_settings_from_context():
    try:
        return bpy.context.scene.unit_settings if bpy.context and bpy.context.scene else None
    except Exception:
        return None


def _should_use_units(unit_settings, unit_category: str | None) -> bool:
    if unit_category is None or unit_category == "NONE":
        return False
    if unit_category == "TIME":
        return False
    if unit_settings is None:
        return False
    if unit_settings.system == "NONE":
        return unit_category in {"ROTATION", "TIME_ABSOLUTE"}
    if unit_category == "ROTATION" and unit_settings.system_rotation == "RADIANS":
        return False
    return True


def _scale_value_for_units(value: float, unit_settings, unit_category: str) -> float:
    if unit_settings is None or unit_settings.system == "NONE":
        return value
    scale = float(unit_settings.scale_length) if getattr(unit_settings, "scale_length", 0.0) else 1.0
    if unit_category in {"LENGTH", "VELOCITY", "ACCELERATION"}:
        return value * scale
    if unit_category in {"AREA", "POWER"}:
        return value * (scale ** 2)
    if unit_category in {"VOLUME", "MASS"}:
        return value * (scale ** 3)
    # CAMERA/WAVELENGTH/ROTATION/TIME/etc. do not scale by scene unit scale.
    return value


def _calc_display_precision(value: float,
                            precision: int,
                            step: float,
                            unit_settings,
                            unit_category: str | None,
                            max_value: Optional[float]) -> int:
    from math import floor

    # Hide fraction when integer value and integer step (unitless or time).
    if unit_category in {None, "NONE", "TIME"}:
        step_scaled = step * UI_PRECISION_FLOAT_SCALE
        if floor(value) == value and floor(step_scaled) == step_scaled:
            return 0

    prec = precision
    if prec == -1:
        if max_value is not None and max_value < 10.001:
            prec = 3
        else:
            prec = 2
    else:
        prec = max(0, min(UI_PRECISION_FLOAT_MAX, prec))

    if unit_category == "ROTATION" and unit_settings and unit_settings.system_rotation == "RADIANS":
        if prec < 5:
            prec = 5

    return _calc_float_precision(prec, value)


def format_numeric_value(value: float,
                         subtype: str = "NONE",
                         precision: int = 2,
                         step: float = 1.0,
                         max_value: Optional[float] = None) -> str:
    """サブタイプに応じて数値を Blender 互換でフォーマット。"""
    subtype = (subtype or "NONE").upper()
    value = float(value) + 0.0  # normalize negative zero

    unit_category = _SUBTYPE_UNIT_CATEGORY.get(subtype)
    unit_settings = _unit_settings_from_context()
    prec = _calc_display_precision(value, precision, step, unit_settings, unit_category, max_value)

    # Special subtypes
    if subtype == "PERCENTAGE":
        return f"{value:.{prec}f}%"
    if subtype in {"PIXEL", "PIXEL_DIAMETER"}:
        return f"{value:.{prec}f} px"
    if subtype == "FACTOR":
        try:
            display_type = bpy.context.preferences.system.factor_display_type
        except Exception:
            display_type = "FACTOR"
        if display_type == "PERCENTAGE":
            return f"{value * 100:.{max(0, prec - 2)}f}"
        return f"{value:.{prec}f}"

    # Units
    if _should_use_units(unit_settings, unit_category):
        preferred_unit = _get_preferred_unit(unit_settings, unit_category)
        value_scaled = _scale_value_for_units(value, unit_settings, unit_category)
        if preferred_unit:
            return _format_preferred_unit(value_scaled, prec, preferred_unit)
        unit_system = unit_settings.system
        split_unit = bool(getattr(unit_settings, "use_separate", False))
        try:
            from bpy.utils import units
            return units.to_string(unit_system, unit_category, value_scaled,
                                   precision=prec, split_unit=split_unit)
        except Exception:
            pass

    # Unit-less fallback (apply integer digit adjustment like Blender).
    int_digits = _integer_digits(value)
    prec_adj = max(0, min(UI_PRECISION_FLOAT_MAX, prec - int_digits))
    return f"{value:.{prec_adj}f}"
