# GPULayout Architecture v2.0 - Clean Redesign

> Version: 0.1.0 (Draft)
> Created: 2026-01-19
> Status: **RFC (Request for Comments)**
> Related: `gpu_layout_issues_report.md`, Issue #100

---

## Executive Summary

現在の GPULayout は「UILayout 互換 API」を持ちながら、内部設計が UILayout と根本的に異なる。
本ドキュメントでは、世界的な UI フレームワークの設計原則を参考に、
GPULayout を**ゼロから再設計**するためのアーキテクチャを提案する。

---

## Part 1: 世界の UI フレームワーク分析

### 1.1 Flutter (Google)

**設計思想**: Declarative UI + Widget Tree + Constraints

```dart
// Flutter の Widget は全て同じ抽象型
abstract class Widget {
  Element createElement();
}

// レイアウトは Constraints ベース
class BoxConstraints {
  final double minWidth, maxWidth;
  final double minHeight, maxHeight;
}

// 3段階パイプライン
// 1. Build: Widget Tree 構築
// 2. Layout: Constraints → Size 決定
// 3. Paint: 描画
```

**Flutter の Layout Protocol**:
```
Parent                          Child
   │                              │
   │─── Constraints (min/max) ───→│
   │                              │ ← 子は制約内でサイズ決定
   │←─────── Size ────────────────│
   │                              │
   │─── Position (Offset) ───────→│ ← 親が位置を決定
```

**学ぶべき点**:
- 親が「制約」を渡し、子が「サイズ」を返す（Constraint-based Layout）
- Build → Layout → Paint の明確な分離
- 全要素が統一インターフェースを持つ

---

### 1.2 SwiftUI (Apple)

**設計思想**: Protocol-based + Declarative + Reactive

```swift
protocol View {
    associatedtype Body: View
    var body: Body { get }
}

// Layout は親から子への「提案」と子からの「応答」
struct ProposedViewSize {
    var width: CGFloat?   // nil = 「好きなだけ使っていい」
    var height: CGFloat?
}

// 子は提案を受けてサイズを決定
func sizeThatFits(_ proposal: ProposedViewSize) -> CGSize
```

**SwiftUI の Layout Protocol (iOS 16+)**:
```swift
protocol Layout {
    // 1. 子のサイズを問い合わせ
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout Cache) -> CGSize

    // 2. 子を配置
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout Cache)
}
```

**学ぶべき点**:
- 「提案 → 応答」モデル（Proposal-based Layout）
- `nil` は「制約なし」を意味する（Blender の `-1` と同様）
- キャッシュによる再計算の最適化

---

### 1.3 React (Meta) + CSS Flexbox/Grid

**設計思想**: Virtual DOM + Reconciliation + CSS Layout Engine

```jsx
// React は描画のみを担当、レイアウトはブラウザ（CSS）に委譲
function Row({ children }) {
  return <div style={{ display: 'flex', flexDirection: 'row' }}>{children}</div>;
}
```

**CSS Flexbox のレイアウトアルゴリズム**:
1. **Intrinsic Size** を計算（min-content, max-content）
2. **Available Space** を決定
3. **Flex Factor** に基づいて空間を分配
4. **Alignment** を適用

**学ぶべき点**:
- `flex-grow`, `flex-shrink` による空間分配
- `align-items`, `justify-content` による配置制御
- Intrinsic Size（固有サイズ）の概念

---

### 1.4 Qt (The Qt Company)

**設計思想**: Constraint-based + Size Policies + Layout Managers

```cpp
// Qt の Size Policy
enum Policy {
    Fixed,      // sizeHint() のみ
    Minimum,    // sizeHint() 以上
    Maximum,    // sizeHint() 以下
    Preferred,  // sizeHint() が理想、伸縮可
    Expanding,  // できるだけ大きく
    Ignored     // sizeHint() を無視
};

// 3つのサイズ
QSize minimumSizeHint();  // 最小サイズ
QSize sizeHint();         // 推奨サイズ
QSize maximumSize();      // 最大サイズ
```

