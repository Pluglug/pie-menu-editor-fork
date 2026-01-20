# GPULayout Implementation Milestones

> Version: 1.1.1
> Created: 2026-01-20
> Updated: 2026-01-20 (split factor=0 の均等分割修正を反映)
> Status: **Active**
> Primary Spec: `gpu_layout_architecture_v3.md`
> Implementation Reference: `gpu_layout_architecture_v2.1.md` (構造・API 形のみ)
> Related Issues: #100, #104, #115, #116

---

## 設計方針

**v3 を主軸に、v2.1 は構造・API 形の参照のみに使用**

### 理由

1. **v3 は検証済み**
   - `blender_source_investigation.md` で Blender ソースコード（`interface_layout.cc`）を調査
   - `test_uilayout_behavior.py` で実機テストを実施
   - `scale_x + alignment` の相互作用を実証

2. **v2.1 の重要な誤りを v3 で修正済み**

   | 項目 | v2.1 (誤) | v3 (正) |
   |------|----------|---------|
   | `scale_x` | weight の倍率として適用 | 子アイテムサイズの直接倍率（子 measure 後、親 measure_impl 前） |
   | `split.label()` | 暗黙 column を自動生成 | 暗黙 column なし、直接追加されたアイテムが列として扱われる |
   | 幅配分 | weight ベース | estimated_width 比例 |

3. **v2.1 の参照範囲を限定**
   - [Done] `ContainerElement` のクラス構造
   - [Done] `row()`, `column()`, `split()` のメソッドシグネチャ
   - [Done] オブジェクトプール戦略（Phase 3）
   - [x] ~~`RowElement.measure()` の配分ロジック~~ → v3 を使用

### 実装時の参照順序

| 優先度 | 参照先 | 用途 |
|--------|--------|------|
| 1 | v3 セクション 5.1 | `distribute_width` アルゴリズム（検証済み） |
| 2 | v3 セクション 5.2 | `scale_x` の処理順序（検証済み） |
| 3 | v3 セクション 6.3 | `split` の幅計算（検証済み） |
| 4 | v2.1 セクション 3.5 | `ContainerElement` のクラス構造（API 形のみ） |

---

## 現在のステータス

> Phase 番号は v3 移行計画に準拠

| Phase | v3 対応内容 | 状態 | 説明 |
|-------|-------------|------|------|
| Phase 0 | 追加順序修正 | [Done] | `_elements` 統合 + 2-pass 導入 |
| **Phase 1** | Constraints/Flex | [WIP] | 幅配分修正 + split v3 準拠 |
| Phase 2 | LayoutKey/HitTest | [Todo] | 安定キーによる状態維持 |
| Phase 3 | 差分更新/プール | [Todo] | IMGUI 再構築コスト最適化 |

### 補足: 実装済み機能（Phase 番号外）

| 機能 | 状態 | 備考 |
|------|------|------|
| `corners` 角丸制御 | [Done] 完了 | `align=True` 時の隣接ボタン角丸 |
| `alignment` 配置 | [Partial] 部分完了 | Phase 1 で v3 準拠に修正予定 |
| `split(factor)` | [Done] 完了 | factor==0 の均等分割を含め v3 準拠 |

---

## Phase 0: 追加順序修正 + 2-pass 導入 [Done]

> 完了日: 2026-01-18

### 目標

1. `_items` と `_children` の分離を解消し、追加順序を保持
2. `measure()` → `arrange()` の 2-pass アルゴリズムを導入

### 完了した変更

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

### 2-pass アルゴリズム

> 用語: v3 に準拠して `measure` / `arrange` を使用
> （現在の実装は `estimate` / `resolve` だが、Phase 1 でリネーム予定）

