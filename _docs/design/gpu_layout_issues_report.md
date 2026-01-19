# GPULayout Issues Report

> Version: 1.1.0
> Created: 2026-01-19
> Updated: 2026-01-19
> Status: **Analysis**
> Related: Issue #100, `gpu_dialog_implementation.md`

---

## 概要

このレポートは、GPULayout システムと Blender 標準の UILayout を比較した結果、
発見された問題点をまとめたものである。

### テスト環境

- **左側**: `demo.uilayout_reference` - Blender 標準 UILayout（invoke_popup）
- **右側**: `demo.layout_structure` - GPULayout（GPUPanelMixin）
- パネル幅はデフォルトより少し広げた状態でスクリーンショットを取得

---

## 発見された問題一覧

| # | カテゴリ | 重要度 | 問題 | 影響範囲 |
|---|---------|--------|------|---------|
| **0** | **描画順序** | **💀 Blocker** | **アイテムと子レイアウトの配置順序が壊れる** | **全レイアウト** |
| 1 | 幅計算 | 🔴 Critical | row() 内アイテムの幅が均等分配されない | 全 row |
| 2 | 幅計算 | 🔴 Critical | row() 内 column() の幅が親幅を超える | 複数列構造 |
| 3 | リサイズ | 🔴 Critical | パネル幅変更時に子レイアウトが追従しない | 全レイアウト |
| 4 | split() | 🟠 High | factor 比率が視覚的に機能していない | split 使用箇所 |
| 5 | box() | 🟠 High | ネスト構造で幅が正しく継承されない | box 使用箇所 |
| 6 | scale_x | 🟡 Medium | scale_x が親幅に対する相対値として計算されない | scale 使用箇所 |
| 7 | alignment | 🟡 Medium | LEFT/CENTER/RIGHT が機能していない | alignment 使用箇所 |

---

## 詳細分析

### 0. 💀 アイテムと子レイアウトの配置順序問題【Blocker】

**期待される動作（UILayout）**:
```
1. row() - Horizontal Layout    ← セクション見出し
   [Left] [Center] [Right]      ← row() の内容（見出しの直後）
   row(align=True)
   [A] [B] [C]

2. column() - Vertical Layout   ← 次のセクション見出し
   [Column 1] [Column 2] ...    ← column() の内容
```

**実際の動作（GPULayout）**:
```
1. row() - Horizontal Layout    ← 見出しが
row(align=True)                    全部先に
2. column() - Vertical Layout      描画される
3. box() - Bordered Container
4. split() - Proportional Split
5. Nested Layout
6. scale_x / scale_y
7. alignment (if supported)
----- ここまで _items -----
Left Center Right               ← コンテンツが
[A] [B] [C]                        全部後に
[Column 1] [Column 2] ...          描画される
----- ここから _children -----
```

**原因コード** (`layout.py` の構造):

GPULayout は `_items` と `_children` を **別々のリスト**で管理している:

```python
class GPULayout:
    def __init__(self, ...):
        self._items: list[LayoutItem] = []      # label(), operator() など
        self._children: list[GPULayout] = []    # row(), column(), box() など
```

**レイアウト計算時** (`layout.py:1533-1554`):
```python
def layout(self, *, force: bool = False) -> None:
    # ...
    # 既存アイテムの後からカーソル位置を取得
    if self._items:
        last_item = self._items[-1]
        cursor_y = last_item.y - last_item.height - spacing

    # ← ここで _children を配置（_items の後に全て配置される）
    for child in self._children:
        child.x = cursor_x
        child.y = cursor_y
        child.layout(force=force)
        cursor_y -= child.calc_height() + spacing
```

**描画時** (`layout.py:1654-1666`):
```python
def draw(self) -> None:
    # ...
    # アイテム描画（全ての _items を先に描画）
    for item in self._items:
        item.draw(self.style, state)

    # 子レイアウト描画（全ての _children を後に描画）
    for child in self._children:
        child.draw()
```

**問題点**:
- アイテム（label, button 等）と子レイアウト（row, column 等）が**追加順序を無視**して配置・描画される
- `_items` → `_children` の順序で処理されるため、**インターリーブ（交互配置）ができない**
- これは UILayout との**根本的な設計の違い**

**UILayout の動作**:
```python
layout.label(text="Section 1")  # → layout に追加
row = layout.row()              # → layout に「row コンテナ」として追加
row.label(text="In Row")        # → row に追加（layout ではない）
layout.label(text="Section 2")  # → layout に追加（row の後）
```

UILayout では `row()` は「その場所に挿入されるコンテナ」として扱われ、
後続の `layout.xxx()` は row の後に配置される。

