# GPULayout Architecture v3 - Long-Term UI Framework Plan

> Version: 0.1.0
> Created: 2026-01-19
> Status: **RFC (Request for Comments)**
> Related: `gpu_layout_issues_report.md`, `gpu_layout_architecture_v2.1.md`, Issue #100
> Reviewer: Codex (GPT-5)

---

## 0. 目的 / 非ゴール

### 目的
- **UILayout の挙動を GPU で等価再現**（row/column/split/box/scale/alignment）
- **長期運用に耐える安定 API**（構造/描画/入力が分離）
- **高い保守性**（新コンテナ・新ウィジェットを安全に追加可能）

### 非ゴール
- HTML/CSS 互換の網羅的レイアウト
- 物理ベース UI や 3D UI

---

## 1. 設計原則（世界的 UI フレームワーク準拠）

1. **Constraints go down, sizes go up, positions go down**（Flutter/Qt 系）
2. **追加順序の厳密保持**（_elements 単一リスト）
3. **Build/Layout/Render/HitTest を分離**
4. **安定キーによる状態維持**（SwiftUI/React の Key）
5. **Flex/Basis で幅配分を統一**（Yoga/Flexbox）
6. **Layout は deterministic**（同じ入力で同じ出力）

---

## 2. パイプライン（v3 の骨格）

```
draw() 呼び出し
  ├─ Build: UI コードで LayoutNode を構築
  ├─ Measure: BoxConstraints を伝播し Size を決定
  ├─ Arrange: 位置を確定（Rect を確定）
  ├─ Paint: RenderCommand を生成（GPU バッチへ）
  └─ HitTest: 入力解決用ツリーを構築
```

**重要**: Build と Layout を分離しない限り、row/split の再現精度は上がらない。

---

## 3. コアデータモデル

### 3.1 LayoutNode

```
LayoutNode:
  key: LayoutKey          # panel_uid + path + explicit_key
  parent: LayoutNode?
  rect: Rect              # arrange で確定
  style: StyleRef
  sizing: SizingPolicy    # basis/flex/min/max

  measure(constraints) -> Size
  arrange(x, y) -> None
  paint(painter) -> None
  hit_test(x, y) -> HitResult?
```

### 3.2 LeafNode / ContainerNode

- **LeafNode**: label/button/prop など終端要素
- **ContainerNode**: row/column/split/box など子を持つ要素

### 3.3 RenderCommand

- Draw call を蓄積し GPU バッチに渡す
- レイアウトツリーから分離（描画最適化のため）

---

## 4. Constraints と Units

### 4.1 BoxConstraints

```
min_width <= width <= max_width
min_height <= height <= max_height
```

### 4.2 Root Constraints

- パネル幅・リージョン幅は **tight**
- 高さは **loose**（必要分だけ伸長）
- `set_region_bounds()` で root constraints を更新 → **必ず re-layout**

### 4.3 Pixel Snap / DPI

- `ui_scale`, `dpi_scale` を LayoutContext に集約
- `Rect` は最終段階でピクセルスナップ

---

## 5. SizingPolicy（equal + fixed + flex の統一モデル）

```
SizingPolicy:
  basis_width: float?  # 固定幅（ui_units_x 等）
  weight: float = 1.0  # flex weight（0 = 固定幅のみ）
  min_width: float = 0
  max_width: float = INF
```

**Blender 互換ルール**:
- row() の既定は `weight=1`（= 均等分配）
- `ui_units_x` は `basis_width` を設定（固定幅）
- `scale_x` は weight の倍率として解釈

### 5.1 幅配分アルゴリズム（Flex Row）

```python
def distribute_width(children, available_width, gap):
    """Row の幅配分アルゴリズム"""
    # 1. 固定幅（basis）を先に確保
    fixed_total = sum(c.basis_width or 0 for c in children)

    # 2. 残り幅を計算
    gaps_total = gap * (len(children) - 1)
    remaining = available_width - fixed_total - gaps_total

    # 3. weight の合計を計算
    weight_total = sum(c.weight for c in children if c.basis_width is None)

    # 4. 各子の幅を決定
    for child in children:
        if child.basis_width is not None:
            child.width = child.basis_width
        elif weight_total > 0:
            child.width = remaining * (child.weight / weight_total)
        else:
            child.width = 0
```

### 5.2 alignment と weight の関係

| 設定 | 意味 | weight の扱い |
|------|------|--------------|
| `alignment = EXPAND` | 子が利用可能幅を全て埋める | weight に従って分配 |
| `alignment = LEFT` | 子は min(natural, weight分配) | 余白は右に |
| `alignment = CENTER` | 子は min(natural, weight分配) | 余白は左右均等 |
| `alignment = RIGHT` | 子は min(natural, weight分配) | 余白は左に |

**重要**: alignment が EXPAND 以外の場合、子は「自然サイズ」を超えて拡張しない。

---

## 6. コンテナ仕様

### 6.1 Column

- 縦方向に積む
- 幅は親 constraints の `max_width`（root は tight）
- 高さは子の合計 + gap

### 6.2 Row（Flex Row）

1. fixed/basis を先に確保  
2. 残り幅を weight で分配  
3. `alignment` は余りが出た場合の主軸配置  
4. `align=True` は gap=0