```python
def layout(self, *, force: bool = False, constraints: Optional[BoxConstraints] = None) -> None:
    """レイアウト計算（2-pass: measure → arrange）"""
    if not self._dirty and not force:
        return

    if constraints is None:
        constraints = BoxConstraints.tight_width(self.width)

    # Pass 1: サイズ推定 (measure)
    self.estimate(constraints)  # → measure() にリネーム予定

    # Pass 2: 位置確定 (arrange)
    self.resolve(self.x, self.y)  # → arrange() にリネーム予定

    self._dirty = False
```

### テスト結果

```python
# 追加順序が正しく保持されることを確認 [Done]
layout.label(text="Section 1")
row = layout.row()
row.label(text="Left")
row.label(text="Right")
layout.label(text="Section 2")  # ← row の後に表示される
```

### 既知の問題（Issue #116）

> これらは Phase 1 で解決予定

| ID | 問題 |
|----|------|
| P1-1 | Width-dependent height problem |
| P1-2 | scale_x inconsistency |
| P1-3 | scale_y double-scaling risk |
| P1-4 | Horizontal layout height constraint ignored |
| P1-5 | calc_height() ignores dirty state |

---

## Phase 1: Constraints / Flex 実装 [WIP]

> 状態: **進行中**
> 参照: v3 セクション 5.1, 5.2, 6.3

### 目標

**UILayout 互換の幅配分アルゴリズムを実装**

### 1.1 用語リネーム

| 現在 | v3 準拠 |
|------|---------|
| `estimate()` | `measure()` |
| `resolve()` | `arrange()` |
| `_estimate_vertical()` | `_measure_vertical()` |
| `_estimate_horizontal()` | `_measure_horizontal()` |
| `_resolve_vertical()` | `_arrange_vertical()` |
| `_resolve_horizontal()` | `_arrange_horizontal()` |

### 1.2 Constraints 契約の明文化

> 参照: v3 セクション 4

**原則**: *Constraints go down, sizes go up, positions go down.*

```python
class BoxConstraints:
    min_width: float
    max_width: float
    min_height: float
    max_height: float

    @staticmethod
    def tight(width: float, height: float) -> "BoxConstraints":
        """サイズを固定"""
        return BoxConstraints(width, width, height, height)

    @staticmethod
    def loose(max_width: float, max_height: float) -> "BoxConstraints":
        """最大サイズのみ指定"""
        return BoxConstraints(0, max_width, 0, max_height)

    def deflate(self, horizontal: float, vertical: float) -> "BoxConstraints":
        """padding を除外した制約を返す"""
        return BoxConstraints(
            max(0, self.min_width - horizontal),
            max(0, self.max_width - horizontal),
            max(0, self.min_height - vertical),
            max(0, self.max_height - vertical)
        )
```

### 1.3 SizingPolicy の導入

> 参照: v3 セクション 5

```python
@dataclass
class SizingPolicy:
    """サイズ決定ポリシー（v3 準拠）"""
    estimated_width: float = 0.0   # measure() で計算されたサイズ
    fixed_width: float | None = None  # ui_units_x で上書きされた固定幅
    is_fixed: bool = False         # fixed_size フラグ
    min_width: float = 0.0
    max_width: float = float('inf')
```

### 1.4 幅配分アルゴリズム（v3 準拠）

> 参照: v3 セクション 5.1 - `distribute_width`