**GPULayout の動作**:
```python
layout.label(text="Section 1")  # → _items[0]
row = layout.row()              # → _children[0]
row.label(text="In Row")        # → row._items[0]
layout.label(text="Section 2")  # → _items[1] ← Section 1 の直後に配置される！
```

**修正方針**:

**案 1: 単一リストで管理**
```python
self._elements: list[LayoutItem | GPULayout] = []

def label(self, ...):
    item = LabelItem(...)
    self._elements.append(item)

def row(self, ...):
    child = GPULayout(...)
    self._elements.append(child)
    return child
```

**案 2: 順序インデックスを保持**
```python
self._items: list[LayoutItem] = []
self._children: list[GPULayout] = []
self._order: list[tuple[str, int]] = []  # ('item', 0), ('child', 0), ('item', 1), ...
```

**推奨**: 案 1（単一リスト）がシンプルで保守しやすい

---

### 1. row() 内アイテムの幅均等分配問題

**期待される動作（UILayout）**:
```
row 内の3アイテム: [  Left  ][  Center  ][  Right  ]
                   ←───────── 親幅 ──────────────→
```

**実際の動作（GPULayout）**:
```
row 内の3アイテム: [Left][Center][Right]
                   ←─ 自然サイズ ─→  ← 余白 →
```

**原因コード** (`layout.py:1109-1116`):
```python
else:
    # 水平レイアウト
    item.x = self._cursor_x
    item.y = self._cursor_y
    item.width = item_width * self.scale_x  # ← 自然サイズのまま
    item.height = item_height * self.scale_y
    self._cursor_x += item.width + self._get_spacing()
```

**問題点**:
- 水平レイアウト（row）でアイテム追加時、`item_width * self.scale_x` で自然サイズを使用
- UILayout は利用可能幅をアイテム数で均等分配する
- GPULayout は各アイテムが自然サイズのまま配置される

**修正方針**:
- row() 生成時に子アイテム数を事前に知る必要があるか、
- 2パスレイアウト（1パス目でアイテム収集、2パス目で幅計算・配置）を検討

---

### 2. row() 内 column() の幅超過問題

**期待される動作（UILayout）**:
```
row 内の3 column: [Column 1][Column 2][Column 3]
                  ←────────── 親幅 ──────────────→
各 column は親幅の 1/3
```

**実際の動作（GPULayout）**:
```
[Column 1          ][Column 2          ][Column 3   (見切れ)
←── 親幅 ──→←── 親幅 ──→←── 親幅 ──→
```

**原因コード** (`layout.py:203-226`):
```python
def column(self, align: bool = False) -> GPULayout:
    available_width = self._get_available_width()

    if self._split_factor > 0.0 and self._split_column_index == 0:
        col_width = available_width * self._split_factor
    elif self._split_factor > 0.0 and self._split_column_index == 1:
        col_width = available_width * (1.0 - self._split_factor)
    else:
        # ← ここが問題: 親の全幅を使ってしまう
        col_width = available_width
```

**問題点**:
- `split()` 外で `column()` を呼んだ場合、各 column は `available_width`（親の全幅）を使用
- row 内で複数の column() を呼ぶと、全て同じ幅（親の全幅）になる
- 結果として column が重なったり、親幅を超えて見切れる

**修正方針**:
- `row()` が自身の子 column 数を把握し、幅を均等分配する仕組みが必要
- または `row().column()` を呼ぶ際に、row 側で幅を動的に計算

---

### 3. パネルリサイズ時の子レイアウト追従問題

**期待される動作**:
```
パネル幅変更 → 全子レイアウトの幅が再計算 → 全アイテムが新幅に追従
```

**実際の動作**:
```
パネル幅変更 → 子レイアウトの幅は初期値のまま → アイテム位置がずれる
```

**原因分析**:

`_rebuild_layout()` (panel_mixin.py) では:
```python
if self._layout is None:
    # 新規作成
    layout = GPULayout(x=..., y=..., width=self.gpu_width, ...)
    ...
else:
    # 位置更新のみ
    self._layout.x = self._panel_x
    self._layout.y = self._panel_y
    # ← width の更新がない
```

`layout()` メソッド (layout.py:1518-1563) でも:
```python
for child in self._children:
    child.x = cursor_x
    child.y = cursor_y
    child.layout(force=force)
    # ← child.width の更新がない
```

**問題点**:
- パネル幅が変わっても、子レイアウトの `width` プロパティは更新されない
- `_relayout_items()` は位置を再計算するが、幅は `self._get_available_width()` から取得
- 子レイアウトの `width` が古い値のままなので、`_get_available_width()` も古い値を返す

**修正方針**:
- `layout()` 時に子レイアウトの `width` を親から伝播させる
- または `_get_available_width()` を親レイアウトから動的に計算

