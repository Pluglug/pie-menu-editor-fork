# GPULayout Next Steps - Input/Units TODO

> 作成日: 2026-01-26
> 目的: 次セッションでの実装タスクを Todo 形式で整理
> 前提: Blender 互換の見た目/挙動に寄せる

---

## 1. Vector のヒットエリア実装

- [ ] VectorItem の子ウィジェット (NumberItem) に確実に hit する
- [ ] vertical/horizontal 両方で当たり判定が崩れないことを確認
- [ ] use_property_split のラベル領域は hit 対象外

### 変更候補
- `ui/gpu/layout/interaction.py`
- `ui/gpu/items/vector.py`

### 受け入れ基準
- Vector の各要素をクリック/ドラッグできる
- 他の項目（ラベル領域、余白）で誤クリックしない

---

## 2. マウスドラッグ精度 (step/shift/ctrl) の Blender 互換

- [ ] step の基準を Blender に合わせて再計算
- [ ] Shift/Ctrl/Alt など修飾キー時の倍率調整
- [ ] unit のスケール差（length, angle など）を反映

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

---

## 4. preferred unit (length_unit など) 対応

- [ ] `unit_settings.length_unit` / `mass_unit` / `time_unit` / `temperature_unit` を反映
- [ ] 表示用の preferred unit を選択可能にする
- [ ] `bpy.utils.units.to_string()` では拾えないため自前の補正が必要

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