### 6.3 Split

- factor は **最初の列の割合**
- 2列目以降は残りを等分
- `split.label()` は暗黙の column

**Split 詳細仕様**:

```python
# 2列（推奨）
split = layout.split(factor=0.3)
col1 = split.column()  # 30%
col2 = split.column()  # 70%

# 3列以上（非推奨だが許容）
split = layout.split(factor=0.25)
col1 = split.column()  # 25%
col2 = split.column()  # 37.5% (残り75%の半分)
col3 = split.column()  # 37.5%

# 暗黙の column
split = layout.split(factor=0.3)
split.label(text="30%")   # ← 暗黙の column(index=0) に追加
split.label(text="70%")   # ← 暗黙の column(index=1) に追加
```

**暗黙 column のルール**:
1. `split.column()` を呼ばずに `split.label()` 等を呼んだ場合
2. 内部で自動的に column を生成し、そこに追加
3. 次の `split.xxx()` 呼び出しは次の column に追加
4. これは UILayout の動作と一致（要実機テスト）

### 6.4 Box

- padding を持つ container
- 背景/枠線は paint で描画

---

## 7. 入力と状態

### 7.1 LayoutKey

```
LayoutKey = (panel_uid, layout_path, explicit_key)

例:
  panel_uid = "demo_quick_viewport"
  layout_path = "root.row[0].button[1]"
  explicit_key = None  # または "my_button_id"

最終キー = "demo_quick_viewport:root.row[0].button[1]"
```

**LayoutKey の生成ルール**:
1. `panel_uid`: パネル固有ID（重複チェックに使用）
2. `layout_path`: Build 時の構造パス（自動生成）
3. `explicit_key`: ユーザー指定のキー（オプション）

```python
# 明示的キーの指定（リストなど順序が変わる場合に有効）
for i, item in enumerate(items):
    layout.button(text=item.name, key=f"item_{item.id}")
```

**キー安定性の重要性**:
- hover/active 状態は LayoutKey に紐づく
- IMGUI で毎フレーム再構築しても、同じキーなら状態を維持
- キーが変わると hover が解除される → UX 劣化

### 7.2 HitTest

- Paint と同じ順序で HitList を構築
- 入力解決は **逆順**（最前面から判定）

**HitTest の流れ**:
```
1. Build: LayoutNode ツリーを構築
2. Layout: Rect を確定
3. Paint: 描画 + HitRect を登録（描画順）
4. Event: マウス座標から HitRect を逆順検索
5. Dispatch: 最前面の HitRect に対応するノードにイベントを送信
```

**既存 HitTestManager との互換**:
- 現在の `HitTestManager` は HitRect を `tag` で管理
- v3 では `tag` → `LayoutKey` に移行
- 移行中は両方をサポート（`tag` は `LayoutKey` の alias として扱う）

---

## 8. パフォーマンス戦略

1. **Dirty Flags**
   - LayoutDirty: サイズ/位置が変わった
   - PaintDirty: 見た目だけ変わった
2. **Structural Hash** で Build の再構築判定
3. **Element Pool** は Phase 2 以降で導入

---

## 9. 移行計画（v2.x → v3）

### Phase 0: 追加順序修正
- `_elements` 統合（既存 GPULayout でも対応）

### Phase 1: Constraints / Flex 実装
- row/column/split の配分ロジックを v3 規約へ

### Phase 2: LayoutKey / HitTest
- 既存 HitTestManager を LayoutKey ベースに移行

### Phase 3: 差分更新 / プール
- 必要なら ElementPool を導入

---

## 10. 検証項目

### 10.1 基本検証

1. `demo.layout_structure` と `demo.uilayout_reference` の完全一致
2. パネルリサイズ追従
3. split(factor=0.3) の視覚比率
4. scale_x/scale_y の互換性
5. alignment (LEFT/CENTER/RIGHT) の互換性

### 10.2 Fixed + Flex 混在検証

```python
# テストケース: ui_units_x と均等分配の混在
row = layout.row()
row.label(text="Fixed 100px")  # ui_units_x = 5 (≒100px)
row.label(text="Flex 1")       # weight = 1
row.label(text="Flex 2")       # weight = 2

# 期待: [100px][残りの1/3][残りの2/3]
```

### 10.3 LayoutKey 安定性検証

```python
# テストケース: hover 中にリスト順序が変わる
items = [A, B, C]  # B を hover 中
items = [A, C, B]  # 順序変更

# 期待: B の hover が維持される（key で識別）
# NG: hover が解除される or C に移る
```

### 10.4 Constraints 伝播検証

```python
# テストケース: root 幅変更時の再配分
panel.width = 300
# → 全子要素が 300px を基準に再配分

panel.width = 400
# → 全子要素が 400px を基準に再配分
# → 固定幅（basis）は変わらず、flex のみ伸縮
```

---

## 11. 結論

v3 は **UILayout 完全模倣 + 長期運用**を同時に満たす最小構成である。
v2.1 の改善点を保持しつつ、**キー安定性・Flex配分・パイプライン分離**を明文化する。

---

*Last Updated: 2026-01-19*
