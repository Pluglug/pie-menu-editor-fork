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

### A-1: MenuButtonItem (MENU) ✅ 完了

**優先度**: 🔴 高
**難易度**: 🟡 中
**依存**: なし
**完了日**: 2026-01-24

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

### A-2: VectorItem (VECTOR) ✅ 完了

**優先度**: 🔴 高
**難易度**: 🟡 中
**依存**: WT-B の `prop(index=)` と連携推奨
**完了日**: 2026-01-25

#### 概要
XYZ などの数値配列を水平/垂直に並べた NumberItem で表示・編集。

#### 実装済み機能

- **水平レイアウト** (デフォルト): `[X: 1.00] [Y: 2.00] [Z: 3.00]`
- **垂直レイアウト** (`vertical=True`): 各要素が縦に並ぶ
- **自動ラベル**: サブタイプに応じて X/Y/Z, R/G/B/A, W/X/Y/Z を自動取得
- **角丸連結**: `align=True` スタイルで端のみ角丸
- **値同期**: 各要素の変更が全体コールバックに連携
- **子ウィジェット**: `get_child_items()` でイベント処理用の NumberItem を返す

#### 今後の拡張予定

| 機能 | 説明 | 優先度 |
|------|------|--------|
| `expand=True` 連携 | prop() の expand パラメータで垂直表示に切り替え | 🟡 中 |
| `slider=True` 連携 | 各要素を SliderItem で表示 | 🟡 中 |
| ロックアイコン | 個別要素を固定するボタン | 🟢 低 |
| 連動編集 | Shift+ドラッグで全要素を同時変更 | 🟢 低 |

#### 使用例

```python
from pie_menu_editor.ui.gpu import GPULayout

layout = GPULayout(x=100, y=500, width=400)

# 水平表示（デフォルト）
layout.prop(C.object, "location")
layout.prop(C.object, "scale", text="Scale")

# index 指定で個別要素（NumberItem として表示）
layout.prop(C.object, "location", index=0, text="X Only")
```

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `items/vector.py` | 新規作成 (253行) |
| `items/__init__.py` | `VectorItem` を re-export |
| `widget_factory.py` | `WidgetContext.vertical` 追加、`_create_vector` 追加 |
| `layout/props.py` | `Direction` import、vertical フラグ対応 |

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

### B-1: index パラメータ ✅ 完了

**優先度**: 🔴 高
**難易度**: 🟢 低
**依存**: WT-A の VectorItem と連携推奨
**完了日**: 2026-01-24

#### Blender API

```python
# Blender UILayout
layout.prop(obj, "location", index=0)  # X のみ
layout.prop(obj, "location", index=1)  # Y のみ
```

#### 現状（修正前）

```python
# index パラメータなし
def prop(self, data, property, *, text="", icon="NONE",
         expand=False, slider=False, toggle=-1, icon_only=False, key="")
```

#### 実装結果 ✅
- `prop(..., index=)` を追加（`index=-1` は従来通り全要素）
- `index>=0` かつ配列の場合は NumberItem/SliderItem を生成
- `set_value` も index 位置を更新するように対応

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

### B-2: icon_only 実装 ✅ 完了

**優先度**: 🟡 中
**難易度**: 🟢 低
**依存**: なし
**完了日**: 2026-01-25

#### 現状（修正前）
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

#### 実装結果 ✅
- `WidgetContext.icon_only` を追加し、各 creator でテキスト非表示に対応
- Boolean + icon_only + icon では ToggleItem を使用（D-1 の対応を参照）

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

### C-1: row/column の heading パラメータ ✅ 完了

**優先度**: 🟡 中
**難易度**: 🟡 中
**依存**: C-3 (use_property_split) と連携
**完了日**: 2026-01-25

#### Blender API

```python
# Blender UILayout
row = layout.row(heading="Options")
col = layout.column(heading="Settings")
```

#### 実装済み機能

