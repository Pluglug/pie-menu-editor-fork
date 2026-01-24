# GPULayout - Blender UILayout 互換性 TODO

> 作成日: 2026-01-24
> ソース比較: Blender 5.0.1 (`rna_ui_api.cc`, `UI_interface_layout.hh`)
> 対象: `ui/gpu/` パッケージ

---

## 概要

このドキュメントは GPULayout を Blender の `bpy.types.UILayout` API に近づけるための TODO リストです。
3つのワークツリー（WT-A, WT-B, WT-C）で並列作業することを想定しています。

### ワークツリー構成

| WT | 担当領域 | 主なファイル |
|----|---------|-------------|
| **WT-A** | 新規ウィジェット実装 | `items/`, `widget_factory.py` |
| **WT-B** | prop() API 拡張 | `layout/props.py`, `rna_utils.py` |
| **WT-C** | コンテナ/レイアウト拡張 | `layout/containers.py`, `layout/flow.py` |

### 依存関係

```
WT-A (ウィジェット)
  │
  ├─→ MENU ウィジェット (独立)
  ├─→ TEXT ウィジェット (独立)
  └─→ VECTOR ウィジェット ←── WT-B: prop(index=) と連携

WT-B (prop API)
  │
  ├─→ index パラメータ (独立)
  ├─→ icon_only 実装 (独立)
  └─→ emboss/invert_checkbox (独立)

WT-C (コンテナ)
  │
  ├─→ heading パラメータ (独立)
  ├─→ column_flow (独立)
  └─→ use_property_split ←── WT-B: prop() と連携
```

---

## WT-A: 新規ウィジェット実装

### A-1: MenuButtonItem (MENU)

**優先度**: 🔴 高
**難易度**: 🟡 中
**依存**: なし

#### 概要
Enum プロパティをドロップダウンメニューで表示・編集するウィジェット。

#### Blender の動作
- クリックでドロップダウンを開く
- 現在値がボタンに表示される
- 動的 Enum にも対応

#### 実装仕様

**新規ファイル**: `ui/gpu/items/enum.py`

```python
@dataclass
class MenuButtonItem(LayoutItem):
    """Enum ドロップダウンボタン"""
    options: list[tuple[str, str, str]] = field(default_factory=list)  # (id, name, desc)
    value: str = ""
    text: str = ""
    icon: str = "NONE"
    on_change: Optional[Callable[[str], None]] = None

    # 状態
    hovered: bool = False
    pressed: bool = False
    dropdown_open: bool = False

    def get_value(self) -> str: ...
    def set_value(self, value: str) -> None: ...
    def get_display_text(self) -> str: ...
    def calc_size(self, style: GPULayoutStyle) -> tuple[float, float]: ...
    def draw(self, style: GPULayoutStyle) -> None: ...
```

**ドロップダウン UI**:
- 方法 A: GPU 描画でオーバーレイ（複雑）
- 方法 B: Blender の `bpy.ops.wm.call_menu` を呼び出す（シンプル）
- **推奨**: 方法 B でまず実装、後で方法 A に置き換え可能

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `items/enum.py` | 新規作成 |
| `items/__init__.py` | `MenuButtonItem` を re-export |
| `widget_factory.py` | `WidgetHint.MENU` に登録 |

#### 検証

```python
# Blender コンソール
from pie_menu_editor.ui.gpu.widget_factory import WidgetFactory, WidgetContext
from pie_menu_editor.ui.gpu.rna_utils import get_property_info

info = get_property_info(C.scene.render, "engine")
ctx = WidgetContext(text="Engine", enabled=True)
widget = WidgetFactory.create(info.widget_hint, info, "BLENDER_EEVEE_NEXT", ctx)
print(type(widget).__name__)  # MenuButtonItem
```

---

### A-2: VectorItem (VECTOR)

**優先度**: 🔴 高
**難易度**: 🟡 中
**依存**: WT-B の `prop(index=)` と連携推奨

#### 概要
XYZ などの数値配列を水平に並べた NumberItem で表示・編集。

#### Blender の動作
- 各要素が独立した数値フィールド
- ラベル（X, Y, Z）が表示される
- `expand=True` で個別表示

