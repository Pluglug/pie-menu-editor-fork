# GPULayout Architecture v2.1 - Refined Design

> Version: 0.2.0
> Created: 2026-01-19
> Status: **RFC (Request for Comments)**
> Related: `gpu_layout_issues_report.md`, `gpu_layout_architecture_v2.md`, Issue #100
> Reviewer: Claude Opus 4.5

---

## Executive Summary

v2.0 の設計方向性は正しいが、以下の点で改良が必要：

1. **IntrinsicSize の過剰設計** → 簡略化
2. **Builder パターンの API 混乱** → UILayout 互換に修正
3. **IMGUI 再構築コスト** → キャッシュ戦略を追加
4. **split() の動作** → UILayout との互換性を明確化
5. **Constraints の契約不明瞭** → root/child の tight/loose を明文化
6. **row() の幅配分モデル不足** → flex/basis で均等分配と固定幅を両立
7. **要素の恒久IDとヒットテスト** → 安定キーで状態/入力を維持

本ドキュメントは v2.0 を基盤とし、上記を修正した **v2.1** を提案する。

---

## Part 1: v2.0 レビュー結果

### 1.1 高評価点（維持）

| 項目 | 評価 |
|------|------|
| 統一要素モデル（`_elements` 単一リスト） | ✅ 必須 |
| BoxConstraints による制約伝播 | ✅ 適切 |
| Build/Layout/Render 分離 | ✅ 良い設計 |
| Flutter/SwiftUI/Qt の分析 | ✅ 参考価値大 |

### 1.2 懸念点（修正が必要）

| 項目 | 問題 | 修正方針 |
|------|------|---------|
| IntrinsicSize.expand_x/y | UILayout にない概念 | 削除 |
| Builder パターンの返り値 | 新 Builder を返すと混乱 | Container を直接返す |
| 毎フレーム再構築 | GC 負荷 | オブジェクトプール検討 |
| split() の動作 | UILayout との乖離 | 2列専用に限定 |
| Constraints 契約 | root/child の幅が曖昧 | tight/loose を明文化 |
| row() の幅配分 | 固定幅/均等分配の両立なし | flex/basis で統一 |
| 要素の恒久ID | IMGUI で状態/入力が不安定 | LayoutKey を必須化 |

---

## Part 2: UILayout 動作の正確な理解

### 2.1 UILayout の本質

Blender UILayout は **IMGUI (Immediate Mode GUI)** だが、内部では **暗黙の 2 パス**で動作する：

```
draw() 呼び出し
    │
    ├─ Pass 1: 構築（ユーザーコード）
    │   layout.label("Title")
    │   row = layout.row()
    │   row.label("Left")
    │   row.label("Right")
    │   layout.separator()
    │
    ├─ Pass 2: レイアウト計算（Blender 内部）
    │   - row 内のアイテム数を確認（2個）
    │   - 利用可能幅を 2 等分
    │   - 位置を確定
    │
    └─ Pass 3: 描画（Blender 内部）
```

**重要**: UILayout は「アイテム追加時に即座に配置」しているように見えるが、
実際は **描画時にまとめてレイアウト計算**している。

### 2.2 row() 内の幅分配ルール

UILayout の row() 内では：

1. **デフォルト**: 利用可能幅をアイテム数で**均等分配**
2. **ui_units_x 指定時**: 固定幅を使用
3. **alignment 指定時**: 均等分配後、alignment に従って配置

```python
# UILayout での動作
row = layout.row()
row.label(text="A")    # → 幅 = 利用可能幅 / 3
row.label(text="BB")   # → 幅 = 利用可能幅 / 3
row.label(text="CCC")  # → 幅 = 利用可能幅 / 3
# テキスト長に関係なく均等分配！
```

### 2.3 scale_x/scale_y の正しい解釈

```python
row = layout.row()
row.scale_x = 2.0
row.operator(...)  # → この行の「全アイテム」が通常の 2 倍幅
```

`scale_x` は:
- ❌ 「利用可能幅の 2 倍」ではない
- ✅ 「デフォルトサイズに対する倍率」

UILayout では `scale_x` を設定すると、その**コンテナ内の全アイテム**に適用される。

### 2.4 split() の正しい動作