**学ぶべき点**:
- Size Policy による柔軟な伸縮制御
- `minimumSize`, `sizeHint`, `maximumSize` の3段階
- Layout Manager パターン（HBox, VBox, Grid, Form）

---

### 1.5 Blender UILayout (現行)

**設計思想**: Immediate Mode GUI (IMGUI)

```python
def draw(self, context):
    layout = self.layout
    layout.label(text="Title")

    row = layout.row()
    row.label(text="Left")
    row.label(text="Right")

    layout.operator("mesh.primitive_cube_add")
```

**Blender UILayout の特徴**:
- `draw()` 内で構築と描画を同時に行う（Immediate Mode）
- 幅は描画時に親から子へ伝播
- 子の数は描画時に決定（事前に分からない）

**問題点（GPULayout で再現できていない）**:
- UILayout は「その場で」幅を決定し配置する
- GPULayout は「後で」まとめて配置しようとしている

---

## Part 2: 現在の GPULayout の問題構造

### 2.1 現在のアーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                      GPULayout                          │
├─────────────────────────────────────────────────────────┤
│  _items: list[LayoutItem]      ← label, button 等      │
│  _children: list[GPULayout]    ← row, column 等        │
├─────────────────────────────────────────────────────────┤
│  問題: _items と _children が分離                       │
│  問題: 追加順序が保持されない                           │
│  問題: 幅が構築時に固定される                           │
└─────────────────────────────────────────────────────────┘
```

### 2.2 処理フローの比較

**UILayout (Blender)**:
```
draw() 呼び出し
    │
    ├─ label("Title") ──────────────→ 即座に幅決定・配置
    │
    ├─ row = layout.row() ──────────→ row のための幅を確保
    │   ├─ row.label("Left") ───────→ row 内で即座に配置
    │   └─ row.label("Right") ──────→ row 内で即座に配置
    │
    └─ operator(...) ───────────────→ row の後に配置
```

**GPULayout (現在)**:
```
draw_panel() 呼び出し
    │
    ├─ label("Title") ──────────────→ _items[0] に追加
    │
    ├─ row = layout.row() ──────────→ _children[0] に追加
    │   ├─ row.label("Left") ───────→ row._items[0] に追加
    │   └─ row.label("Right") ──────→ row._items[1] に追加
    │
    └─ operator(...) ───────────────→ _items[1] に追加
    │
    │   ↓ layout() 呼び出し時
    │
    ├─ _items[0] (label) を配置
    ├─ _items[1] (operator) を配置  ← 順序が狂う！
    └─ _children[0] (row) を配置    ← 最後に配置される
```

---

## Part 3: 理想的なアーキテクチャ

### 3.1 設計原則

| # | 原則 | 説明 |
|---|------|------|
| 1 | **Unified Element Model** | 全要素を単一の抽象型で扱う |
| 2 | **Constraint Propagation** | 親から子へ制約を伝播 |
| 3 | **Two-pass Layout** | Measure → Arrange の2段階 |
| 4 | **Intrinsic Size** | 各要素が「自然サイズ」を報告 |
| 5 | **Build/Layout/Render Separation** | 構築・配置・描画の分離 |

### 3.2 新しいクラス階層

```
┌─────────────────────────────────────────────────────────┐
│                    LayoutElement                         │
│              (Abstract Base Class)                       │
├─────────────────────────────────────────────────────────┤
│  # Identity                                              │
│  parent: Optional[LayoutElement]                         │
│                                                          │
│  # Intrinsic Size (自然サイズ)                           │
│  def get_intrinsic_size() -> IntrinsicSize               │
│                                                          │
│  # Layout (制約を受けてサイズ・位置を決定)                │
│  def layout(constraints: BoxConstraints) -> Size         │
│                                                          │
│  # Render (描画)                                         │
│  def draw(rect: Rect, style: Style) -> None              │
│                                                          │
│  # Computed (レイアウト後に確定)                         │
│  x, y, width, height: float                              │
└─────────────────────────────────────────────────────────┘
            ▲                    ▲
            │                    │
   ┌────────┴────────┐  ┌───────┴────────┐
   │   LeafElement   │  │ ContainerElement│
   │ (終端要素)       │  │ (コンテナ要素)  │
   ├─────────────────┤  ├─────────────────┤
   │ LabelElement    │  │ RowElement      │
   │ ButtonElement   │  │ ColumnElement   │
   │ SeparatorElement│  │ BoxElement      │
   │ SliderElement   │  │ SplitElement    │
   │ ...             │  │ ...             │
   └─────────────────┘  └─────────────────┘