#### 実装仕様

**新規ファイル**: `ui/gpu/items/vector.py`

```python
@dataclass
class VectorItem(LayoutItem):
    """ベクトル入力 (XYZ 等)"""
    value: tuple[float, ...] = (0.0, 0.0, 0.0)
    labels: tuple[str, ...] = ("X", "Y", "Z")
    min_val: float = -1e9
    max_val: float = 1e9
    step: float = 0.01
    precision: int = 3
    text: str = ""
    on_change: Optional[Callable[[tuple[float, ...]], None]] = None

    # 内部: 各要素の NumberItem
    _items: list[NumberItem] = field(default_factory=list)

    def get_value(self) -> tuple[float, ...]: ...
    def set_value(self, value: tuple[float, ...]) -> None: ...
    def set_element(self, index: int, value: float) -> None: ...
```

**レイアウト**:
```
┌─────────────────────────────────────────────┐
│ Location   [X: 1.00] [Y: 2.00] [Z: 3.00]   │
└─────────────────────────────────────────────┘
```

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `items/vector.py` | 新規作成 |
| `items/__init__.py` | `VectorItem` を re-export |
| `widget_factory.py` | `WidgetHint.VECTOR` に登録 |

---

### A-3: TextInputItem (TEXT)

**優先度**: 🟡 中
**難易度**: 🔴 高
**依存**: なし

#### 概要
文字列を入力・編集するテキストフィールド。

#### Blender の動作
- クリックで編集モード
- カーソル表示・移動
- 選択・コピペ
- Escape でキャンセル、Enter で確定
- IME の変換中表示・候補位置の追従（C 実装）

#### GPULayout (Python) の制約
- Python からは `WM_IME_COMPOSITE_*` や `wmIMEData` にアクセスできない
- `event.type == 'TEXTINPUT'` / `event.unicode` による確定入力のみ対応可能
- IME の変換中下線や候補ウィンドウ位置追従は C 側の API 追加が必要

#### 実装仕様

**新規ファイル**: `ui/gpu/items/text_input.py`

```python
@dataclass
class TextInputItem(LayoutItem):
    """テキスト入力フィールド"""
    value: str = ""
    placeholder: str = ""
    text: str = ""  # ラベル
    max_length: int = 0  # 0 = 無制限
    on_change: Optional[Callable[[str], None]] = None
    on_confirm: Optional[Callable[[str], None]] = None

    # 編集状態
    editing: bool = False
    cursor_pos: int = 0
    selection_start: int = -1
    selection_end: int = -1

    # 表示
    scroll_offset: float = 0.0  # 長いテキストのスクロール

    def get_value(self) -> str: ...
    def set_value(self, value: str) -> None: ...
    def start_editing(self) -> None: ...
    def stop_editing(self, confirm: bool = True) -> None: ...
    def handle_key(self, event: Event) -> bool: ...
```

**必要な機能**:
1. テキスト描画とカーソル
2. キーボード入力処理（文字、Backspace、Delete、矢印）
3. クリップボード（Ctrl+C/V）
4. 選択範囲の描画と操作

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `items/text_input.py` | 新規作成 |
| `items/__init__.py` | `TextInputItem` を re-export |
| `widget_factory.py` | `WidgetHint.TEXT` に登録 |

---

## WT-B: prop() API 拡張

### B-1: index パラメータ

**優先度**: 🔴 高
**難易度**: 🟢 低
**依存**: WT-A の VectorItem と連携推奨

#### Blender API

```python
# Blender UILayout
layout.prop(obj, "location", index=0)  # X のみ
layout.prop(obj, "location", index=1)  # Y のみ
```

#### 現在の GPULayout

```python
# index パラメータなし
def prop(self, data, property, *, text="", icon="NONE",
         expand=False, slider=False, toggle=-1, icon_only=False, key="")
```

#### 実装仕様

**変更ファイル**: `layout/props.py`

```python
def prop(self, data: Any, property: str, *,
         text: str = "",
         icon: str = "NONE",
         expand: bool = False,
         slider: bool = False,
         toggle: int = -1,
         icon_only: bool = False,
         index: int = -1,  # 追加: -1 = 全要素、0+ = 特定要素
         key: str = "") -> Optional[LayoutItem]:
```

