# GPULayout Architecture v3 - Long-Term UI Framework Plan

> Version: 0.2.1
> Created: 2026-01-19
> Updated: 2026-01-19 (実機テスト結果を反映: scale_x + alignment 相互作用)
> Status: **RFC (Request for Comments)**
> Related: `gpu_layout_issues_report.md`, `gpu_layout_architecture_v2.1.md`, `blender_source_investigation.md`, Issue #104
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

## 5. SizingPolicy（Blender UILayout 互換モデル）

> **Note**: Blender ソースコード調査結果に基づく（`blender_source_investigation.md` 参照）

```
SizingPolicy:
  estimated_width: float   # estimate() で計算されたサイズ
  fixed_width: float?      # ui_units_x で上書きされた固定幅
  is_fixed: bool = false   # fixed_size フラグ
  min_width: float = 0
  max_width: float = INF
```

**Blender 互換ルール**:
- `alignment = EXPAND` の場合のみ、推定サイズの比率で幅を拡大
- `ui_units_x` は estimate 結果を**完全上書き**し、`is_fixed = true` を設定
- `scale_x` は **子アイテムのサイズを直接倍率**（estimate 前に適用）

### 5.1 幅配分アルゴリズム（Blender ui_item_fit 互換）

```python
def distribute_width(children, available_width, gap, alignment):
    """Row の幅配分アルゴリズム（Blender interface_layout.cc:347-382 準拠）"""
    gaps_total = gap * (len(children) - 1)
    available = available_width - gaps_total

    # 各子の推定幅を合計
    total_estimated = sum(c.estimated_width for c in children)

    if total_estimated == 0:
        return  # 何もしない

    for child in children:
        if available == 0 or total_estimated == 0:
            child.width = child.estimated_width
            continue

        if total_estimated > available:
            # 内容が利用可能幅より大きい → 比例縮小
            child.width = (child.estimated_width * available) / total_estimated
        elif alignment == Alignment.EXPAND:
            # EXPAND: 比例拡大
            child.width = (child.estimated_width * available) / total_estimated
        else:
            # LEFT/CENTER/RIGHT: 元のサイズを維持
            child.width = child.estimated_width
```

### 5.2 scale_x の動作（⚠️ v3.0.2 で追記）

Blender の `scale_x` は **estimate_impl 前に子アイテムのサイズを直接倍率** する。

```python
def apply_scale(layout, scale_x, scale_y):
    """scale_x/y の適用（Blender interface_layout.cc:5265-5287 準拠）"""
    for child in layout.children:
        if isinstance(child, Layout):
            apply_scale(child, scale_x, scale_y)  # 再帰

        if scale_x != 0.0:
            child.offset_x *= scale_x
            child.size_x *= scale_x  # ← サイズを直接倍率

        if scale_y != 0.0:
            child.offset_y *= scale_y
            child.size_y *= scale_y
```

**処理順序**:
1. 子の `estimate()` を再帰呼び出し
2. `scale_x/y` を子アイテムに適用（ui_item_scale）
3. `estimate_impl()` でサイズ計算
4. `ui_units_x` が設定されていれば上書き

**⚠️ 実機テスト結果（2026-01-19）**:

| alignment | scale_x の効果 | 理由 |
|-----------|---------------|------|
| `EXPAND` | **見えにくい** | 比率 1:1 → 2:2 = 1:1、利用可能幅を同比率で配分 |
| `LEFT/CENTER/RIGHT` | **見える** | 自然サイズを維持するため、倍率効果が visible |

```python
# scale_x の効果を確認するには alignment=LEFT を使用
row = layout.row()
row.alignment = 'LEFT'
row.scale_x = 2.0  # 効果が visible
row.operator("mesh.primitive_cube_add", text="A")
```

### 5.3 alignment と幅の関係

| 設定 | 意味 | 子の幅 |
|------|------|--------|
| `alignment = EXPAND` | 子が利用可能幅を全て埋める | 推定サイズの比率で拡大 |
| `alignment = LEFT` | 子は自然サイズを維持 | 余白は右に |
| `alignment = CENTER` | 子は自然サイズを維持 | 余白は左右均等 |
| `alignment = RIGHT` | 子は自然サイズを維持 | 余白は左に |

**重要**: alignment が EXPAND 以外の場合、子は「推定サイズ」を超えて拡張しない。

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

> **⚠️ v3.0.2 で修正**: Blender ソースコード調査により暗黙 column は存在しないことが判明