```

### 3.3 BoxConstraints（制約）

```python
@dataclass
class BoxConstraints:
    """親から子へ渡される制約"""
    min_width: float = 0.0
    max_width: float = float('inf')
    min_height: float = 0.0
    max_height: float = float('inf')

    @classmethod
    def tight(cls, width: float, height: float) -> 'BoxConstraints':
        """固定サイズの制約"""
        return cls(min_width=width, max_width=width,
                   min_height=height, max_height=height)

    @classmethod
    def loose(cls, width: float, height: float) -> 'BoxConstraints':
        """最大サイズの制約（0 から指定値まで）"""
        return cls(max_width=width, max_height=height)

    def constrain(self, size: 'Size') -> 'Size':
        """サイズを制約内に収める"""
        return Size(
            width=max(self.min_width, min(size.width, self.max_width)),
            height=max(self.min_height, min(size.height, self.max_height))
        )
```

### 3.4 IntrinsicSize（固有サイズ）

```python
@dataclass
class IntrinsicSize:
    """要素の自然なサイズ"""
    min_width: float      # 最小幅（これ以下には縮められない）
    natural_width: float  # 自然幅（理想的なサイズ）
    min_height: float     # 最小高さ
    natural_height: float # 自然高さ

    # オプション: 拡張ポリシー
    expand_x: bool = False  # 水平方向に拡張したいか
    expand_y: bool = False  # 垂直方向に拡張したいか
```

### 3.5 ContainerElement（コンテナ）

```python
class ContainerElement(LayoutElement):
    """子要素を持つコンテナ"""

    def __init__(self):
        super().__init__()
        self._children: list[LayoutElement] = []  # 統一リスト！
        self.direction: Direction = Direction.VERTICAL
        self.spacing: float = 4.0
        self.align: bool = False

    def add(self, element: LayoutElement) -> LayoutElement:
        """子要素を追加（追加順序を保持）"""
        element.parent = self
        self._children.append(element)
        return element

    def get_intrinsic_size(self) -> IntrinsicSize:
        """子要素の固有サイズから自身の固有サイズを計算"""
        if self.direction == Direction.VERTICAL:
            # 垂直: 幅は最大、高さは合計
            max_width = 0.0
            total_height = 0.0
            for child in self._children:
                child_size = child.get_intrinsic_size()
                max_width = max(max_width, child_size.natural_width)
                total_height += child_size.natural_height
            total_height += self.spacing * max(0, len(self._children) - 1)
            return IntrinsicSize(
                min_width=max_width,
                natural_width=max_width,
                min_height=total_height,
                natural_height=total_height
            )
        else:
            # 水平: 幅は合計、高さは最大
            total_width = 0.0
            max_height = 0.0
            for child in self._children:
                child_size = child.get_intrinsic_size()
                total_width += child_size.natural_width
                max_height = max(max_height, child_size.natural_height)
            total_width += self.spacing * max(0, len(self._children) - 1)
            return IntrinsicSize(
                min_width=total_width,
                natural_width=total_width,
                min_height=max_height,
                natural_height=max_height
            )

    def layout(self, constraints: BoxConstraints) -> Size:
        """子要素を配置"""
        if self.direction == Direction.VERTICAL:
            return self._layout_vertical(constraints)
        else:
            return self._layout_horizontal(constraints)

    def _layout_horizontal(self, constraints: BoxConstraints) -> Size:
        """水平レイアウト - 幅を均等分配"""
        n = len(self._children)
        if n == 0:
            return Size(0, 0)

        # 利用可能幅を計算
        available_width = constraints.max_width
        total_spacing = self.spacing * (n - 1)
        content_width = available_width - total_spacing

        # 各子の幅を均等に分配
        child_width = content_width / n

        # 子を配置
        x = 0.0
        max_height = 0.0
        for child in self._children:
            child_constraints = BoxConstraints(
                min_width=child_width,
                max_width=child_width,
                min_height=constraints.min_height,
                max_height=constraints.max_height
            )
            child_size = child.layout(child_constraints)
            child.x = x
            child.y = 0
            x += child_width + self.spacing
            max_height = max(max_height, child_size.height)

        # 高さを揃える
        for child in self._children:
            child.height = max_height

        return Size(available_width, max_height)