**ロジック変更**:
```python
# index が指定された場合
if index >= 0 and info.is_array:
    # 配列の特定要素のみ取得
    full_value = get_property_value(raw_data, property)
    current_value = full_value[index] if index < len(full_value) else 0

    # NumberItem または SliderItem を生成（VECTOR ではなく）
    hint = WidgetHint.SLIDER if slider else WidgetHint.NUMBER

    # set_value も index 対応
    def set_indexed_value(context, value):
        full = list(getattr(resolver(context), property))
        full[index] = value
        setattr(resolver(context), property, full)
```

---

### B-2: icon_only 実装

**優先度**: 🟡 中
**難易度**: 🟢 低
**依存**: なし

#### 現状
パラメータは受け取るが、ウィジェット生成時に使われていない。

#### 実装仕様

**変更ファイル**: `widget_factory.py`

`WidgetContext` に `icon_only` を追加:

```python
@dataclass
class WidgetContext:
    text: str = ""
    icon: str = "NONE"
    icon_only: bool = False  # 追加
    # ...
```

各 creator で `icon_only=True` の場合はテキストを非表示:

```python
@staticmethod
def _create_toggle(info, value, ctx):
    return ToggleItem(
        text="" if ctx.icon_only else ctx.text,  # icon_only 対応
        icon=ctx.icon,
        # ...
    )
```

---

### B-3: emboss パラメータ

**優先度**: 🟡 中
**難易度**: 🟡 中
**依存**: なし

#### Blender の動作
- `emboss=True`: 通常のボタン背景
- `emboss=False`: 背景なし（`ITEM_R_NO_BG`）

#### 実装仕様

**変更ファイル**: `widget_factory.py`, `items/buttons.py`

```python
# WidgetContext に追加
@dataclass
class WidgetContext:
    emboss: bool = True  # 追加

# ButtonItem 等に追加
@dataclass
class ButtonItem(LayoutItem):
    emboss: bool = True  # 追加

    def draw(self, style):
        if self.emboss:
            # 通常の背景描画
        else:
            # 背景なし
```

---

### B-4: invert_checkbox

**優先度**: 🟢 低
**難易度**: 🟢 低
**依存**: なし

#### Blender の動作
チェックボックスの表示を反転（checked ↔ unchecked）。

#### 実装仕様

```python
# WidgetContext に追加
invert_checkbox: bool = False

# CheckboxItem の描画で
display_value = not self.value if invert else self.value
```

---

### B-5: placeholder パラメータ

**優先度**: 🟢 低
**難易度**: 🟢 低
**依存**: WT-A の TextInputItem

#### Blender の動作
テキスト入力フィールドが空の時に表示されるプレースホルダー。

---

## WT-C: コンテナ/レイアウト拡張

### C-1: row/column の heading パラメータ

**優先度**: 🟡 中
**難易度**: 🟡 中
**依存**: C-3 (use_property_split) と連携

#### Blender API

```python
# Blender UILayout
row = layout.row(heading="Options")
col = layout.column(heading="Settings")
```

#### 実装仕様

**変更ファイル**: `layout/containers.py`

```python
def row(self, align: bool = False, heading: str = "") -> GPULayout:
    child = GPULayout(...)
    if heading:
        # heading ラベルを追加
        child._heading = heading
        # use_property_split 時は左カラムに表示
    return child
```

**描画時の処理**:
```
use_property_split=False:
┌─────────────────────────────────────┐
│ Options:  [Widget] [Widget]         │
└─────────────────────────────────────┘

use_property_split=True:
┌──────────────┬──────────────────────┐
│ Options      │ [Widget] [Widget]    │
└──────────────┴──────────────────────┘
```

---

### C-2: column_flow()

**優先度**: 🟡 中
**難易度**: 🟡 中
**依存**: なし

#### Blender API

```python
# Blender UILayout
flow = layout.column_flow(columns=2, align=True)
flow.label(text="A")
flow.label(text="B")
flow.label(text="C")
flow.label(text="D")
# 結果:
# A  B
# C  D
```

#### 実装仕様