```python
def distribute_width(children, available_width, gap, alignment):
    """Row の幅配分アルゴリズム（Blender interface_layout.cc:347-382 準拠）"""
    gaps_total = gap * (len(children) - 1)
    available = available_width - gaps_total

    # 各子の推定幅を合計
    total_estimated = sum(c.estimated_width for c in children)

    if total_estimated == 0:
        return  # 推定サイズがない → 何もしない

    for child in children:
        # ガード: available が 0 なら推定サイズをそのまま使用
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

### 1.5 scale_x の動作（v3 準拠）

> 参照: v3 セクション 5.2

**処理順序**（Blender `interface_layout.cc:5265-5287` 準拠）:
1. 子の `measure()` を再帰呼び出し（子の推定サイズを計算）
2. `scale_x/y` を子アイテムに適用（**子 measure 後、親 measure_impl 前**）
3. 親の `measure_impl()` でサイズ計算（scale 適用後の子サイズを使用）
4. `ui_units_x` が設定されていれば上書き

**[Partial] 重要**: `scale_x` は「子の measure 後、親の measure_impl 前」に適用される。
「measure 前」と書くと曖昧なので、この順序を厳守すること。

**[Partial] 重要な発見（実機テスト結果）**:

| alignment | scale_x の効果 | 理由 |
|-----------|---------------|------|
| `EXPAND` | **見えにくい** | 比率 1:1 → 2:2 = 1:1、利用可能幅を同比率で配分 |
| `LEFT/CENTER/RIGHT` | **見える** | 自然サイズを維持するため、倍率効果が visible |

### 1.6 Split の v3 準拠修正

> 参照: v3 セクション 6.3

**状態**:
- [Done] 3列目以降の幅計算を v3 準拠に修正
- [Done] factor==0 の均等分割を追加

```python
def resolve_split(items, total_width, gap, percentage):
    """Split の幅配分（v3 / Blender 準拠）"""
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

**暗黙 column なし（v3 確定事項）**:
- `split.label()` で追加されたアイテムは各々が独立した列として扱われる
- 縦に複数アイテムを配置したい場合は明示的に `split.column()` を使用

### 1.7 実装タスク

- [ ] 用語リネーム: `estimate` → `measure`, `resolve` → `arrange`
- [x] `BoxConstraints.deflate()` メソッド追加
- [ ] `SizingPolicy` クラス導入
- [ ] `_measure_horizontal()` を `distribute_width` アルゴリズムに修正
- [ ] `scale_x` の適用タイミングを修正（子 measure 後、親 measure_impl 前）
- [x] `split` の幅計算を v3 準拠に修正（3列目以降 + factor==0）
- [ ] Issue #116 の P1-1 〜 P1-5 を解決
- [ ] `alignment` を v3 準拠に修正（EXPAND vs LEFT/CENTER/RIGHT）

### 1.8 検証項目

```python
# テストケース 1: 均等分配（EXPAND）
row = layout.row()
row.alignment = 'EXPAND'  # デフォルト
row.label(text="A")
row.label(text="BBBBBB")
row.label(text="C")
# 期待: 3つのラベルが利用可能幅を推定サイズ比で分配

# テストケース 2: scale_x + alignment
row = layout.row()
row.alignment = 'LEFT'
row.scale_x = 2.0
row.operator("mesh.primitive_cube_add", text="A")
# 期待: ボタン幅が 2 倍、右に余白

# テストケース 3: split 3列
split = layout.split(factor=0.25)
split.column()  # 25%
split.column()  # 37.5% (残り75%の半分)
split.column()  # 37.5%
# 期待: 25% : 37.5% : 37.5%

# テストケース 4: split 暗黙 column なし
split = layout.split(factor=0.3)
split.label(text="A")  # 30%
split.label(text="B")  # 70%
# 期待: 2つの label が横に並ぶ（縦に積まれない）
```

---

## Phase 2: LayoutKey / HitTest [Todo]

> 参照: v3 セクション 7

### 目標

**安定キーによる状態維持と入力解決**

### 2.1 LayoutKey の設計

```
LayoutKey = (panel_uid, layout_path, explicit_key)

例:
  panel_uid = "demo_quick_viewport"
  layout_path = "root.row[0].button[1]"
  explicit_key = None  # または "my_button_id"

最終キー = "demo_quick_viewport:root.row[0].button[1]"
```

**生成ルール**:
1. `panel_uid`: パネル固有ID
2. `layout_path`: Build 時の構造パス（自動生成）
3. `explicit_key`: ユーザー指定のキー（オプション）

### 2.2 HitTest の流れ

```
1. Build: LayoutNode ツリーを構築
2. Layout: Rect を確定
3. Paint: 描画 + HitRect を登録（描画順）
4. Event: マウス座標から HitRect を逆順検索
5. Dispatch: 最前面の HitRect に対応するノードにイベントを送信
```