```

---

## Part 4: 新しい GPULayout API

### 4.1 Builder Pattern（構築）

```python
class GPULayoutBuilder:
    """UILayout 互換 API を提供するビルダー"""

    def __init__(self, root: ContainerElement):
        self._stack: list[ContainerElement] = [root]

    @property
    def _current(self) -> ContainerElement:
        return self._stack[-1]

    def label(self, *, text: str = "", icon: str = "NONE") -> LabelElement:
        element = LabelElement(text=text, icon=icon)
        self._current.add(element)
        return element

    def operator(self, idname: str, *, text: str = "", icon: str = "NONE") -> ButtonElement:
        element = ButtonElement(text=text or idname, icon=icon, operator=idname)
        self._current.add(element)
        return element

    def separator(self, *, factor: float = 1.0) -> SeparatorElement:
        element = SeparatorElement(factor=factor)
        self._current.add(element)
        return element

    def row(self, align: bool = False) -> 'GPULayoutBuilder':
        """新しい行を開始し、そのビルダーを返す"""
        container = RowElement(align=align)
        self._current.add(container)
        # 新しいビルダーを返す（チェーン可能）
        return GPULayoutBuilder(container)

    def column(self, align: bool = False) -> 'GPULayoutBuilder':
        """新しい列を開始し、そのビルダーを返す"""
        container = ColumnElement(align=align)
        self._current.add(container)
        return GPULayoutBuilder(container)

    def box(self) -> 'GPULayoutBuilder':
        """ボックスを開始し、そのビルダーを返す"""
        container = BoxElement()
        self._current.add(container)
        return GPULayoutBuilder(container)

    def split(self, *, factor: float = 0.5, align: bool = False) -> 'GPULayoutBuilder':
        """分割レイアウトを開始"""
        container = SplitElement(factor=factor, align=align)
        self._current.add(container)
        return GPULayoutBuilder(container)
```

### 4.2 使用例

```python
def draw_panel(self, layout: GPULayoutBuilder, context):
    # セクション 1
    layout.label(text="1. row() - Horizontal Layout")

    row = layout.row()
    row.label(text="Left")
    row.label(text="Center")
    row.label(text="Right")

    layout.label(text="row(align=True)")

    row2 = layout.row(align=True)
    row2.operator("mesh.primitive_cube_add", text="A")
    row2.operator("mesh.primitive_cube_add", text="B")
    row2.operator("mesh.primitive_cube_add", text="C")

    # セクション 2
    layout.label(text="2. column() - Vertical Layout")

    row3 = layout.row()
    for i in range(3):
        col = row3.column()
        col.label(text=f"Column {i+1}")
        col.operator("mesh.primitive_cube_add", text=f"Btn {i+1}-A")
        col.operator("mesh.primitive_cube_add", text=f"Btn {i+1}-B")
