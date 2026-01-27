# GPULayout Next Steps - Input/Units TODO

> 作成日: 2026-01-26
> 目的: 次セッションでの実装タスクを Todo 形式で整理
> 前提: Blender 互換の見た目/挙動に寄せる

---

## 0. キー入力スコープのメモ (2026-01-27)

- パネル外のキーは PASS_THROUGH を基本にする（hover/drag 時のみ処理）
- 次段階: focus/active 状態を導入して TextInput へルーティング

---

## 1. Vector のヒットエリア実装 ✅ 完了

- [x] VectorItem の子ウィジェット (NumberItem) に確実に hit する
- [x] vertical/horizontal 両方で当たり判定が崩れないことを確認
- [x] use_property_split のラベル領域は hit 対象外

> 完了日: 2026-01-26

### 変更候補
- `ui/gpu/layout/interaction.py`
- `ui/gpu/items/vector.py`

### 受け入れ基準
- Vector の各要素をクリック/ドラッグできる
- 他の項目（ラベル領域、余白）で誤クリックしない

---

## 2. マウスドラッグ精度 (step/shift/ctrl) の Blender 互換 ✅ 実装

- [x] step の基準を Blender に合わせて再計算
- [x] Shift/Ctrl/Alt など修飾キー時の倍率調整
- [x] unit のスケール差（length, angle など）を反映

> 実装日: 2026-01-26（Ctrl スナップ調整を追加、実機比較はこれから）

### 参考
- Blender: `ui_get_but_step_unit()`
- 影響: `NumberItem.set_value_from_delta()` / `SliderItem.set_value_from_position()`

### 受け入れ基準
- Blender と同じ感覚でドラッグ量が変化
- 値が跳ねず、精度変更時も安定

---

## 3. TextInput 実装 + 入力パース

- [ ] NumberItem の直接入力モード
- [ ] 単位付き入力のパース (`bpy.utils.units.to_value`)
- [ ] Factor/Percentage の入力ルールを Blender と一致

### 変更候補
- `ui/gpu/items/text_input.py` (新規)
- `ui/gpu/items/inputs.py`
- `ui/gpu/layout/interaction.py`

### 受け入れ基準
- Enter/ESC で確定/キャンセル
- `1m 20cm` のような入力が有効

### 調査メモ (Blender)
- Text edit 本体: `source/blender/editors/interface/interface_handlers.cc`
  - `ui_textedit_begin/end`, `ui_textedit_insert_buf`, `ui_textedit_move`, `ui_textedit_delete` で
    カーソル/選択/Undo/IME を処理。
- 数値入力パース: `source/blender/editors/interface/interface.cc`
  - `button_string_eval_number()` → `ui_number_from_string_*()` を分岐（units/factor/percentage）。
- 単位付き数値パース: `source/blender/editors/util/numinput.cc`
  - `user_string_to_number()` は **ユニット付き文字列**のみ `BKE_unit_replace_string` を使い、
    **ユニット無し**は `BKE_unit_apply_preferred_unit()` を適用後に `unit_scale` で戻す。
- Python API: `source/blender/python/intern/bpy_utils_units.cc`
  - `bpy.utils.units.to_value(system, category, str_input, str_ref_unit=None)` が
    `BKE_unit_replace_string` + Python eval を内包（ユニット付きの式入力に有効）。

### IME について
- Blender C 実装は `WM_IME_COMPOSITE_*` と `wmIMEData` に依存（`interface_handlers.cc`）。
- Python からは IME composition data を直接扱えないため、
  **確定文字列 (`TEXTINPUT`) のみ対応**に留まる見込み。
  変換中の下線表示や候補ウィンドウ位置追従は C 側 API 追加が必要。

---

## 4. preferred unit (length_unit など) 対応 ✅ 実装

- [x] `unit_settings.length_unit` / `mass_unit` / `time_unit` / `temperature_unit` を反映
- [x] 表示用の preferred unit を選択可能にする
- [x] `bpy.utils.units.to_string()` では拾えないため自前の補正が必要

> 実装日: 2026-01-27（preferred unit の強制表示）

### 参考
- Blender: `BKE_unit_value_as_string()` / `PreferredUnits`
- `bpy.context.scene.unit_settings.*`

### 受け入れ基準
- Blender と同じ単位で表示される (例: cm を指定した場合 cm 表示)

---

## 5. テスト・確認

- [ ] `use_property_split=True` の vector / number / slider
- [ ] column_flow / row align の混在
- [ ] unit_settings の切替（metric/imperial + split + preferred unit）

---

## 6. Drag キャンセル (右クリック/ESC)

- [ ] Number/Slider ドラッグ中に右クリック or ESC で変更をキャンセル
- [ ] キャンセル時はドラッグ開始時の値へ復帰
- [ ] ドラッグ中の on_change を抑制しない（Blender と同様に即時反映 + キャンセルで巻き戻し）

### 変更候補
- `ui/gpu/interactive.py`
- `ui/gpu/layout/interaction.py`
- `ui/gpu/items/inputs.py`

### 受け入れ基準
- ドラッグ中の RMB/ESC で値が元に戻る
- RMB/ESC 以外のリリースは確定

---

## 7. マルチ編集 (align=True の縦ドラッグ / Alt オフセット)

- [ ] align=True 列で縦ドラッグ → 複数 Number/Slider を選択
- [ ] 選択後、横ドラッグで一括変更
- [ ] 横ドラッグせずに離すと一括テキスト編集を開始
- [ ] Alt ドラッグ時に選択オブジェクト全体へオフセット適用

### 変更候補
- `ui/gpu/interactive.py`
- `ui/gpu/layout/interaction.py`
- `ui/gpu/items/inputs.py`
- `ui/gpu/layout/flow.py` (align グループ/領域判定)

### 受け入れ基準
- Blender と同様に複数フィールドを選択・一括編集可能
- Alt で選択オブジェクトへ同一オフセットが適用される

---