- **遅延挿入**: heading は最初のアイテム追加時に自動挿入される
- **一度だけ処理**: 挿入後 `_heading` はクリアされ、以降のアイテムでは処理されない
- **use_property_split 対応**: True の場合、split を作成し左カラムに右寄せでラベル配置
- **空コンテナ対応**: アイテムが追加されない場合、heading は表示されない（Blender と同じ）

**描画結果**:
```
use_property_split=False:
┌─────────────────────────────────────┐
│ Options  [Widget] [Widget]          │
└─────────────────────────────────────┘

use_property_split=True:
┌──────────────┬──────────────────────┐
│      Options │                      │
├──────────────┼──────────────────────┤
│        Prop1 │ [Widget]             │
│        Prop2 │ [Widget]             │
└──────────────┴──────────────────────┘
```

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `layout/core.py` | `_heading: str = ""` 属性を追加 |
| `layout/containers.py` | `row()`, `column()` に `heading` パラメータ追加 |
| `layout/utils.py` | `_insert_heading_label()` 追加、`_add_item()` を更新 |

#### 使用例

```python
from pie_menu_editor.ui.gpu import GPULayout

layout = GPULayout(x=100, y=500, width=300)

# 基本的な使い方
row = layout.row(heading="Options")
row.label(text="Item 1")
row.label(text="Item 2")

# use_property_split と組み合わせ
layout.use_property_split = True
col = layout.column(heading="Transform")
col.prop(C.object, "location")
col.prop(C.object, "rotation_euler")
```

---

### C-2: column_flow() ✅ 完了

**優先度**: 🟡 中
**難易度**: 🟡 中
**依存**: なし
**完了日**: 2026-01-25

#### Blender API

```python
# Blender UILayout
flow = layout.column_flow(columns=2, align=True)
flow.label(text="A")
flow.label(text="B")
flow.label(text="C")
flow.label(text="D")
# 結果:
# A  C
# B  D
```

#### 実装済み機能

- **累積高さベースの分配**: Blender `LayoutItemFlow::estimate_impl()` に準拠
- **自動列数計算**: `columns=0` で利用可能幅 / 最大アイテム幅から自動決定
- **高さ閾値による列切り替え**: 固定行数ではなく、合計高さ / 列数で閾値を計算
- **align 対応**: `align=True` でアイテム間・列間のスペースを削除
- **子レイアウト対応**: row/column を含む場合も正常動作

**動作の詳細**:
```
columns=2:
┌─────────┬─────────┐
│ Item A  │ Item C  │
│ Item B  │ Item D  │
│         │ Item E  │
└─────────┴─────────┘

columns=0 (自動):
列数は利用可能幅とアイテム幅から自動計算
```

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `layout/core.py` | `_is_column_flow`, `_flow_columns`, `_flow_totcol` 属性を追加 |
| `layout/containers.py` | `column_flow()` メソッドを追加 |
| `layout/flow.py` | `_measure_column_flow()`, `_arrange_column_flow()` を追加 |

#### 使用例

```python
from pie_menu_editor.ui.gpu import GPULayout

layout = GPULayout(x=100, y=500, width=300)

# 2列フローレイアウト
flow = layout.column_flow(columns=2)
for i in range(6):
    flow.label(text=f"Item {chr(65+i)}")

# 自動列数
flow2 = layout.column_flow(columns=0)
for i in range(8):
    flow2.label(text=f"Long Item {i}")

layout.layout()
layout.draw()
```

---

### C-3: use_property_split 実装 ✅ 完了

**優先度**: 🔴 高
**難易度**: 🔴 高
**依存**: C-1 (heading) と連携
**完了日**: 2026-01-25

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

#### 実装済み機能

- **split(factor=0.4)** で 40/60 のカラム分割
- **左カラム**: ラベル（右寄せ `alignment=RIGHT`）
- **右カラム**: ウィジェット（ラベルなし）
- **子レイアウト継承**: `row()`, `column()`, `split()` で `use_property_split` を自動継承
- **再帰防止**: split 内の column では `use_property_split=False` に設定
- **例外処理**: `icon_only=True` や `is_readonly` の場合は通常描画にフォールスルー

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `widget_factory.py` | `WidgetContext.use_property_split` 追加 |
| `layout/containers.py` | `row()`, `column()`, `split()` に継承追加 |
| `layout/props.py` | `_prop_with_split()` 追加、`prop()` に分岐追加 |