---

### 4. split() の factor 比率問題

**期待される動作（UILayout）**:
```
split(factor=0.3):
[  30%  ][      70%      ]
```

**実際の動作（GPULayout）**:
```
[30%][70%] ← 非常に狭い（親幅に追従していない）
```

**原因分析**:

`split()` の実装は正しいが、問題 #3（リサイズ追従）の影響を受けている:
```python
def split(self, *, factor: float = 0.0, align: bool = False) -> GPULayout:
    child = GPULayout(
        x=self._cursor_x,
        y=self._cursor_y,
        width=self._get_available_width(),  # ← 初期幅
        ...
    )
    child._split_factor = factor
```

**問題点**:
- `split()` 作成時の `_get_available_width()` が固定値
- パネルリサイズ後も split の幅は変わらない

**修正方針**:
- 問題 #3 を解決すれば、この問題も解消される見込み

---

### 5. box() のネスト幅継承問題

**期待される動作（UILayout）**:
```
┌─ Outer Box ─────────────────────┐
│ ┌─ Inner 1 ─┐┌─ Inner 2 ─────┐ │
│ │           ││               │ │
│ └───────────┘└───────────────┘ │
└─────────────────────────────────┘
  ←──────────── 親幅 ────────────→
```

**実際の動作（GPULayout）**:
```
┌─ Outer Box ─┐
│ ┌─ Inner 1 ─┐┌─ Inner 2 ───────────┐ ← 見切れ
│ │           ││                     │
│ └───────────┘└─────────────────────┘
└─────────────┘
```

**原因分析**:

`box()` は `column()` を呼ぶ:
```python
def box(self) -> GPULayout:
    child = self.column()
    child._draw_background = True
    child._draw_outline = True
    return child
```

問題 #2 と同様、column() が親の全幅を使用してしまう。

---

### 6. scale_x の動作問題

**期待される動作（UILayout）**:
```
scale_x=2.0: [        Button        ] ← 通常の2倍幅
```

**実際の動作（GPULayout）**:
```
scale_x=2.0: [Button] ← 自然サイズ × 2（親幅に追従しない）
```

**原因コード** (`layout.py:1086-1089`):
```python
if self.alignment == Alignment.EXPAND:
    item.width = available_width * self.scale_x  # ← EXPAND 時のみ scale_x 適用
```

**問題点**:
- `scale_x` は `available_width * scale_x` として計算される
- `available_width` が古い値（問題 #3）だと、期待通りに動作しない
- また、`scale_x=2.0` は「親幅の2倍」ではなく「利用可能幅 × 2」

**参考**: Blender UILayout の `scale_x` は、デフォルトサイズに対する倍率

---

### 7. alignment の動作問題

**期待される動作（UILayout）**:
```
alignment=LEFT:   [Button]
alignment=CENTER:        [Button]
alignment=RIGHT:                [Button]
```

**実際の動作（GPULayout）**:
```
alignment=LEFT:   [Button]
alignment=CENTER: [Button]  ← 左寄せのまま
alignment=RIGHT:  [Button]  ← 左寄せのまま
```

**原因コード** (`layout.py:1091-1098`):
```python
else:
    # LEFT/CENTER/RIGHT: 自然サイズを維持
    item.width = item_width * self.scale_x
    if self.alignment == Alignment.CENTER:
        item.x = self._cursor_x + (available_width - item.width) / 2
    elif self.alignment == Alignment.RIGHT:
        item.x = self._cursor_x + available_width - item.width
    else:  # LEFT
        item.x = self._cursor_x
```

**問題点**:
- コード自体は正しいが、`available_width` が古い値（問題 #3）だと位置計算が正しくない
- パネルを広げても `available_width` は初期値のままなので、CENTER/RIGHT が機能しない

---

## 根本原因の整理

上記 8 つの問題は、**3 つの根本原因**に集約される:

### 💀 根本原因 0: _items と _children の分離管理【最優先】

**影響する問題**: #0（他の全問題の前提条件）

現在の実装では:
1. `_items`（label, button 等）と `_children`（row, column 等）が**別リスト**で管理
2. レイアウト計算・描画時に `_items` → `_children` の順で処理
3. 追加順序（インターリーブ）が**完全に無視**される

**解決策**:
- `_elements: list[LayoutItem | GPULayout]` に統合
- 追加順序を保持し、その順序で配置・描画

**影響範囲**:
- `__init__()`: リスト構造の変更
- `row()`, `column()`, `split()`, `box()`: `_children.append()` → `_elements.append()`
- `_add_item()`: `_items.append()` → `_elements.append()`
- `layout()`: `_items` + `_children` の分離処理 → `_elements` の統合処理
- `draw()`: 同上
- `calc_height()`, `calc_width()`: 同上

