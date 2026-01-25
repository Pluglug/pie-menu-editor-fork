# GPULayout - Blender互換 Align Pass 計画書

> 作成日: 2026-01-25  
> 対象: `ui/gpu/` (GPULayout)  
> 目的: row/column/column_flow/grid_flow を含む **全レイアウトで Blender と同様の角連結**を実現

---

## 背景 / 問題

GPULayout の `align=True` は現在、row/column の **1次元隣接**のみで corners を決定している。  
そのため `column_flow` や `grid_flow` など **2次元配置**では角連結が起きず、各ボタンが独立した丸角になる。

Blender はレイアウト種別に依存せず、**最終配置された矩形の近接判定（block_align_calc）**で連結を決定する。  
この設計差が、column_flow の不一致を生んでいる。

---

## 目標

1. **Blender の align 処理に準拠**した「2D 近接ベースの角連結」を実装する
2. row/column/column_flow/grid_flow など **すべてのレイアウトで一貫して動作**させる
3. **非 alignable アイテム**や **欠けた隣接**にも Blender と同じ挙動で対応する
4. 既存の `corners` 手動設定を **最小限に整理**し、align pass に統合する

---

## 非目標

- Blender の C 実装を「完全移植」すること自体は目的ではない  
  （ただし *出力が一致* することは必須）
- 一時的な描画テクニック（アウトラインのみでごまかす等）

---

## Blender 側の設計要点（要約）

### 1) align グループ付与
- `Layout::resolve()` で `align=True` のレイアウト配下に **alignnr を一括付与**
- ネストした align レイアウトは **同じ alignnr に属する**（上位が優先）

### 2) 近接判定（block_align_calc）
- 2D 近接判定で隣接ボタンを決定
- `MAX_DELTA = 0.45 * max(UI_UNIT_X, UI_UNIT_Y)` 以内なら “隣接”
- 隣接していれば **境界線を中間に寄せて連結**
- L字/T字形状などは **stitch_neighbors** で伝播整列

### 3) 角丸決定（widget_roundbox_set）
- `BUT_ALIGN_*` フラグから角丸を削る  
  （上下左右の隣接がある辺は直角）

---

## 現状の GPULayout の課題

- align を **レイアウト方向の一次元計算**として扱っている  
  → 2D 配置に対応できない
- `column_flow` / `grid_flow` で **角連結処理が存在しない**
- `align=True` が **spacing を 0 に固定**  
  → Blender の `column_flow` と差異（Blender は spacing を残しつつ align pass で吸収）

---

## 新設計: Align Pass（2D 近接ベース）

### 全体フロー（layout() の拡張）

```
measure() → arrange()
  → align_group_assign()        # 新規
  → align_pass_2d()              # 新規
  → _register_title_bar()
  → _register_resize_handle()
  → _update_hit_positions_recursive()
```

> Align pass は **arrange 後・hit 生成前**に実行する  
> これにより “見た目の連結” と “当たり判定” を一致させる。

---

## 1. align グループ付与（assign）

### 仕様
- Blender と同様に **最初に見つかった align=True のレイアウトがグループを支配**  
  （ネストした align レイアウトは新グループを作らない）
- グループ単位で “隣接判定” を行う

### 実装案
- `LayoutItem` に `align_group: int | None` を追加
- `GPULayout` に `assign_align_groups()` を追加

擬似コード:
```python
def assign_align_groups(layout, current_group=None):
    if layout.align and current_group is None:
        current_group = next_group_id()
    for child in layout._elements:
        if isinstance(child, GPULayout):
            assign_align_groups(child, current_group if layout.align else None)
        elif isinstance(child, LayoutItem):
            if current_group:
                child.align_group = current_group
```

**Blender準拠ポイント**
- `align_group` が既に付いている要素は上書きしない  
  → “最初の align 祖先が勝つ” を再現

---

## 2. 2D 近接判定（align_pass_2d）

### 概要
各 align グループごとに「隣接関係」を決め、  
隣接がある辺の角を直角にする。

### データ構造（Blender互換の縮小版）
```
AlignItem:
  item: LayoutItem
  rect: (xmin, xmax, ymin, ymax)
  neighbors[4]: AlignItem | None   # LEFT, TOP, RIGHT, DOWN
  dists[4]: float                  # 隣接距離
  flags[4]: int                    # stitch フラグ (後述)
```

### 近接判定の条件（Blender準拠）
- **同じ列 / 行を共有しているか**を先に確認
- **左右隣接**: Y範囲が重なる & X距離が `MAX_DELTA` 未満
- **上下隣接**: X範囲が重なる & Y距離が `MAX_DELTA` 未満

### MAX_DELTA
```
MAX_DELTA = 0.45 * max(UI_UNIT_X, UI_UNIT_Y)
```

GPULayout 側では次を使用:
- `UI_UNIT_Y` 相当: `style.scaled_item_height()`
- `UI_UNIT_X` 相当: `style.scaled_item_height()` を暫定採用  
  （横方向の UI_UNIT を導入するなら置き換え）

---

## 3. 隣接伝播（stitch_neighbors）