```

### 4.3 レイアウト実行

```python
class GPUPanel:
    """GPUPanelMixin の後継"""

    def __init__(self, width: float, style: Style):
        self._root = ContainerElement()
        self._root.direction = Direction.VERTICAL
        self._width = width
        self._style = style

    def build(self, draw_func: Callable[[GPULayoutBuilder, Context], None], context: Context):
        """Build Phase: 要素ツリーを構築"""
        self._root._children.clear()
        builder = GPULayoutBuilder(self._root)
        draw_func(builder, context)

    def layout(self):
        """Layout Phase: サイズと位置を計算"""
        constraints = BoxConstraints.loose(self._width, float('inf'))
        self._root.layout(constraints)

    def draw(self, x: float, y: float):
        """Render Phase: 描画"""
        self._root.x = x
        self._root.y = y
        self._root.draw(self._style)
```

---

## Part 5: レイアウトアルゴリズム詳細

### 5.1 Row/Column の幅分配アルゴリズム

**Flutter の Flex アルゴリズムを参考**:

```python
def _layout_horizontal(self, constraints: BoxConstraints) -> Size:
    """水平レイアウト - Flex 風の幅分配"""

    # Phase 1: 固有サイズを収集
    intrinsic_sizes = [child.get_intrinsic_size() for child in self._children]

    # Phase 2: 拡張要素と固定要素を分類
    fixed_width = 0.0
    expand_count = 0
    for i, child in enumerate(self._children):
        size = intrinsic_sizes[i]
        if size.expand_x:
            expand_count += 1
        else:
            fixed_width += size.natural_width

    # Phase 3: 利用可能幅を計算
    available_width = constraints.max_width
    total_spacing = self.spacing * (len(self._children) - 1)
    remaining_width = available_width - total_spacing - fixed_width

    # Phase 4: 拡張要素に幅を分配
    expand_width = remaining_width / expand_count if expand_count > 0 else 0

    # Phase 5: 子を配置
    x = 0.0
    max_height = 0.0
    for i, child in enumerate(self._children):
        size = intrinsic_sizes[i]
        child_width = expand_width if size.expand_x else size.natural_width

        child_constraints = BoxConstraints.tight(child_width, constraints.max_height)
        child_size = child.layout(child_constraints)

        child.x = x
        child.y = 0
        child.width = child_width
        child.height = child_size.height

        x += child_width + self.spacing
        max_height = max(max_height, child_size.height)

    return Size(available_width, max_height)
```

### 5.2 split() の実装

```python
class SplitElement(ContainerElement):
    """分割レイアウト（2列限定）"""

    def __init__(self, factor: float = 0.5, align: bool = False):
        super().__init__()
        self.direction = Direction.HORIZONTAL
        self.factor = factor
        self.align = align

    def _layout_horizontal(self, constraints: BoxConstraints) -> Size:
        """factor に基づいて幅を分配"""
        n = len(self._children)
        if n == 0:
            return Size(0, 0)

        available_width = constraints.max_width
        total_spacing = self.spacing * (n - 1)
        content_width = available_width - total_spacing

        # factor に基づいて幅を計算
        if n == 2 and self.factor > 0:
            widths = [content_width * self.factor, content_width * (1 - self.factor)]
        else:
            # 3列以上または factor=0 なら均等分配
            widths = [content_width / n] * n

        # 子を配置
        x = 0.0
        max_height = 0.0
        for i, child in enumerate(self._children):
            child_constraints = BoxConstraints(
                min_width=widths[i], max_width=widths[i],
                min_height=0, max_height=constraints.max_height
            )
            child_size = child.layout(child_constraints)
            child.x = x
            child.y = 0
            child.width = widths[i]
            child.height = child_size.height
            x += widths[i] + self.spacing
            max_height = max(max_height, child_size.height)

        return Size(available_width, max_height)