### 根本原因 A: 子レイアウト幅の動的更新不足

**影響する問題**: #3, #4, #5, #6, #7

現在の実装では:
1. `row()`, `column()`, `split()`, `box()` 作成時に `width` が固定される
2. 親レイアウトの幅が変わっても、子レイアウトの `width` は更新されない
3. `_get_available_width()` は自身の `width` から計算するため、古い値を返す

**解決策**:
- `layout()` 呼び出し時に、親から子へ `width` を伝播させる
- または、`_get_available_width()` を親レイアウトから動的に計算する仕組みを導入

### 根本原因 B: row() 内アイテムの幅均等分配ロジック不足

**影響する問題**: #1, #2

現在の実装では:
1. row() 内のアイテムは自然サイズで配置される
2. 利用可能幅をアイテム数で割る均等分配が行われていない

**解決策**:
- 2パスレイアウト方式を導入:
  - 1パス目: アイテムを収集し、総数を把握
  - 2パス目: 利用可能幅 ÷ アイテム数 で幅を計算し、配置
- または、アイテム追加後に `layout()` で幅を再計算する仕組み

---

## 修正優先度

### 💀 Phase 0: 根本原因 0 の解決（配置順序）【最優先・Blocker】

**これを解決しないと他の問題の検証すらできない。**

1. `_items` と `_children` を `_elements` に統合
2. `layout()` で `_elements` を順序通りに配置
3. `draw()` で `_elements` を順序通りに描画
4. テスト: label → row → label → column の順序が正しく描画されるか確認

**変更箇所の一覧**:
```
layout.py:
  - __init__: _items, _children → _elements
  - row(): _children.append → _elements.append
  - column(): 同上
  - split(): 同上
  - box(): column() 経由なので変更不要
  - _add_item(): _items.append → _elements.append
  - layout(): _items + _children ループ → _elements ループ
  - _relayout_items(): _items ループ → _elements から LayoutItem を抽出
  - draw(): _items + _children ループ → _elements ループ
  - calc_height(): 同上
  - calc_width(): 同上
  - handle_event(): _children ループ → _elements から GPULayout を抽出
  - sync_reactive(): 同上
```

### Phase 1: 根本原因 A の解決（幅伝播）

1. `GPULayout.layout()` で子レイアウトの `width` を更新
2. `GPUPanelMixin._rebuild_layout()` でルートレイアウトの `width` を更新
3. テスト: パネルリサイズ時に box, split, alignment が追従するか確認

### Phase 2: 根本原因 B の解決（均等分配）

1. `row()` 用の 2パスレイアウトを実装
2. または、`row()._finalize()` メソッドで子アイテムの幅を再計算
3. テスト: row 内の label, button, column が均等に配置されるか確認

### Phase 3: 検証

1. `demo.layout_structure` で全セクションが UILayout と同等に表示されるか確認
2. `demo.uilayout_reference` との差分が許容範囲か評価

---

## UILayout との互換性メモ

### row() の挙動差異

| 項目 | UILayout | GPULayout (現状) |
|------|----------|-----------------|
| 子アイテム幅 | 利用可能幅を均等分配 | 自然サイズ |
| alignment | 利用可能幅内で配置 | 自然サイズ内で配置 |
| scale_x | デフォルトサイズに対する倍率 | 利用可能幅に対する倍率 |

### column() の挙動差異

| 項目 | UILayout | GPULayout (現状) |
|------|----------|-----------------|
| row() 内での幅 | 親幅を兄弟数で分配 | 親の全幅を使用 |
| split() 内での幅 | factor に応じて分配 | factor に応じて分配（✓ 正しい） |

### build/layout タイミング

| 項目 | UILayout | GPULayout (現状) |
|------|----------|-----------------|
| 幅計算 | draw() 呼び出し時 | アイテム追加時（固定） |
| リサイズ対応 | 自動 | 手動で mark_dirty() + layout() が必要 |

---

## 参照ファイル

| ファイル | 関連コード |
|---------|-----------|
| `ui/gpu/layout.py:1071-1119` | `_add_item()` - アイテム配置ロジック |
| `ui/gpu/layout.py:180-286` | `row()`, `column()`, `split()` |
| `ui/gpu/layout.py:1518-1563` | `layout()` - レイアウト計算 |
| `ui/gpu/layout.py:1565-1599` | `_relayout_items()` - アイテム再配置 |
| `ui/gpu/panel_mixin.py:271-345` | `_rebuild_layout()` |
| `ui/gpu/test_layout.py` | テストオペレーター |

---

*Last Updated: 2026-01-19*