```python
# UILayout での split()
split = layout.split(factor=0.3)
col1 = split.column()  # 30% 幅
col2 = split.column()  # 70% 幅

# または
split = layout.split(factor=0.3)
split.label(text="30%")  # 30% 幅（暗黙の column）
split.label(text="70%")  # 70% 幅（暗黙の column）
```

**重要**: `split()` は:
1. `factor` で最初の列の幅を指定（デフォルト 0.5）
2. 2 列目以降は残り幅を等分
3. `align=True` でアイテム間スペースをなくす

### 2.5 row()/scale_x/alignment の補足仕様（GPULayout 側の解釈）

test_layout.py / issues_report の観測結果を前提に、GPULayout 側で以下を仕様化する：

1. **row() 既定は均等分配**（全子要素が同じ幅）
2. **固定幅がある場合は先に確保**  
   - `ui_units_x` / 明示的な `fixed_width` / prop の UI 仕様で決まる幅
3. **残り幅は flex weight で分配**  
   - 既定 weight=1  
   - `scale_x` は weight の倍率として扱う
4. **alignment は「余りが出た場合」の主軸配置**  
   - `Alignment.EXPAND` は余りを分配  
   - `LEFT/CENTER/RIGHT` はオフセットのみ
5. **scale_y は高さ倍率**  
   - `scale_x` は「親幅倍率」ではなく **子要素の幅係数**

---

## Part 3: 修正版アーキテクチャ

### 3.1 設計原則（v2.1）

| # | 原則 | v2.0 | v2.1 |
|---|------|------|------|
| 1 | 統一要素モデル | ✅ | ✅ 維持 |
| 2 | Constraint Propagation | ✅ | ✅ 維持 |
| 3 | Two-pass Layout | ✅ | ✅ 維持 |
| 4 | Intrinsic Size | ⚠️ 過剰 | 🔧 簡略化 |
| 5 | Builder Pattern | ⚠️ 混乱 | 🔧 Container 直接返却 |
| 6 | Object Pooling | ❌ なし | ➕ 追加 |
| 7 | Stable Identity | ? なし | ? LayoutKey を追加 |

### 3.2 クラス階層（修正版）

```
┌─────────────────────────────────────────────────────────┐
│                    LayoutElement                         │
│              (Abstract Base Class)                       │
├─────────────────────────────────────────────────────────┤
│  # Identity                                              │
│  parent: Optional[LayoutElement]                         │
│  tag: str  # デバッグ・識別用                            │
│  key: LayoutKey  # 安定ID（状態/ヒット保持）              │
│                                                          │
│  # Computed (Layout Phase で確定)                        │
│  x, y, width, height: float                              │
│                                                          │
│  # Core Methods                                          │
│  def measure(constraints: BoxConstraints) -> Size        │
│  def arrange(x: float, y: float) -> None                 │
│  def draw(style: Style) -> None                          │
└─────────────────────────────────────────────────────────┘
            ▲                    ▲
            │                    │
   ┌────────┴────────┐  ┌───────┴────────┐
   │   LeafElement   │  │ ContainerElement│
   │ (終端要素)       │  │ (コンテナ要素)  │
   ├─────────────────┤  ├─────────────────┤
   │ # 固有サイズ    │  │ # 子要素管理    │
   │ min_width       │  │ _elements: list │
   │ natural_width   │  │ spacing: float  │
   │ min_height      │  │ align: bool     │
   │ natural_height  │  │                 │
└─────────────────┘  └─────────────────┘
```

**補足**:
- `LayoutKey` は **追加順序 + 明示キー** から生成する安定ID（状態/ヒット/プール再利用に必須）
- `SizingPolicy` は **basis + flex(weight)** を保持し、row/column の幅配分に使用
- `ContainerElement` は `padding` を持ち、constraints を **deflate** して子へ渡す

### 3.3 Constraints 契約（tight/loose の明文化）

**原則**: *Constraints go down, sizes go up, positions go down.*

```python
class BoxConstraints:
    min_width: float
    max_width: float
    min_height: float
    max_height: float

    @staticmethod
    def tight(width: float, height: float) -> "BoxConstraints":
        return BoxConstraints(width, width, height, height)

    @staticmethod
    def loose(max_width: float, max_height: float) -> "BoxConstraints":
        return BoxConstraints(0, max_width, 0, max_height)
```

**root の契約**:
- パネル幅/リージョン幅は **tight** で固定（row の等分配がブレない）
- 高さは `loose`（必要分だけ伸びる）
- `set_region_bounds()` は root constraints を更新し **必ず re-layout** する

