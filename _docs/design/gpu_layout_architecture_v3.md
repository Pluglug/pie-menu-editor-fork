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
  weight: float = 1.0  # flex weight
  min_width: float = 0
  max_width: float = INF
```

**Blender 互換ルール**:
- row() の既定は `weight=1`（= 均等分配）
- `ui_units_x` は `basis_width` を設定（固定幅）
- `scale_x` は weight の倍率として解釈

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

### 6.4 Box

- padding を持つ container
- 背景/枠線は paint で描画

---

## 7. 入力と状態

### 7.1 LayoutKey

```
LayoutKey = (panel_uid, layout_path, explicit_key)
```

- HitTest/hover/active 状態は LayoutKey に紐づく
- IMGUI でも状態が安定する

### 7.2 HitTest

- Paint と同じ順序で HitList を構築
- 入力解決は **逆順**（最前面から判定）

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

1. `demo.layout_structure` と `demo.uilayout_reference` の完全一致
2. パネルリサイズ追従
3. split(factor=0.3) の視覚比率
4. scale_x/scale_y の互換性
5. alignment (LEFT/CENTER/RIGHT) の互換性

---

## 11. 結論

v3 は **UILayout 完全模倣 + 長期運用**を同時に満たす最小構成である。
v2.1 の改善点を保持しつつ、**キー安定性・Flex配分・パイプライン分離**を明文化する。

---

*Last Updated: 2026-01-19*