#### 使用例

```python
from pie_menu_editor.ui.gpu import GPULayout

layout = GPULayout(x=100, y=500, width=300)
layout.use_property_split = True

layout.prop(C.scene.render, "resolution_x")
layout.prop(C.scene.render, "resolution_y")
layout.prop(C.object, "location")

layout.layout()
layout.draw()
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

| ID | タスク | 状態 | 完了日 |
|----|-------|------|------|
| A-1 | MenuButtonItem | ✅ 完了 | 2026-01-24 |
| A-2 | VectorItem | ✅ 完了 | 2026-01-25 |
| A-3 | TextInputItem | ⬜ TODO | |

### WT-B: prop() API

| ID | タスク | 状態 | 完了日 |
|----|-------|------|------|
| B-1 | index パラメータ | ✅ 完了 | 2026-01-24 |
| B-2 | icon_only 実装 | ✅ 完了 | 2026-01-25 |
| B-3 | emboss パラメータ | ⬜ TODO | |
| B-4 | invert_checkbox | ⬜ TODO | |
| B-5 | placeholder | ⬜ TODO | |

### WT-C: コンテナ

| ID | タスク | 状態 | 完了日 |
|----|-------|------|------|
| C-1 | heading パラメータ | ✅ 完了 | 2026-01-25 |
| C-2 | column_flow() | ✅ 完了 | 2026-01-25 |
| C-3 | use_property_split | ✅ 完了 | 2026-01-25 |
| C-4 | grid_flow() | ⬜ TODO | |

---

## 実装順序の推奨

### Phase 1: 基本機能（独立して実装可能）
1. ~~**A-1: MenuButtonItem** - 最も使用頻度が高い~~ ✅ 完了
2. ~~**B-1: index** - VectorItem 実装の前準備~~ ✅ 完了
3. ~~**B-2: icon_only** - 簡単、すぐ終わる~~ ✅ 完了

### Phase 2: 連携機能
4. ~~**A-2: VectorItem** - B-1 と連携~~ ✅ 完了
5. ~~**C-1: heading** - C-3 と連携~~ ✅ 完了
6. ~~**C-2: column_flow** - 独立~~ ✅ 完了

### Phase 3: 複雑な機能
7. ~~**C-3: use_property_split** - C-1 と連携~~ ✅ 完了
8. **A-3: TextInputItem** - 最も複雑
9. **B-3, B-4, B-5** - 優先度低め

---

## 比較テストで発見された課題（2026-01-25）

> テスト方法: `DEMO_OT_blender_compat_gpulayout`（GPULayout）と `DEMO_PT_blender_compat_reference`（N-Panel）を並べて比較

### D-1: CheckboxItem / ToggleItem の icon_only 対応 ✅ 完了

**優先度**: 🔴 高
**関連**: B-2 (icon_only 実装)
**完了日**: 2026-01-25

#### 現象（修正前）
- `icon_only=True` でもテキストが表示される
- Blender ではアイコンボタンとして描画されるが、GPULayout では単純なチェックボックスのまま

#### Blender の動作（スクリーンショットより）
```
┌──────────────────────────────────────────────────────────┐
│ 3. icon_only (B-2)                                        │
│ ┌───┐ ┌─────────────────────────────┐ ┌───┐ ┌───┐ ┌───┐  │
│ │ 🖥 │ │        Normal               │ │ 🖥 │ │ 📷 │ │ ➡ │  │
│ └───┘ └─────────────────────────────┘ └───┘ └───┘ └───┘  │
└──────────────────────────────────────────────────────────┘
※ icon_only=True のボタンはアイコンのみの正方形ボタンになる
```

#### GPULayout の現状（修正前）
```
┌──────────────────────────────────────────────────────────┐
│ 3. icon_only (B-2)                                        │
│ ☐Normal  ☐  ☐  ☐                                         │
└──────────────────────────────────────────────────────────┘
※ チェックボックス形式のまま、icon_only が効いていない
```

#### GPULayout の現状（修正後）
- `icon_only=True` のボタンはアイコンのみの正方形ボタンで描画
- テキストありの場合は「アイコン左・テキスト中央」に配置

#### 調査項目
- [x] `uiItemFullR()` での `icon_only` フラグの処理確認（`UI_ITEM_R_ICON_ONLY`）
- [x] Boolean プロパティの描画先ウィジェット決定ロジック（`ui_item_rna_size()`, `ui_item_add_but()`）
- [x] `icon_only=True` 時のウィジェットサイズ計算（`UI_UNIT_X` ベースの正方形）
- [x] CheckboxItem と ToggleItem の描画区別（Blender の `UI_BUT_CHECKBOX` vs `UI_BUT_TOGGLE`）

#### 調査結果（2026-01-25）

**Blender ソース分析** (`interface_utils.cc:55-105`):

```cpp
// uiDefAutoButR() での Boolean 処理
case PROP_BOOLEAN: {
  if (icon && name && name->is_empty()) {
    // icon あり + name 空 → IconToggle（正方形ボタン）
    but = uiDefIconButR_prop(block, ButtonType::IconToggle, icon, ...);
  }
  else if (icon) {
    // icon あり + name あり → IconToggle（アイコン+テキスト）
    but = uiDefIconTextButR_prop(block, ButtonType::IconToggle, ...);
  }
  // icon なし → Checkbox
}
```

**ポイント**:
1. `icon_only=True` の場合、`name` は空文字列になる（`interface_layout.cc:1223`）
2. `icon` + `name.is_empty()` → `ButtonType::IconToggle`（正方形アイコンボタン）
3. サイズは `UI_UNIT_X` ベース（`ui_item_rna_size` で `icon_only` 時は `ICON_BLANK1` 幅）

#### 実装結果 ✅

**1. ToggleItem に icon_only フィールドを追加**:
- `icon_only: bool = False` フィールド追加
- `__post_init__()` で `icon_only=True` のとき `sizing.is_fixed = True` を設定
- `calc_size()` で `icon_only=True` のとき正方形 `(item_height, item_height)` を返す

**2. WidgetFactory での分岐**:
- `_create_checkbox()`: `icon_only=True` かつ `icon != "NONE"` の場合は ToggleItem を返す
- `_create_toggle()`: `icon_only` フラグを ToggleItem に渡す

**3. アイコン/テキスト配置の Blender 準拠化**:
- **icon_only または text=""**: アイコンを中央揃え（スケール 85% でパディング確保）
- **テキストあり**: アイコンは左端、テキストは残り領域で中央揃え

**4. split レイアウト対応**:
- `text=""` でアイコンがある場合も `icon_only` と同様にアイコン中央揃えを適用
- 判定条件: `(self.icon_only or not self.text) and display_icon != "NONE"`

**Blender ソース参照**:
- `widget_draw_text()` のデフォルト配置は `UI_STYLE_TEXT_CENTER`
- `BUT_TEXT_LEFT` フラグがない限りテキストは中央揃え

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `widget_factory.py` | `_create_checkbox()` で icon_only 分岐、`_create_toggle()` で icon_only 渡し |
| `items/buttons.py` | ToggleItem に `icon_only` フィールド追加、`__post_init__()`、`calc_size()` 修正、`draw()` でアイコン/テキスト配置を Blender 準拠に変更 |

#### 関連ソース
- `source/blender/editors/interface/interface_layout.cc` - `uiItemFullR()`, `ui_item_rna_size()`
- `source/blender/editors/interface/interface_utils.cc` - `uiDefAutoButR()`
- `source/blender/editors/interface/interface_widgets.cc` - `widget_draw_text()`, `widget_draw_text_icon()`

---

### D-2: VectorItem のサイズがテキスト依存

**優先度**: 🟡 中
**関連**: A-2 (VectorItem)

#### 現象
- GPULayout では `text="Location:"` の長さによってラベル部分の幅が変動
- Blender では固定比率でラベルとウィジェットが分割される

#### Blender の動作
```
┌──────────────────────────────────────────────────────────┐
│ Location: │ X │  0 m  │ Y │  0 m  │ Z │  0 m  │          │
│ Scale:    │   │ 1.000 │   │ 1.000 │   │ 1.000 │          │
│ Rotation: │ X │   0°  │ Y │   0°  │ Z │   0°  │          │
└──────────────────────────────────────────────────────────┘
※ ラベル幅は固定（約30%）、ウィジェット幅も均等
```

#### GPULayout の現状
```
┌──────────────────────────────────────────────────────────┐
│ Location: │ X: 0.00000 │ Y: 0.00000 │ Z: 0.00000 │       │
│ Scale:    │ X: 1.000   │ Y: 1.000   │ Z: 1.000   │       │
│ Rotation: │ X: 0.00000 │ Y: 0.00000 │ Z: 0.00000 │       │
└──────────────────────────────────────────────────────────┘
※ テキスト長に応じてラベル幅が変動
```

#### 2026-01-25 更新
- Vector 内部の **X/Y/Z 間のギャップ**を 0 に変更（Blender の連結表示に近づけた）
- Vector ラベルを **固定比率領域内でクリップ/省略表示**に変更

#### 調査項目
- [ ] `uiLayoutItemFlow` でのベクトルプロパティ幅計算
- [ ] ColorItem で実装済みの固定比率ロジックを VectorItem に適用可能か
- [ ] `UI_UNIT_X` ベースの幅計算ルール

---

### D-3: サブタイプに応じた単位・精度・ラベル表示

**優先度**: 🔴 高
**関連**: A-2 (VectorItem), B-1 (index)

#### 現象
- Blender では `TRANSLATION` サブタイプは「0 m」、`EULER` は「0°」と単位表示
- 小数点以下の桁数もサブタイプ依存（Length=3桁, Angle=0桁デフォルト）
- 各要素のラベル（X, Y, Z）の表示条件が不明

#### Blender の動作
```
Location:  X │  0 m  │ Y │  0 m  │ Z │  0 m  │   ← 長さ単位
Scale:       │ 1.000 │   │ 1.000 │   │ 1.000 │   ← 無次元
Rotation:  X │   0°  │ Y │   0°  │ Z │   0°  │   ← 角度単位
```

#### GPULayout の現状
```
Location: X: 0.00000  Y: 0.00000  Z: 0.00000   ← 単位なし、桁数固定
Scale:    X: 1.000    Y: 1.000    Z: 1.000
Rotation: X: 0.00000  Y: 0.00000  Z: 0.00000   ← 度数表示なし
```

#### 2026-01-25 更新
- Number/Slider/Vector に `subtype` を伝播
- `TRANSLATION`/`EULER` などは **単位付きフォーマット**を適用（best-effort）
  - `bpy.utils.units.to_string()` が利用可能な場合は Blender の表示に追従
  - 利用不可時は簡易フォールバック（Rotation は °、Translation は m）

#### 2026-01-26 更新
- Blender の `ui_but_calc_float_precision()` 相当ロジックを実装
  - step と値に基づいた **小数桁の自動決定**（`UI_PRECISION_FLOAT_MAX` 互換）
  - `precision=-1` 時の上限判定（`max_value < 10.001` → 3桁）
  - 回転がラジアン表示の時は最小 5 桁
- `PERCENTAGE` / `PIXEL(_DIAMETER)` / `FACTOR` の表示を Blender と同様に調整
- `DISTANCE_CAMERA` / `DISTANCE_DIAMETER` / `CAMERA` などの単位カテゴリを追加
- Number/Slider の表示に `step` / `max_val` を渡すよう修正

#### 調査項目
- [ ] `RNA_property_subtype()` で取得できるサブタイプ一覧
- [ ] `PROP_UNIT_LENGTH`, `PROP_UNIT_ROTATION` 等の単位タイプ
- [ ] `bUnit_AsString2()` での単位文字列変換
- [ ] `ui_but_value_to_string()` での精度決定ロジック
- [ ] `RNA_property_ui_range()` での `precision` / `step` 取得
- [ ] 要素ラベル（X/Y/Z）の表示条件（`use_property_split` との関係）

#### 関連ソース
- `source/blender/makesrna/RNA_types.hh` - `PropSubType`, `PropUnit`
- `source/blender/blenlib/intern/unit.cc` - `bUnit_AsString2()`
- `source/blender/editors/interface/interface.cc` - `ui_but_value_to_string()`

---

### D-4: column_flow(align=True) の角丸処理

**優先度**: 🟡 中
**関連**: C-2 (column_flow)

#### 現象
- GPULayout では列間で隣接するアイテムの角が丸いまま
- Blender では隣接する辺の角は直角（連結して見える）

#### Blender の動作
```
┌─────────┬─────────┬─────────┐
│  Btn 1  │  Btn 4  │  Btn 7  │  ← 上辺のみ角丸
├─────────┼─────────┼─────────┤  ← 内部は直角
│  Btn 2  │  Btn 5  │  Btn 8  │
├─────────┼─────────┼─────────┤
│  Btn 3  │  Btn 6  │  Btn 9  │  ← 下辺のみ角丸
└─────────┴─────────┴─────────┘
```

#### GPULayout の現状
```
┌─────────┐ ┌─────────┐ ┌─────────┐
│  Btn 1  │ │  Btn 4  │ │  Btn 7  │  ← 各ボタンが独立して角丸
├─────────┤ ├─────────┤ ├─────────┤
│  Btn 2  │ │  Btn 5  │ │  Btn 8  │
├─────────┤ ├─────────┤ ├─────────┤
│  Btn 3  │ │  Btn 6  │ │  Btn 9  │
└─────────┘ └─────────┘ └─────────┘
```

#### 調査項目
- [ ] `uiLayoutSetEmboss()` と `align` の関係
- [ ] `UI_block_align_begin/end` での連結処理
- [ ] 各アイテムの `alignnr` による位置判定（`UI_BUT_ALIGN_*` フラグ）
- [ ] 列をまたぐ align の適用ルール（同一 alignnr グループに属するか）

#### 関連ソース
- `source/blender/editors/interface/interface_layout.cc` - `uiLayoutSetAlign()`
- `source/blender/editors/interface/interface.cc` - `ui_block_align_calc()`

---

### D-5: heading パラメータの表示条件

**優先度**: 🟡 中
**関連**: C-1 (heading)

#### 現象
- GPULayout では `row(heading="Row Heading")` でラベルアイテムにも heading が表示
- Blender では heading はプロパティアイテムの前にのみ表示され、label() では表示されない

#### Blender の動作
```
4. heading parameter (C-1)
          Item 1        Item 2       ← "Row Heading" が表示されない