- factor は **最初のアイテムの割合**
- 2番目以降のアイテムは残りを等分
- **暗黙の column 生成はない** — 直接追加されたアイテムがそれぞれ列として扱われる

**Split 幅計算アルゴリズム** (`interface_layout.cc:4650-4690`):

```python
def resolve_split(items, total_width, gap, percentage):
    """Split の幅配分（Blender 準拠）"""
    if percentage == 0.0:
        percentage = 1.0 / len(items)  # 均等分割

    available = total_width - gap * (len(items) - 1)
    first_width = available * percentage
    remaining = available - first_width

    for i, item in enumerate(items):
        if i == 0:
            item.width = first_width
        else:
            # 2番目以降: 残りを (n-1) で均等分割
            item.width = remaining / (len(items) - 1)
```

**使用例**:

```python
# パターン1: column を明示的に使う（推奨）
split = layout.split(factor=0.3)
col1 = split.column()  # items[0] → 30%
col1.label(text="Label A")
col1.label(text="Label B")
col2 = split.column()  # items[1] → 70%
col2.label(text="Label C")

# パターン2: 直接アイテムを追加（各アイテムが列として扱われる）
split = layout.split(factor=0.3)
split.label(text="30%")   # items[0] → 30%
split.label(text="70%")   # items[1] → 70%
# ⚠️ 2つの label が横に並ぶ（暗黙の column は生成されない）

# パターン3: 3列以上
split = layout.split(factor=0.25)
split.column()  # 25%
split.column()  # 37.5% (残り75%の半分)
split.column()  # 37.5%
```

**重要な違い**:
- パターン1: 列内に複数のアイテムを縦に配置できる
- パターン2: 各 label が独立した列として扱われる（縦配置不可）

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

# explicit_key を指定した場合は安定 ID を優先
# 最終キー = "demo_quick_viewport:my_button_id"
```

**LayoutKey の生成ルール**:
1. `panel_uid`: パネル固有ID（重複チェックに使用）
2. `layout_path`: Build 時の構造パス（自動生成）
3. `explicit_key`: ユーザー指定のキー（オプション）

```python
# 明示的キーの指定（リストなど順序が変わる場合に有効）
for i, item in enumerate(items):
    layout.button(text=item.name, key=f"item_{item.id}")

# explicit_key は panel 内で一意であることが望ましい
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

### 10.2 scale_x 動作検証

```python
# テストケース: scale_x の効果
row = layout.row()
row.scale_x = 2.0  # 子アイテムのサイズを 2 倍
row.operator("mesh.primitive_cube_add", text="A")
row.operator("mesh.primitive_cube_add", text="B")

# 期待: A と B のボタン幅がそれぞれ 2 倍になる
# ソースコード参照: interface_layout.cc:5249-5273
```

### 10.2b ui_units_x + 推定サイズ混在検証

```python
# テストケース: ui_units_x と通常アイテムの混在
row = layout.row()
sub = row.row()
sub.ui_units_x = 5  # 固定幅 (≒100px)
sub.label(text="Fixed")
row.label(text="Flex 1")
row.label(text="Flex 2")

# 期待: [100px][残りを推定サイズ比で分配]
# ソースコード参照: interface_layout.cc:5297-5300
```

### 10.3 LayoutKey 安定性検証

```python
# テストケース: hover 中にリスト順序が変わる
items = [A, B, C]  # B を hover 中
items = [A, C, B]  # 順序変更

# 期待: B の hover が維持される（explicit_key で識別）
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
v2.1 の改善点を保持しつつ、**キー安定性・推定サイズベース配分・パイプライン分離**を明文化する。

### Blender ソースコード調査による修正点

| 項目 | 当初の仮定 | 実際の動作 |
|------|-----------|-----------|
| scale_x | weight の倍率 | 子サイズの直接倍率 |
| split 暗黙 column | 自動生成 | **なし** |
| 幅配分 | weight ベース | 推定サイズベース |
| alignment | weight に影響 | 拡張するかどうかのみ |

詳細は `blender_source_investigation.md` を参照。

---

## 12. 参照ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| `blender_source_investigation.md` | Blender ソースコード調査レポート |
| `gpu_layout_architecture_v2.1.md` | 前バージョンのアーキテクチャ |
| `gpu_layout_issues_report.md` | 問題分析レポート |

---

*Last Updated: 2026-01-22*