**変更ファイル**: `layout/containers.py`

```python
def column_flow(self, columns: int = 0, align: bool = False) -> GPULayout:
    """
    複数列フローレイアウト

    Args:
        columns: 列数（0 = 自動）
        align: アイテム間のスペースをなくす
    """
    child = GPULayout(...)
    child._is_column_flow = True
    child._flow_columns = columns
    return child
```

**flow.py の変更**:
- `_arrange_column_flow()` メソッドを追加
- アイテムを列数で折り返し

---

### C-3: use_property_split 実装

**優先度**: 🔴 高
**難易度**: 🔴 高
**依存**: C-1 (heading) と連携

#### Blender の動作
- `use_property_split=True`: ラベルとウィジェットを分離
- ラベルは左カラム（約40%）、ウィジェットは右カラム

```
use_property_split=False:
┌─────────────────────────────────────┐
│ Location X: [1.00]                  │
│ Location Y: [2.00]                  │
└─────────────────────────────────────┘

use_property_split=True:
┌──────────────┬──────────────────────┐
│ Location X   │ [1.00]               │
│ Location Y   │ [2.00]               │
└──────────────┴──────────────────────┘
```

#### 実装仕様

**変更ファイル**: `layout/props.py`, `layout/flow.py`

```python
def prop(self, data, property, ...):
    if self.use_property_split:
        # 2カラムレイアウトで描画
        split = self.split(factor=0.4)
        col1 = split.column()
        col1.label(text=display_text)
        col2 = split.column()
        # ウィジェットは col2 に追加（ラベルなし）
        item = self._create_prop_widget(..., text="")
        col2._add_item(item)
    else:
        # 通常描画
        item = self._create_prop_widget(..., text=display_text)
        self._add_item(item)
```

---

### C-4: grid_flow()

**優先度**: 🟢 低
**難易度**: 🔴 高
**依存**: なし

#### Blender API

```python
grid = layout.grid_flow(
    row_major=True,
    columns=3,
    even_columns=True,
    even_rows=True,
    align=True
)
```

#### 実装仕様

後回し。column_flow() の拡張として実装可能。

---

## 進捗トラッキング

### WT-A: ウィジェット

| ID | タスク | 状態 | 担当 |
|----|-------|------|------|
| A-1 | MenuButtonItem | ⬜ TODO | |
| A-2 | VectorItem | ⬜ TODO | |
| A-3 | TextInputItem | ⬜ TODO | |

### WT-B: prop() API

| ID | タスク | 状態 | 担当 |
|----|-------|------|------|
| B-1 | index パラメータ | ⬜ TODO | |
| B-2 | icon_only 実装 | ⬜ TODO | |
| B-3 | emboss パラメータ | ⬜ TODO | |
| B-4 | invert_checkbox | ⬜ TODO | |
| B-5 | placeholder | ⬜ TODO | |

### WT-C: コンテナ

| ID | タスク | 状態 | 担当 |
|----|-------|------|------|
| C-1 | heading パラメータ | ⬜ TODO | |
| C-2 | column_flow() | ⬜ TODO | |
| C-3 | use_property_split | ⬜ TODO | |
| C-4 | grid_flow() | ⬜ TODO | |

---

## 実装順序の推奨

### Phase 1: 基本機能（独立して実装可能）
1. **A-1: MenuButtonItem** - 最も使用頻度が高い
2. **B-1: index** - VectorItem 実装の前準備
3. **B-2: icon_only** - 簡単、すぐ終わる

### Phase 2: 連携機能
4. **A-2: VectorItem** - B-1 と連携
5. **C-1: heading** - C-3 の前準備
6. **C-2: column_flow** - 独立

### Phase 3: 複雑な機能
7. **C-3: use_property_split** - C-1 必須
8. **A-3: TextInputItem** - 最も複雑
9. **B-3, B-4, B-5** - 優先度低め

---

## 参照

- Blender ソース: `source/blender/makesrna/intern/rna_ui_api.cc`
- Blender ヘッダー: `source/blender/editors/include/UI_interface_layout.hh`
- GPULayout: `ui/gpu/layout/`
- WidgetFactory: `ui/gpu/widget_factory.py`