### 目的
以下のような **L字/T字の列連結**で角の欠けや不整合を防ぐ:

```
┌──────┬──────┐
│ A    │ B    │
├──────┘      │
│ C           │
└─────────────┘
```

### Blender の挙動
`block_align_stitch_neighbors()` が  
「斜め方向の隣接を検出 → 列全体に補正伝播」

### 実装方針
Blender の `flags` と `stitch` の仕組みを **ほぼそのまま移植**する。  
これにより “複雑な欠け” も一致させる。

---

## 4. 角丸の決定（corners）

### corners の定義（GPULayout）
```
(bottomLeft, topLeft, topRight, bottomRight)
```

### 角丸判定ルール
- **上に隣接** → topLeft/topRight は直角
- **下に隣接** → bottomLeft/bottomRight は直角
- **左に隣接** → bottomLeft/topLeft は直角
- **右に隣接** → bottomRight/topRight は直角

### 例（単純な縦並び）
```
first : (False, True,  True,  False)
middle: (False, False, False, False)
last  : (True,  False, False, True)
```

---

## 5. 位置補正（境界を中間に寄せる）

Blender は隣接が確定した辺を **中間線に寄せて境界を一致**させる。  
これにより “隙間ゼロの連結” が保証される。

### 実装方針
- `AlignItem` の `rect` を “表示用 rect” として補正  
  → `item.x/y/width/height` に反映
- align pass 後に `_update_hit_positions_recursive()` を呼び直す

> まずは **補正あり**の完全互換を目指す。  
> もし副作用が大きい場合は “描画専用 rect” 方式を検討。

---

## 6. Spacing ルールの整合

Blender では:
- row/column の align → spacing 0
- column_flow/grid_flow の align → spacing は残る（block_align が吸収）

GPULayout は `_get_spacing()` が `align=True` で 0 を返すため不一致。

### 方針
- **row/column/split**: align=True で spacing=0 （現状維持）
- **column_flow/grid_flow**: align=True でも spacing を残す  
  （`style.scaled_spacing_x()` / `style.scaled_spacing()` を使用）

---

## 7. 非 alignable アイテムの整合

Blender では `button_can_align()` が **特定のボタン種別を除外**する。  
GPULayout も `LayoutItem.can_align()` を再設計して整合させる。

### 対象候補（Blender基準）
- Label / Separator 系
- Checkbox 系
- Tab / Spacer 系

**実装方針**
- `can_align()` の override を各アイテムで明示
- align pass は `can_align()` が True のものだけ参加

---

## 8. 既存の corners 手動設定の整理

現在 `props._prop_split_vector()` で corners を **手動ロック**している。  
Align pass 導入後は不要なので整理する。

### 方針
- `corners_locked` の使用箇所を棚卸し
- Align pass が正しく動作するなら **手動 corners 設定を削除**

---

## 実装ステップ（フェーズ）

### Phase A: 基盤
1. `LayoutItem.align_group` の追加
2. `assign_align_groups()` 実装
3. align グループの単体テスト追加

### Phase B: 2D 近接 + corners
4. `align_pass_2d()` 実装（neighbors + corners）
5. row/column/column_flow での動作確認

### Phase C: Stitch + 境界補正
6. `stitch_neighbors` 移植
7. rect の中間線補正を導入

### Phase D: Spacing / can_align 整合
8. column_flow/grid_flow の spacing 方針を変更
9. can_align の精査と修正

### Phase E: 既存手動 corners の整理
10. `props._prop_split_vector()` の corners 手動設定を撤去
11. 既存 UI との視覚差分確認

---

## 影響ファイル（予定）

- `ui/gpu/layout/flow.py`  
  - align pass 呼び出し追加
- `ui/gpu/layout/core.py`  
  - align グループ割当の基盤
- `ui/gpu/items/base.py`  
  - `align_group` 追加
- `ui/gpu/layout/utils.py`  
  - spacing 方針の見直し
- `ui/gpu/layout/props.py`  
  - corners 手動ロックの整理
- `ui/gpu/test_layout.py`  
  - align/flow/grid の回帰テスト

---

## テスト計画

### 1. 基本連結
- row/column align=True の上端・中間・下端の corners

### 2. column_flow 連結
- 3列 × 3行の均等グリッド
- 欠け列（例: 8個配置）での corner 破綻確認

### 3. grid_flow 連結（将来）
- row_major True/False の両パターン
- even_columns/rows の有無

### 4. 非 alignable
- Label/Separator が挟まった時に連結が途切れるか

---

## 主要な論点 / 決定事項

1. **align pass の境界補正を行うか？**  
   → Blender互換性重視なら実施が望ましい

2. **spacing を align で常に 0 にするか？**  
   → column_flow/grid_flow は Blender に合わせて残す

3. **corners_locked の扱い**  
   → align pass が優先するのか、例外を許すのか

---

## 完了条件（Definition of Done）

- column_flow/grid_flow で Blender と同じ角連結が再現できる
- row/column の corner も既存挙動を維持
- 目視比較で “見た目の差” がほぼ無いこと
- 回帰テストが追加され、将来の変更で崩れないこと