**container の契約**:
- padding を除外して子へ constraints を渡す（deflate）
- 子の計測結果 + padding で自身の size を確定
### 3.4 IntrinsicSize 簡略化

```python
# v2.0（過剰）
@dataclass
class IntrinsicSize:
    min_width: float
    natural_width: float
    min_height: float
    natural_height: float
    expand_x: bool = False  # ← 削除
    expand_y: bool = False  # ← 削除

# v2.1（簡略化）
@dataclass
class Size:
    """単純なサイズ"""
    width: float
    height: float

class LeafElement:
    """終端要素の基底クラス"""

    # 固有サイズ（構築時に確定、変更不可）
    min_width: float = 0.0
    natural_width: float = 0.0
    min_height: float = 0.0
    natural_height: float = 0.0

    def measure(self, constraints: BoxConstraints) -> Size:
        """制約内でサイズを決定"""
        # デフォルト: 自然サイズを制約内に収める
        return Size(
            width=constraints.clamp_width(self.natural_width),
            height=constraints.clamp_height(self.natural_height)
        )
```

**変更点**:
- `expand_x/expand_y` を削除
- 「拡張したいか」は Container レベルで制御（均等分配）
- LeafElement は単に「自然サイズ」を報告するのみ

### 3.5 ContainerElement（修正版）

```python
class ContainerElement(LayoutElement):
    """子要素を持つコンテナ"""

    def __init__(self):
        super().__init__()
        self._elements: list[LayoutElement] = []  # 統一リスト！

        # レイアウト設定
        self.direction: Direction = Direction.VERTICAL
        self.spacing: float = 4.0
        self.align: bool = False  # True = spacing を 0 に

        # UILayout 互換プロパティ
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.alignment: Alignment = Alignment.EXPAND

    def add(self, element: LayoutElement) -> LayoutElement:
        """子要素を追加（追加順序を保持）"""
        element.parent = self
        self._elements.append(element)
        return element

    # ─────────────────────────────────────────────────────
    # UILayout 互換メソッド
    # ─────────────────────────────────────────────────────

    def label(self, *, text: str = "", icon: str = "NONE") -> LabelElement:
        """ラベルを追加"""
        element = LabelElement(text=text, icon=icon)
        return self.add(element)

    def operator(self, idname: str = "", *, text: str = "",
                 icon: str = "NONE", on_click: Callable = None) -> ButtonElement:
        """ボタンを追加"""
        element = ButtonElement(
            text=text or idname,
            icon=icon,
            operator=idname,
            on_click=on_click
        )
        return self.add(element)

    def separator(self, *, factor: float = 1.0) -> SeparatorElement:
        """区切り線を追加"""
        element = SeparatorElement(factor=factor)
        return self.add(element)

    def row(self, align: bool = False) -> 'RowElement':
        """水平レイアウトを追加"""
        element = RowElement(align=align)
        element.parent = self
        self._elements.append(element)
        return element  # ← Container を直接返す（新 Builder ではない）

    def column(self, align: bool = False) -> 'ColumnElement':
        """垂直レイアウトを追加"""
        element = ColumnElement(align=align)
        element.parent = self
        self._elements.append(element)
        return element

    def box(self) -> 'BoxElement':
        """ボックスを追加"""
        element = BoxElement()
        element.parent = self
        self._elements.append(element)
        return element

    def split(self, *, factor: float = 0.5, align: bool = False) -> 'SplitElement':
        """分割レイアウトを追加"""
        element = SplitElement(factor=factor, align=align)
        element.parent = self
        self._elements.append(element)
        return element
```

### 3.6 Row の幅配分アルゴリズム（equal + fixed + flex）

row() は **均等分配が既定**だが、固定幅や weight も扱えるようにする。