```

---

## Part 6: 移行戦略

### 6.1 段階的移行

| Phase | 内容 | リスク |
|-------|------|--------|
| **Phase A** | 新アーキテクチャを `ui/gpu/v2/` に実装 | 低（既存に影響なし） |
| **Phase B** | `test_layout.py` で新旧比較テスト | 低 |
| **Phase C** | 新アーキテクチャに切り替え | 中 |
| **Phase D** | 旧コードを削除 | 低 |

### 6.2 ファイル構成案

```
ui/gpu/v2/
├── __init__.py
├── elements/
│   ├── __init__.py
│   ├── base.py          # LayoutElement, ContainerElement
│   ├── leaf.py          # LabelElement, ButtonElement, etc.
│   └── container.py     # RowElement, ColumnElement, BoxElement
├── constraints.py       # BoxConstraints, IntrinsicSize, Size
├── builder.py           # GPULayoutBuilder
├── panel.py             # GPUPanel (v2)
└── style.py             # Style (既存を継承)
```

### 6.3 既存コードとの互換性

```python
# 互換レイヤー（移行期間中）
class GPULayout(GPULayoutBuilder):
    """既存 API との互換性を提供"""

    def __init__(self, x: float, y: float, width: float, ...):
        root = ContainerElement()
        super().__init__(root)
        self._x = x
        self._y = y
        self._width = width
        # ...

    def draw(self):
        """旧 API: build + layout + draw を一度に実行"""
        constraints = BoxConstraints.loose(self._width, float('inf'))
        self._root.layout(constraints)
        self._root.x = self._x
        self._root.y = self._y
        self._root.draw(self._style)
```

---

## Part 7: 設計の比較

### 7.1 現在 vs 新アーキテクチャ

| 項目 | 現在 | 新アーキテクチャ |
|------|------|-----------------|
| 要素管理 | `_items` + `_children` 分離 | `_children` 統一 |
| 追加順序 | 保持されない | 保持される |
| 幅計算 | 構築時に固定 | Layout Phase で動的計算 |
| 均等分配 | なし | Flex 風アルゴリズム |
| リサイズ対応 | 手動 | 自動（Constraints 再伝播） |
| コード量 | 約2000行 | 約1000行（予想） |

### 7.2 API 互換性

| API | 現在 | 新アーキテクチャ | 互換性 |
|-----|------|-----------------|--------|
| `label()` | ✅ | ✅ | 100% |
| `operator()` | ✅ | ✅ | 100% |
| `separator()` | ✅ | ✅ | 100% |
| `row()` | ✅ | ✅ | 100% |
| `column()` | ✅ | ✅ | 100% |
| `box()` | ✅ | ✅ | 100% |
| `split()` | ✅ | ✅ | 100% |
| `prop()` | ✅ | ✅ | 100% |
| `scale_x/y` | ⚠️ | ✅ | 改善 |
| `alignment` | ⚠️ | ✅ | 改善 |

---

## Part 8: 推奨事項

### 8.1 実装推奨

1. **新アーキテクチャを採用する**
   - 現在の問題を根本から解決できる
   - 将来の拡張が容易
   - コード量が減る（保守性向上）

2. **Flutter の Constraints モデルを採用する**
   - 親→子の制約伝播が明確
   - 動的リサイズに自然に対応
   - 業界標準のアプローチ

3. **Builder パターンを維持する**
   - UILayout 互換 API を提供
   - 既存のユーザーコード（Custom モード）が動く

### 8.2 実装しないこと

1. **React の Virtual DOM/Reconciliation**
   - PME では過剰な複雑さ
   - 毎フレーム再構築で十分

2. **CSS Grid のような複雑なレイアウト**
   - UILayout 互換が目標
   - Grid が必要になったら追加

3. **アニメーションフレームワーク**
   - Phase 2 以降で検討
   - まずは静的レイアウトを完成させる

---

## 結論

GPULayout の問題は「パッチ」では解決できない。
**Flutter の Constraints モデル**を参考に、**統一要素モデル**と**2パスレイアウト**を採用した新アーキテクチャへの移行を推奨する。

移行は `ui/gpu/v2/` で並行開発し、テストで検証後に切り替えることでリスクを最小化できる。

---

*Last Updated: 2026-01-19*