Vertical Item 1
Vertical Item 2                      ← "Column Heading" も表示されない
```

#### GPULayout の現状
```
4. heading parameter (C-1)
Row Heading  Item 1     Item 2       ← heading が表示される
Column Heading
Vertical Item 1
Vertical Item 2
```

#### 調査項目
- [ ] `uiLayout::heading` の挿入タイミング（`uiItemL` vs `uiItemR`）
- [ ] `UI_block_layout_set_current()` での heading 消費ロジック
- [ ] heading が表示される条件（`ui_layout_heading_draw()` の呼び出し条件）
- [ ] `use_property_split` との相互作用

#### 関連ソース
- `source/blender/editors/interface/interface_layout.cc` - `ui_layout_heading_draw()`
- `source/blender/editors/include/UI_interface_layout.hh` - `uiLayout.heading`

---

### D-6: use_property_split での VectorItem 縦表示

**優先度**: 🔴 高
**関連**: C-3 (use_property_split), A-2 (VectorItem)

#### 現象
- GPULayout では `use_property_split=True` でも VectorItem が水平表示のまま
- Blender では各要素が縦に並ぶ（Location X, Y, Z が別々の行）

#### Blender の動作
```
use_property_split=True:
┌────────────────┬────────────────────────┬───┐
│    Location X  │         0 m            │ ● │
│            Y   │         0 m            │ ● │
│            Z   │         0 m            │ ● │
├────────────────┼────────────────────────┼───┤
│      Scale X   │        1.000           │ ● │
│            Y   │        1.000           │ ● │
│            Z   │        1.000           │ ● │
└────────────────┴────────────────────────┴───┘
※ 最初の要素のみプロパティ名、以降は軸名のみ
※ 右端に操作ボタン（●）
```

#### GPULayout の現状
```
use_property_split=True:
┌────────────────┬───────────────────────────────────────┐
│    Location    │ X: 0.00000  Y: 0.00000  Z: 0.00000    │
│    Scale       │ X: 1.000    Y: 1.000    Z: 1.000      │
└────────────────┴───────────────────────────────────────┘
※ 水平表示のまま
```

#### 調査項目
- [ ] `uiItemFullR()` での配列プロパティ + `use_property_split` 処理
- [ ] `ui_item_array()` vs `ui_item_array_with_property_split()` の分岐
- [ ] 各要素行でのラベル生成ロジック（最初の行のみフルラベル）
- [ ] 「デコレーター」（右端の ● ボタン）の用途と実装

#### 関連ソース
- `source/blender/editors/interface/interface_layout.cc` - `uiItemFullR()`, `ui_item_array()`
- `source/blender/editors/interface/interface_layout.cc` - `uiLayout::property_split`

---

## 調査優先順位

### 高優先度（機能的な差異）
1. **D-6**: use_property_split での VectorItem 縦表示
2. **D-3**: サブタイプに応じた単位・精度・ラベル表示
3. ~~**D-1**: CheckboxItem / ToggleItem の icon_only 対応~~ ✅ 完了

### 中優先度（見た目の差異）
4. **D-5**: heading パラメータの表示条件
5. **D-4**: column_flow(align=True) の角丸処理
6. **D-2**: VectorItem のサイズがテキスト依存

---

## アイコンシステム（2026-01-25 完了）

### I-1: Blender 公式アイコンの PNG 変換 ✅

**完了日**: 2026-01-25

#### 概要
Blender の SVG アイコンを PNG に変換し、GPULayout で描画するシステム。

#### 実装済み機能

- **SVG → PNG 変換**: `tools/blender_icon_fetch.py` で Inkscape を使用
- **アスペクト比保持**: `--export-width` のみ指定（高さは自動）
- **テーマカラー対応**: パス名に基づく色検出（`icon_`, `text_` など）
- **中央揃え**: Blender の `icon_draw_rect()` スタイルのセンタリング

#### 主なファイル

| ファイル | 役割 |
|---------|------|
| `tools/blender_icon_fetch.py` | SVG → PNG 変換スクリプト |
| `ui/gpu/drawing.py` | `IconDrawing.draw_texture_file()` でアスペクト比保持描画 |
| `ui/gpu/style.py` | `ICON_SIZE = 16` 定数（単一ソース） |
| `ui/gpu/icons/` | 生成された PNG ファイル（gitignore 対象） |

#### 技術的ポイント

1. **非正方形 SVG の処理**:
   - Blender の SVG は viewBox が非正方形のものがある（例: 1500×1400）
   - `--export-width` のみで変換することでアスペクト比を保持
   - 描画時に `preserve_aspect=True` でセンタリング

2. **サイズ一元管理**:
   - `style.py` の `ICON_SIZE = 16` が唯一の定義
   - `drawing.py` と `buttons.py` はこの値を参照

3. **テーマカラー検出**:
   ```python
   # パス名による色判定
   if path.stem.startswith("icon_"):
       color = theme.icon_color
   elif path.stem.startswith("text_"):
       color = theme.text_color
   ```

#### アイコン再生成

```bash
# Inkscape が必要
python tools/blender_icon_fetch.py --local-svg-dir path/to/icons_svg --size 16
```

---

## 参照

- Blender ソース: `source/blender/makesrna/intern/rna_ui_api.cc`
- Blender ヘッダー: `source/blender/editors/include/UI_interface_layout.hh`
- GPULayout: `ui/gpu/layout/`
- WidgetFactory: `ui/gpu/widget_factory.py`
