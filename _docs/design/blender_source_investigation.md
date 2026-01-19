# Blender UILayout ソースコード調査レポート

> Version: 1.0.0
> Created: 2026-01-19
> Source: Blender 5.0+ (`source/blender/editors/interface/interface_layout.cc`)
> Related: `gpu_layout_architecture_v3.md`

---

## 調査目的

GPULayout v3 設計の仮定を Blender ソースコードと照合し、設計の正確性を検証する。

---

## 調査結果サマリー

| # | 質問 | v3 仮定 | 実際 | 一致 |
|---|------|---------|------|------|
| 1 | row() 等幅配分のタイミング | 常にデフォルト | alignment=EXPAND 時のみ | ⚠️ 部分一致 |
| 2 | ui_units_x vs 等幅配分の優先順位 | ui_units_x 優先 | **ui_units_x で上書き** | ✅ 一致 |
| 3 | scale_x の適用先 | weight の倍率 | **子アイテムサイズの直接倍率** | ❌ 不一致 |
| 4 | split 暗黙 column 生成 | 最初の要素で自動生成 | **暗黙 column なし** | ❌ 不一致 |
| 5 | split 3列以上の幅計算 | 残りを均等分割 | 残りを均等分割 | ✅ 一致 |
| 6 | alignment と子の幅 | EXPAND以外は自然サイズ | EXPAND以外は自然サイズ | ✅ 一致 |
| 7 | 2-pass vs 1-pass | 暗黙の 2-pass | **明示的 2-pass** | ✅ 一致 |
| 8 | 幅確定タイミング | 描画直前 | resolve() 完了時 | ✅ 一致 |

---

## 詳細分析

### 質問1: row() 等幅配分のタイミング

**v3 仮定**: row() はデフォルトで weight=1 の等幅配分

**実際のロジック** (`interface_layout.cc:347-382`):

```cpp
static int ui_item_fit(...)
{
  // available == 0 は無制限
  if (ELEM(0, available, all)) {
    return item;  // 元のサイズをそのまま返す
  }

  if (all > available) {
    // 内容が利用可能幅より大きい → 比例縮小
    const float width = (item * available) / float(all);
    return int(width);
  }

  // 内容が利用可能幅以下
  if (alignment == LayoutAlign::Expand) {
    // EXPAND: 比例拡大
    const float width = (item * available) / float(all);
    return int(width);
  }
  return item;  // EXPAND以外: 元のサイズをそのまま返す
}
```

**結論**:
- `alignment = EXPAND` (デフォルト) の場合のみ等幅配分
- row の alignment が LEFT/CENTER/RIGHT の場合、子は自然サイズを維持
- v3 の「weight による配分」は**不正確** — 実際は「推定サイズの比率」で配分

---

### 質問2: ui_units_x vs 等幅配分の優先順位

**v3 仮定**: ui_units_x が basis_width として先に確保される

**実際のロジック** (`interface_layout.cc:5297-5300`):

```cpp
void Layout::estimate()
{
  // ... 子の estimate を再帰実行 ...

  if (this->scale_x() != 0.0f || this->scale_y() != 0.0f) {
    ui_item_scale(this, blender::float2{this->scale_x(), this->scale_y()});
  }
  this->estimate_impl();  // 推定サイズ計算

  // Force fixed size: ui_units_x で上書き
  if (this->ui_units_x() > 0) {
    w_ = UI_UNIT_X * this->ui_units_x();
  }
}
```

**結論**:
- `ui_units_x` は estimate 結果を**完全に上書き**する
- これは v3 の「fixed 優先」と一致
- ただし、v3 の「残り幅を weight で配分」ではなく、「ui_units_x が設定されたものは fixed_size フラグが立つ」

---

### 質問3: scale_x の適用先

**v3 仮定**: scale_x は weight の倍率として機能

**実際のロジック** (`interface_layout.cc:5249-5273`):

```cpp
static void ui_item_scale(Layout *litem, const float scale[2])
{
  for (uiItem *item : litem->items()) {
    if (item->type() != uiItemType::Button) {
      ui_item_scale(subitem, scale);  // 再帰
    }

    int2 size = item->size();
    int2 offset = item->offset();

    if (scale[0] != 0.0f) {
      offset.x *= scale[0];
      size.x *= scale[0];  // ← 子アイテムのサイズを直接倍率
    }
    ui_item_position(item, offset.x, offset.y, size.x, size.y);
  }
}
```

**結論**:
- `scale_x` は **子アイテムのサイズを直接倍率** する
- これは estimate の**前**に実行される
- v3 の「weight 倍率」とは異なる動作
- **v3 設計要修正**: SizingPolicy に scale_x 対応を追加

---

### 質問4: split 暗黙 column 生成

**v3 仮定**: split.label() を呼ぶと暗黙の column が自動生成される

**実際のロジック**:

`Layout::label()` (`interface_layout.cc:3168-3171`):
```cpp
void Layout::label(const StringRef name, int icon)
{
  uiItem_simple(this, name, icon);  // 直接ボタンを追加
}
```

`uiItem_simple()` は split 固有の処理を持たず、単純にボタンを追加する。