```python
class RowElement(ContainerElement):
    """水平レイアウト - equal/fixed/flex を統一"""

    def __init__(self, align: bool = False):
        super().__init__()
        self.direction = Direction.HORIZONTAL
        self.align = align

    def measure(self, constraints: BoxConstraints) -> Size:
        n = len(self._elements)
        if n == 0:
            return Size(0, 0)

        spacing = 0 if self.align else self.spacing
        total_spacing = spacing * (n - 1)

        available_width = constraints.max_width
        content_width = max(0.0, available_width - total_spacing)

        fixed: list[tuple[LayoutElement, float]] = []
        flex: list[tuple[LayoutElement, float]] = []

        # 1) fixed/basis と flex(weight) を分離
        for child in self._elements:
            basis = child.sizing.basis_width  # None なら flex
            weight = max(child.sizing.weight * self.scale_x, 0.0)
            if basis is not None:
                fixed.append((child, basis))
            else:
                flex.append((child, weight))

        fixed_total = sum(basis for _, basis in fixed)
        remaining = max(0.0, content_width - fixed_total)
        total_weight = sum(w for _, w in flex) or 1.0

        max_height = 0.0
        for child, basis in fixed:
            size = child.measure(BoxConstraints.tight(basis, constraints.max_height))
            max_height = max(max_height, size.height)

        for child, weight in flex:
            width = remaining * (weight / total_weight)
            size = child.measure(BoxConstraints.tight(width, constraints.max_height))
            max_height = max(max_height, size.height)

        return Size(available_width, max_height * self.scale_y)

    def arrange(self, x: float, y: float) -> None:
        spacing = 0 if self.align else self.spacing
        widths = self._measured_widths  # measure() で保存した結果を使用

        content_total = sum(widths) + spacing * (len(widths) - 1)
        extra = max(0.0, self.width - content_total)

        if self.alignment == Alignment.CENTER:
            cursor_x = x + extra / 2
        elif self.alignment == Alignment.RIGHT:
            cursor_x = x + extra
        else:
            cursor_x = x

        for child, width in zip(self._elements, widths):
            child.width = width
            child.arrange(cursor_x, y)
            cursor_x += width + spacing
```

**補足**:
- `SizingPolicy.basis_width` は `ui_units_x` や明示幅から設定する
- `SizingPolicy.weight` の既定は 1（均等分配になる）
- `row.scale_x` は weight の倍率として適用
- `self._measured_widths` は arrange で再利用するために保持

### 3.7 Split の実装

```python
class SplitElement(ContainerElement):
    """分割レイアウト（factor で最初の列の幅を指定）"""

    def __init__(self, factor: float = 0.5, align: bool = False):
        super().__init__()
        self.direction = Direction.HORIZONTAL
        self.factor = factor
        self.align = align
        self._column_index = 0  # column() が呼ばれるたびにインクリメント

    def column(self, align: bool = False) -> 'ColumnElement':
        """列を追加（factor に基づいて幅を計算）"""
        element = ColumnElement(align=align)
        element.parent = self
        element._split_index = self._column_index
        self._elements.append(element)
        self._column_index += 1
        return element

    def measure(self, constraints: BoxConstraints) -> Size:
        """factor に基づいて幅を分配"""
        n = len(self._elements)
        if n == 0:
            return Size(0, 0)

        spacing = 0 if self.align else self.spacing
        total_spacing = spacing * (n - 1)
        available_width = constraints.max_width - total_spacing

        # 幅を計算
        if n == 1:
            widths = [available_width]
        elif n == 2:
            widths = [available_width * self.factor,
                      available_width * (1 - self.factor)]
        else:
            # 3列以上: 最初は factor、残りを等分
            first_width = available_width * self.factor
            remaining = available_width - first_width
            widths = [first_width] + [remaining / (n - 1)] * (n - 1)

        # 各子要素を測定
        max_height = 0.0
        for i, child in enumerate(self._elements):
            child_constraints = BoxConstraints(
                min_width=widths[i],
                max_width=widths[i],
                min_height=0,
                max_height=constraints.max_height
            )
            child_size = child.measure(child_constraints)
            max_height = max(max_height, child_size.height)

        return Size(constraints.max_width, max_height)
```

**補足**:
- `split.label()/operator()` は **暗黙の column** として扱い、`_column_index` を進める
- `n > 2` かつ `factor > 0` の場合は「最初だけ factor、残り等分」

---

## Part 4: パフォーマンス最適化

### 4.1 IMGUI 再構築の問題

PME では `draw_panel()` が毎フレーム呼ばれ、レイアウトを再構築する：

```python
def draw_panel(self, layout, context):
    layout.label(text="Title")       # ← 毎フレーム新しい LabelElement を生成
    row = layout.row()               # ← 毎フレーム新しい RowElement を生成
    row.operator(text="Button")      # ← 毎フレーム新しい ButtonElement を生成
```