### 2.3 既存 HitTestManager との互換

- 現在の `HitTestManager` は `tag` で管理
- Phase 2 では `tag` → `LayoutKey` に移行
- 移行中は両方をサポート

### 2.4 実装タスク

- [ ] `LayoutKey` クラス導入
- [ ] Build 時に `layout_path` を自動生成
- [ ] `HitTestManager` を `LayoutKey` ベースに移行
- [ ] hover/active 状態を `LayoutKey` に紐づけ
- [ ] 順序変更時の状態維持テスト

---

## Phase 3: 差分更新 / プール [Todo]

> 参照: v3 セクション 8, v2.1 セクション 4

### 目標

**IMGUI 再構築コストの最適化**

### 3.1 問題

```python
def draw_panel(self, layout, context):
    layout.label(text="Title")       # 毎フレーム新しい LabelElement
    row = layout.row()               # 毎フレーム新しい RowElement
    row.operator(text="Button")      # 毎フレーム新しい ButtonElement
```

60fps で実行すると、毎秒 60 回のオブジェクト生成・GC が発生。

### 3.2 解決策 A: オブジェクトプール

> 参照: v2.1 セクション 4.2（構造のみ）

```python
class ElementPool:
    """要素のオブジェクトプール"""

    def acquire(self, element_type: type) -> LayoutElement:
        """プールから要素を取得（なければ新規作成）"""
        ...

    def release(self, element: LayoutElement) -> None:
        """要素をプールに返却"""
        ...
```

### 3.3 解決策 B: Dirty Flag + 差分更新

```python
class GPUPanel:
    def build(self, draw_func, context):
        structure_hash = self._compute_structure_hash(draw_func, context)

        if structure_hash != self._cached_structure_hash:
            # 構造が変わった → フル再構築
            ...
        else:
            # 構造は同じ → 値の更新のみ
            self._update_values(context)
```

### 3.4 実装優先度

**Phase 3 は Phase 1-2 完了後に検討**

理由:
1. 現在の GPULayout は 60fps で問題なく動作している
2. プール実装は複雑性を増す
3. まずは「正しいレイアウト」を優先

---

## リスク評価

### 低リスク [Done]

| 項目 | 理由 |
|------|------|
| `_elements` 統合 | 内部変更のみ、API は変わらない |
| 用語リネーム | 機能変更なし |

### 中リスク [Partial]

| 項目 | 理由 | 対策 |
|------|------|------|
| `distribute_width` 変更 | 全レイアウトに影響 | UILayout 比較検証 |
| `split` 3列対応 | 幅計算ロジック変更 | テストケース追加 |
| LayoutKey / HitTest | 入力系に影響 | フラグで段階的切替 |

### 高リスク [High]

| 項目 | 理由 | 対策 |
|------|------|------|
| パフォーマンス劣化 | 2-pass レイアウトのコスト | ベンチマーク |
| 既存コードの破壊 | test_layout.py 動作不良 | 互換レイヤー |

---

## 参照ドキュメント

| ドキュメント | 用途 | 参照範囲 |
|-------------|------|---------|
| `gpu_layout_architecture_v3.md` | 主要仕様 | **全セクション** |
| `gpu_layout_architecture_v2.1.md` | 実装参照 | 構造・API 形のみ |
| `blender_source_investigation.md` | Blender ソースコード調査 | 検証根拠 |
| `gpu_layout_issues_report.md` | 問題分析 | Issue #116 詳細 |

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0.0 | 2026-01-20 | 初版作成 |
| 1.1.0 | 2026-01-20 | レビュー反映: Phase 番号を v3 に整合、v2.1 参照範囲限定、用語統一 |
| 1.1.1 | 2026-01-20 | 再レビュー反映: `distribute_width` ガード復活、`scale_x` 適用タイミング明確化、絵文字を ASCII 化 |

---

*Last Updated: 2026-01-20*