`uiLayoutItemSplit::resolve_impl()` (`interface_layout.cc:4650-4690`):
```cpp
void uiLayoutItemSplit::resolve_impl()
{
  const float percentage = (this->percentage == 0.0f) ? 1.0f / float(tot) : this->percentage;

  int colw = w * percentage;  // 最初の列の幅

  for (uiItem *item : this->items()) {
    ui_item_position(item, x, y - size.y, colw, size.y);

    if (!is_item_last) {
      // 2列目以降: 残りを (tot-1) で均等分割
      colw = (w - int(w * percentage)) / (float(tot) - 1);
    }
  }
}
```

**結論**:
- **暗黙の column 生成はない**
- split に直接追加されたアイテム（label/button/column など）がそれぞれ列として扱われる
- **v3 設計要修正**: セクション 6.3 の「暗黙 column」を削除

**Python での挙動確認**:
```python
split = layout.split(factor=0.3)
split.label(text="A")  # split の items[0] として追加 → 30%
split.label(text="B")  # split の items[1] として追加 → 70%

# column を使う場合
split = layout.split(factor=0.3)
col1 = split.column()  # items[0] → 30%
col1.label(text="A")
col2 = split.column()  # items[1] → 70%
col2.label(text="B")
```

---

### 質問5: split 3列以上の幅計算

**v3 仮定**: 残りを均等分割

**実際のロジック** (`interface_layout.cc:4677`):

```cpp
// 2列目以降の幅
const float width = (w - int(w * percentage)) / (float(tot) - 1);
```

**結論**:
- v3 の仮定と**完全一致**
- 例: `split(factor=0.25)` で 3 列 → [25%, 37.5%, 37.5%]

---

### 質問6: alignment と子の幅

**v3 仮定**: alignment が EXPAND 以外の場合、子は自然サイズを維持

**実際のロジック** (`interface_layout.cc:3722-3733`):

```cpp
// align right/center
offset = 0;
if (this->alignment() == LayoutAlign::Right) {
  if (freew + fixedw > 0 && freew + fixedw < w) {
    offset = w - (fixedw + freew);  // 右にオフセット
  }
}
else if (this->alignment() == LayoutAlign::Center) {
  if (freew + fixedw > 0 && freew + fixedw < w) {
    offset = (w - (fixedw + freew)) / 2;  // 中央にオフセット
  }
}
```

**結論**:
- v3 の仮定と**完全一致**
- LEFT/CENTER/RIGHT: 子は自然サイズ、余白をオフセットで処理
- EXPAND: 子を比例拡大

---

### 質問7: 2-pass vs 1-pass

**v3 仮定**: 暗黙の 2-pass レイアウト

**実際のフロー**:

```
1. estimate() — 再帰的にサイズを推定
   ├─ 子の estimate() を呼び出し
   ├─ scale_x/y を適用
   ├─ estimate_impl() でサイズ計算
   └─ ui_units_x/y で上書き（必要なら）

2. resolve() — 再帰的に位置を確定
   ├─ resolve_impl() で子の位置を決定
   └─ 子の resolve() を呼び出し
```

**結論**:
- **明示的な 2-pass** (estimate + resolve)
- v3 の設計と一致
- GPULayout では Build/Measure/Arrange に分離予定（3-pass 相当）

---

### 質問8: 幅確定タイミング

**v3 仮定**: 描画直前に確定

**実際のタイミング**:
- `resolve()` 完了時に全ての Rect が確定
- その後 `uiEndBlock()` で描画処理へ

**結論**: v3 と一致

---

## v3 設計への影響

### 修正が必要な箇所

1. **セクション 5: SizingPolicy**
   - `scale_x` の扱いを再定義
   - 現在: weight の倍率
   - 修正: 子アイテムサイズの直接倍率（estimate 前に適用）

2. **セクション 6.3: Split**
   - 「暗黙 column」の記述を削除
   - 実際: 直接追加されたアイテムがそれぞれ列として扱われる

3. **セクション 5.1: distribute_width**
   - アルゴリズムは概念的に正しいが、実装詳細を調整
   - Blender は「推定サイズの比率」で配分、weight という概念はない

### 維持できる設計

1. **Constraints 伝播**: root → leaf の方向は正しい
2. **2-pass レイアウト**: estimate + resolve
3. **ui_units_x 優先**: fixed size の扱いは正しい
4. **alignment 効果**: EXPAND/LEFT/CENTER/RIGHT の動作は正しい
5. **split 幅計算**: 最初の列は percentage、残りは均等分割

---

## 推奨アクション

1. **v3 ドキュメント修正**
   - scale_x の定義を「子サイズ倍率」に変更
   - split の暗黙 column を削除
   - SizingPolicy を「推定サイズベース」に再定義

2. **実機テスト追加**
   - scale_x の動作確認
   - split 直接アイテム追加の確認

3. **GPULayout 実装方針**
   - Blender の挙動を忠実に再現
   - ただし、内部モデルは v3 の概念（Constraints/SizingPolicy）を維持

---

## 参照コード位置

| 機能 | ファイル | 行番号 |
|------|----------|--------|
| ui_item_fit() | interface_layout.cc | 347-382 |
| Layout::estimate() | interface_layout.cc | 5275-5305 |
| ui_item_scale() | interface_layout.cc | 5249-5273 |
| LayoutRow::resolve_impl() | interface_layout.cc | 3602-3749 |
| uiLayoutItemSplit::resolve_impl() | interface_layout.cc | 4650-4690 |
| Layout::split() | interface_layout.cc | 5022-5033 |
| Layout::label() | interface_layout.cc | 3168-3171 |
| Layout::local_direction() | interface_layout.cc | 568-586 |

---

*Last Updated: 2026-01-19*