**問題**: 60fps で実行すると、毎秒 60 回のオブジェクト生成・GC が発生。

### 4.2 解決策 A: オブジェクトプール

```python
class ElementPool:
    """要素のオブジェクトプール"""

    def __init__(self):
        self._pools: dict[type, list[LayoutElement]] = {}

    def acquire(self, element_type: type) -> LayoutElement:
        """プールから要素を取得（なければ新規作成）"""
        pool = self._pools.setdefault(element_type, [])
        if pool:
            element = pool.pop()
            element.reset()
            return element
        return element_type()

    def release(self, element: LayoutElement) -> None:
        """要素をプールに返却"""
        pool = self._pools.setdefault(type(element), [])
        pool.append(element)

class GPUPanel:
    """パネル管理（プール付き）"""

    def __init__(self):
        self._pool = ElementPool()
        self._root: ContainerElement = None

    def begin_frame(self):
        """フレーム開始: 前フレームの要素をプールに返却"""
        if self._root:
            self._release_recursive(self._root)
        self._root = self._pool.acquire(ColumnElement)

    def end_frame(self):
        """フレーム終了: レイアウト計算"""
        # measure + arrange
        ...
```

### 4.3 解決策 B: Dirty Flag + 差分更新

```python
class GPUPanel:
    """パネル管理（差分更新）"""

    def __init__(self):
        self._root: ContainerElement = None
        self._cached_structure_hash: int = 0

    def build(self, draw_func, context):
        """構造が変わった場合のみ再構築"""
        # 構造のハッシュを計算（軽量）
        structure_hash = self._compute_structure_hash(draw_func, context)

        if structure_hash != self._cached_structure_hash:
            # 構造が変わった → フル再構築
            self._root = ColumnElement()
            draw_func(self._root, context)
            self._cached_structure_hash = structure_hash
        else:
            # 構造は同じ → 値の更新のみ
            self._update_values(context)
```

### 4.4 推奨: Phase 0 では解決策 A を省略

**理由**:
1. 現在の GPULayout は 60fps で問題なく動作している（報告なし）
2. プール実装は複雑性を増す
3. Phase 0 の目標は「正しいレイアウト」であり、最適化は後回し

**Phase 0 で実装するもの**:
- `_elements` 統一リスト
- 均等分配アルゴリズム
- Constraints 伝播

**Phase 1 以降で検討するもの**:
- オブジェクトプール
- 差分更新
- GPU バッチング

### 4.5 LayoutKey と HitTest の安定化

IMGUI であっても、**要素IDが安定していないと入力/状態が破綻**する。

- `LayoutKey = (panel_uid, layout_path, explicit_key)` を基本とする
- HitTest は **描画順と同じ要素順**で構築し、入力時は逆順で解決
- プール/差分更新は `LayoutKey` で再利用対象を決定

---

## Part 5: 実装計画

### 5.1 Phase 0: 根本原因の解決（最優先）

**目標**: `_items` と `_children` の分離を解消

**変更箇所**:

```python
# Before
class GPULayout:
    def __init__(self):
        self._items: list[LayoutItem] = []
        self._children: list[GPULayout] = []

# After
class GPULayout:
    def __init__(self):
        self._elements: list[LayoutItem | GPULayout] = []
```

**影響範囲**:

| メソッド | 変更内容 |
|---------|---------|
| `__init__` | `_items`, `_children` → `_elements` |
| `row()`, `column()`, `split()`, `box()` | `_children.append()` → `_elements.append()` |
| `_add_item()` | `_items.append()` → `_elements.append()` |
| `layout()` | `_items` + `_children` ループ → `_elements` ループ |
| `_relayout_items()` | `_items` ループ → `_elements` から LeafItem を抽出 |
| `draw()` | `_items` + `_children` ループ → `_elements` ループ |
| `calc_height()` | 同上 |
| `calc_width()` | 同上 |
| `handle_event()` | `_children` ループ → `_elements` から Container を抽出 |

**テスト**:
```python
# このコードが正しく動作することを確認
layout.label(text="Section 1")
row = layout.row()
row.label(text="Left")
row.label(text="Right")
layout.label(text="Section 2")  # ← row の後に表示されること！
```

### 5.2 Phase 1: 幅の動的更新

**目標**: パネルリサイズ時に子レイアウトが追従

**実装**:

```python
def layout(self, constraints: BoxConstraints = None) -> None:
    """レイアウト計算"""
    if constraints is None:
        constraints = BoxConstraints.loose(self.width, float('inf'))

    # 自身のサイズを確定
    size = self.measure(constraints)
    self.width = size.width
    self.height = size.height

    # 子要素を配置
    self.arrange(self.x, self.y)
```

**補足**:
- `LayoutKey` を生成し、HitTest/状態管理のキーとして保存
- パネルの `uid` と `layout_path` を組み合わせて衝突を回避

### 5.3 Phase 2: row() 均等分配

**目標**: row() 内のアイテムを均等分配

**実装**: 3.6 節の `RowElement.measure()` を参照

### 5.4 Phase 3: 検証

**テスト項目**:

1. `demo.layout_structure` が `demo.uilayout_reference` と同等に表示
2. パネルリサイズで全要素が追従
3. split(factor=0.3) が視覚的に 30%:70% に分割
4. scale_x/scale_y が正しく動作
5. alignment (LEFT/CENTER/RIGHT) が正しく動作

---

## Part 6: v2.0 との差分まとめ

| 項目 | v2.0 | v2.1 |
|------|------|------|
| IntrinsicSize | expand_x/expand_y あり | 削除（簡略化） |
| row() 返り値 | GPULayoutBuilder | RowElement（Container 直接） |
| split() 動作 | 曖昧 | 2列専用、factor で最初の列を指定 |
| Constraints 契約 | 未定義 | tight/loose を明文化 |
| row() 幅配分 | 均等のみ | fixed + flex を統一 |
| LayoutKey | 未検討 | 必須化 |
| オブジェクトプール | 未検討 | Phase 1 以降で検討 |
| 差分更新 | 未検討 | Phase 1 以降で検討 |
| 実装優先順位 | Phase 0 のみ詳細 | Phase 0-3 を詳細化 |

---

## Part 7: リスク評価

### 7.1 低リスク

| 項目 | 理由 |
|------|------|
| `_elements` 統合 | 内部変更のみ、API は変わらない |
| 均等分配実装 | 新機能追加、既存動作に影響なし |

### 7.2 中リスク

| 項目 | 理由 | 対策 |
|------|------|------|
| `layout()` の変更 | 全レイアウトに影響 | 段階的テスト |
| Constraints 導入 | 新概念 | v2/ に並行実装 |
| LayoutKey / HitTest | 入力系に影響 | フラグで段階的切替 |

### 7.3 高リスク

| 項目 | 理由 | 対策 |
|------|------|------|
| パフォーマンス劣化 | 2パスレイアウトのコスト | ベンチマーク |
| 既存コードの破壊 | test_layout.py 動作不良 | 互換レイヤー |

---

## Part 8: 結論

### 8.1 v2.1 の採用推奨

v2.0 の基本設計は正しい。v2.1 では以下を改良：

1. **IntrinsicSize 簡略化** → UILayout 互換性向上
2. **Builder API 修正** → Container 直接返却で混乱解消
3. **実装計画詳細化** → Phase 0-3 の明確な目標
4. **Constraints 契約** → root/child の width を明文化
5. **row() 幅配分の統一** → fixed + flex を明確化
6. **LayoutKey の導入** → 状態/入力の安定化
7. **パフォーマンス考慮** → Phase 1 以降で最適化

### 8.2 実装順序

```
Phase 0 (Blocker)
  └─ _elements 統合 + 追加順序保持
       ↓
Phase 1 (High)
  └─ Constraints 伝播 + 幅の動的更新
       ↓
Phase 2 (High)
  └─ row() 均等分配
       ↓
Phase 3 (Medium)
  └─ 検証 + パフォーマンス測定
       ↓
Phase 4 (Low, 将来)
  └─ オブジェクトプール / 差分更新
```

### 8.3 v2/ 並行実装の推奨維持

v2.0 の提案通り、`ui/gpu/v2/` で並行実装を推奨：

```
ui/gpu/v2/
├── __init__.py
├── elements.py      # LayoutElement, LeafElement, ContainerElement
├── containers.py    # RowElement, ColumnElement, SplitElement, BoxElement
├── constraints.py   # BoxConstraints, Size
├── panel.py         # GPUPanel (v2)
└── compat.py        # 既存 GPULayout との互換レイヤー
```

---

*Last Updated: 2026-01-19*
*Reviewer: Claude Opus 4.5*

