# GPU Layout - layout.prop() 実装計画

> **Status**: Planning
> **Date**: 2026-01-16
> **Related Issue**: #110 Theme Integration
> **Prerequisite**: `gpu_theme_widget_mapping.md`

---

## 目標

PME の GPU Layout システムに `layout.prop()` を実装し、Blender のプロパティを
GPU 描画でレンダリングできるようにする。

---

## 実装フェーズ

### Phase 1: テーマシステム拡張

**目的**: ウィジェット別テーマカラーを GPULayoutStyle に統合

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 1.1 | ThemeWidgetColors データクラス作成 | `inner`, `inner_sel`, `item`, `outline`, `text`, `text_sel`, `roundness` を持つクラス | - |
| 1.2 | GPULayoutStyle にウィジェットテーマ追加 | `wcol_numslider`, `wcol_num`, `wcol_option`, `wcol_toggle`, `wcol_text`, `wcol_menu`, `wcol_radio` | 1.1 |
| 1.3 | `from_blender_theme()` を拡張 | 各 `wcol_*` を Blender テーマから読み込み | 1.2 |
| 1.4 | テーマ取得ヘルパー関数 | `get_widget_colors(widget_type)` で適切なテーマを返す | 1.3 |

**成果物**: `ui/gpu/style.py` の拡張

---

### Phase 2: 基本ウィジェット描画

**目的**: 各ウィジェットの描画ロジックを実装

#### 2.1 Slider (スライダー)

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 2.1.1 | SliderItem クラス作成 | `items.py` に追加 | Phase 1 |
| 2.1.2 | スライダー背景描画 | `inner` + `outline` + `roundness` | 2.1.1 |
| 2.1.3 | スライダーつまみ描画 | `item` カラーで現在値を表示 | 2.1.2 |
| 2.1.4 | 値テキスト描画 | 数値をスライダー上に表示 | 2.1.3 |
| 2.1.5 | ドラッグ操作 | HitRect + on_drag で値変更 | 2.1.4 |
| 2.1.6 | 直接入力モード | クリックでテキスト入力に切り替え（将来） | - |

**テーマ**: `wcol_numslider`
**複雑度**: ★★★★☆

#### 2.2 Number (数値フィールド)

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 2.2.1 | NumberItem クラス作成 | `items.py` に追加 | Phase 1 |
| 2.2.2 | フィールド背景描画 | `inner` + `outline` | 2.2.1 |
| 2.2.3 | 値テキスト描画 | 数値を中央/右揃えで表示 | 2.2.2 |
| 2.2.4 | 増減ボタン（矢印） | 左右の三角アイコン | 2.2.3 |
| 2.2.5 | ドラッグ操作 | 左右ドラッグで値変更 | 2.2.4 |

**テーマ**: `wcol_num`
**複雑度**: ★★★☆☆

#### 2.3 Checkbox (チェックボックス)

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 2.3.1 | CheckboxItem クラス作成 | `items.py` に追加 | Phase 1 |
| 2.3.2 | ボックス描画 | 小さな正方形 | 2.3.1 |
| 2.3.3 | チェックマーク描画 | チェック時のマーク | 2.3.2 |
| 2.3.4 | ラベル配置 | チェックボックスの右にテキスト | 2.3.3 |
| 2.3.5 | クリック操作 | 値トグル | 2.3.4 |

**テーマ**: `wcol_option`
**複雑度**: ★★☆☆☆

#### 2.4 Toggle (トグルボタン)

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 2.4.1 | ToggleItem 拡張 | 既存の ToggleItem をテーマ対応に | Phase 1 |
| 2.4.2 | 押下状態の描画 | `inner_sel` で選択状態を表現 | 2.4.1 |
| 2.4.3 | アイコン対応 | Boolean with icon | 2.4.2 |

**テーマ**: `wcol_toggle`
**複雑度**: ★★☆☆☆
**備考**: 既存の ToggleItem/ButtonItem を拡張

#### 2.5 Text (テキスト入力)

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 2.5.1 | TextInputItem クラス作成 | `items.py` に追加 | Phase 1 |
| 2.5.2 | フィールド背景描画 | `inner` + `outline` | 2.5.1 |
| 2.5.3 | テキスト描画 | 現在値を表示 | 2.5.2 |
| 2.5.4 | カーソル描画 | 編集中のカーソル位置 | 2.5.3 |
| 2.5.5 | キーボード入力 | 文字入力処理 | 2.5.4 |
| 2.5.6 | 選択範囲 | テキスト選択（将来） | - |

**テーマ**: `wcol_text`
**複雑度**: ★★★★★
**備考**: テキスト編集は複雑なため、最初は読み取り専用から始める

#### 2.6 Menu (Enum ドロップダウン)

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 2.6.1 | MenuButtonItem クラス作成 | ドロップダウンボタン | Phase 1 |
| 2.6.2 | ボタン描画 | 現在値 + 下矢印アイコン | 2.6.1 |
| 2.6.3 | メニューポップアップ | 別パネルとして選択肢を表示 | 2.6.2 |
| 2.6.4 | 選択操作 | クリックで値変更 | 2.6.3 |

**テーマ**: `wcol_menu`
**複雑度**: ★★★★☆
**備考**: ポップアップメニューは別システムが必要

#### 2.7 Radio (Enum 展開)

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 2.7.1 | RadioGroupItem クラス作成 | 横並びボタングループ | Phase 1 |
| 2.7.2 | 各ボタン描画 | 選択状態に応じた描画 | 2.7.1 |
| 2.7.3 | 選択操作 | クリックで値変更 | 2.7.2 |

**テーマ**: `wcol_radio`
**複雑度**: ★★★☆☆

#### 2.8 Color Swatch (カラー)

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 2.8.1 | ColorSwatchItem クラス作成 | カラー表示ボックス | Phase 1 |
| 2.8.2 | カラー描画 | 現在色を塗りつぶし | 2.8.1 |
| 2.8.3 | アウトライン | 背景との区別用 | 2.8.2 |
| 2.8.4 | カラーピッカー連携 | クリックでピッカー表示（将来） | - |

**テーマ**: (特殊 - 色そのものを表示)
**複雑度**: ★★☆☆☆

---

### Phase 3: layout.prop() API

**目的**: プロパティパスから適切なウィジェットを自動選択

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 3.1 | `layout.prop()` メソッド追加 | `GPULayout` クラスに追加 | Phase 2 |
| 3.2 | プロパティタイプ判定 | RNA から PropertyType を取得 | 3.1 |
| 3.3 | サブタイプ判定 | PropertySubType から適切なウィジェットを選択 | 3.2 |
| 3.4 | ウィジェット自動生成 | 判定結果に基づいてアイテム作成 | 3.3 |
| 3.5 | 値の双方向バインディング | プロパティ値の読み書き | 3.4 |

---

### Phase 4: テスト & デモ

| # | タスク | 詳細 | 依存 |
|---|--------|------|------|
| 4.1 | test_layout.py にウィジェットデモ追加 | 全ウィジェットの表示テスト | Phase 2 |
| 4.2 | 実際のプロパティとのバインディングテスト | `C.object.location` など | Phase 3 |
| 4.3 | パフォーマンステスト | 大量のプロパティ表示時の FPS | Phase 3 |

---

## 推奨実装順序

複雑さ・依存関係・視覚的インパクトを考慮した推奨順序：

```
Phase 1 (テーマ)
    ↓
┌───────────────────────────────────────────────────────┐
│ Phase 2.1: Slider      ★★★★☆  最も視覚的、スライダー │
│     ↓                                                 │
│ Phase 2.2: Number      ★★★☆☆  スライダーの簡易版    │
│     ↓                                                 │
│ Phase 2.3: Checkbox    ★★☆☆☆  シンプル              │
│     ↓                                                 │
│ Phase 2.4: Toggle      ★★☆☆☆  既存拡張              │
│     ↓                                                 │
│ Phase 2.8: Color       ★★☆☆☆  視覚的に面白い        │
│     ↓                                                 │
│ Phase 2.7: Radio       ★★★☆☆  Enum展開              │
│     ↓                                                 │
│ Phase 2.6: Menu        ★★★★☆  ポップアップ必要      │
│     ↓                                                 │
│ Phase 2.5: Text        ★★★★★  最も複雑              │
└───────────────────────────────────────────────────────┘
    ↓
Phase 3 (API)
    ↓
Phase 4 (テスト)
```

---

## チェックリスト

### Phase 1 完了条件
- [ ] ThemeWidgetColors クラスが動作する
- [ ] GPULayoutStyle から各 wcol_* にアクセスできる
- [ ] Blender テーマが正しく読み込まれる

### Phase 2 完了条件 (各ウィジェット)
- [ ] 静的な描画ができる
- [ ] テーマカラーが適用される
- [ ] ホバー状態が表示される
- [ ] クリック/ドラッグで値が変更できる
- [ ] test_layout.py でデモ表示できる

### Phase 3 完了条件
- [ ] `layout.prop(ptr, "property_name")` で自動的にウィジェットが生成される
- [ ] PropertyType に応じた適切なウィジェットが選択される
- [ ] 値の変更がプロパティに反映される

### Phase 4 完了条件
- [ ] 全ウィジェットのデモが動作する
- [ ] 実際の Blender プロパティとバインディングできる
- [ ] パフォーマンスが許容範囲内

---

## 見積もり

| Phase | 作業量目安 |
|-------|-----------|
| Phase 1 | 小 (1-2 sessions) |
| Phase 2.1 Slider | 中 (2-3 sessions) |
| Phase 2.2 Number | 小 (1-2 sessions) |
| Phase 2.3 Checkbox | 小 (1 session) |
| Phase 2.4 Toggle | 小 (1 session) |
| Phase 2.5 Text | 大 (3-5 sessions) |
| Phase 2.6 Menu | 中 (2-3 sessions) |
| Phase 2.7 Radio | 小 (1-2 sessions) |
| Phase 2.8 Color | 小 (1 session) |
| Phase 3 | 中 (2-3 sessions) |
| Phase 4 | 小 (1-2 sessions) |

---

## 参照

- `_docs/design/gpu_theme_widget_mapping.md` - テーマ・ウィジェット対応表
- `ui/gpu/style.py` - GPULayoutStyle クラス
- `ui/gpu/items.py` - 既存アイテムクラス
- `ui/gpu/layout.py` - GPULayout クラス

---

## 将来の改善点（TODO）

### Slider 改善

| 項目 | 詳細 | 優先度 |
|------|------|--------|
| **相対値モード** | クリック位置へジャンプせず、ドラッグ移動量のみ反映するモード | 中 |
| **精度モード（Shift）** | Shift 押下中は step を 1/10 にして細かい調整を可能に | 高 |

**実装案（精度モード）**:
```python
def on_drag(dx, dy, mouse_x, mouse_y, event):
    if event.shift:
        dx *= 0.1  # 精度モード
    item.set_value_from_position(mouse_x)
```

### Number 改善

| 項目 | 詳細 | 優先度 |
|------|------|--------|
| **増減ボタン HitRect** | `show_buttons=True` 時に左右ボタンに個別の HitRect を登録し、クリックで `increment()`/`decrement()` を呼び出す | 中 |
| **精度モード（Shift）** | Slider 同様、Shift 押下中は step を 1/10 に | 高 |

**実装案（ボタン HitRect）**:
- 左ボタン: `on_click=item.decrement`
- 右ボタン: `on_click=item.increment`
- メイン領域: 既存のドラッグ対応

---

## 進捗記録

| 日付 | Phase | 内容 |
|------|-------|------|
| 2026-01-16 | - | 計画作成 |
| 2026-01-16 | 2.1 | SliderItem 実装完了 |
| 2026-01-16 | 2.2 | NumberItem 実装完了 |
| 2026-01-16 | 2.3 | CheckboxItem 実装完了（wcol_option テーマ対応） |
| 2026-01-16 | 2.4 | ToggleItem 拡張完了（wcol_toggle テーマ対応） |
| 2026-01-16 | 2.8 | ColorItem 実装完了（チェッカーパターン・透明色対応） |
| 2026-01-17 | 2.7 | RadioGroupItem 実装完了（wcol_radio テーマ対応、on_move コールバック追加） |
| 2026-01-17 | 3 | **layout.prop() 実装完了**（RNA introspection、双方向バインディング） |
| 2026-01-17 | - | **リアクティブコンテキスト実装** (ContextProvider, PropertyBinding) |

---

## Phase 5: リアクティブコンテキスト（新規追加）

**目的**: 常時表示パネルとして、コンテキスト変更（オブジェクト選択変更など）に自動追従

**背景**: 従来の `prop(data, property)` はスナップショット参照を保持するため、
オブジェクト選択変更後も古いオブジェクトを参照し続ける問題があった。

### 5.1 ContextProvider

**ファイル**: `ui/gpu/context.py`

Blender コンテキストへの遅延アクセスを提供。

```python
provider = ContextProvider()
# プリセット: "object", "scene", "render", "material" などは自動登録済み

# 最新のデータを取得
obj = provider.get("object", bpy.context)  # 常に最新の context.object
```

### 5.2 PropertyBinding

プロパティとウィジェットのバインディング。遅延評価により常に最新のデータにアクセス。

### 5.3 ContextHash

コンテキスト変更を検知するためのハッシュ計算。

### 5.4 リアクティブ API

**ファイル**: `ui/gpu/layout.py`

```python
# プロバイダ設定
layout.set_context_provider(provider)

# リアクティブ prop（data_key を使用）
layout.prop_reactive("object", "hide_viewport", text="Hide")

# modal() 内で同期
context_changed = layout.sync_reactive(context)
if context_changed:
    # UI 再構築が必要
    rebuild_ui()
```

### 5.5 テスト用オペレーター

**ファイル**: `ui/gpu/test_reactive.py`

- `bpy.ops.pme.test_reactive_panel()` でテスト可能
- オブジェクト選択変更で UI が自動更新されることを確認

---

## Phase 3 実装詳細

### 3.1 RNA Introspection ユーティリティ

**ファイル**: `ui/gpu/rna_utils.py`（新規作成）

- `PropType` enum: BOOLEAN, INT, FLOAT, STRING, ENUM, POINTER, COLLECTION
- `WidgetHint` enum: CHECKBOX, TOGGLE, NUMBER, SLIDER, COLOR, TEXT, MENU, RADIO, VECTOR
- `PropertyInfo` dataclass: プロパティの全情報（タイプ、範囲、enum アイテムなど）
- `get_property_info(data, prop_name)`: RNA プロパティを解析
- `get_property_value()` / `set_property_value()`: 値の読み書き

### 3.2 layout.prop() API

**ファイル**: `ui/gpu/layout.py`

```python
layout.prop(data, property, *, text="", icon="", expand=False, slider=False, toggle=-1)
```

**対応状況**:

| PropertyType | WidgetHint | Widget | 状態 |
|--------------|------------|--------|------|
| BOOLEAN | CHECKBOX | CheckboxItem | ✅ |
| BOOLEAN | TOGGLE | ToggleItem | ✅ |
| INT/FLOAT | NUMBER | NumberItem | ✅ |
| INT/FLOAT | SLIDER | SliderItem | ✅ |
| FLOAT[] (COLOR) | COLOR | ColorItem | ✅（表示のみ） |
| ENUM | RADIO | RadioGroupItem | ✅ |
| ENUM | MENU | RadioGroupItem | ✅（フォールバック） |
| STRING | TEXT | - | ⏳ フォールバック |
| FLOAT[] (VECTOR) | VECTOR | - | ⏳ フォールバック |

### 3.3 双方向バインディング

- 各ウィジェットの `on_change` / `on_toggle` コールバックで `set_property_value()` を呼び出し
- 値変更が即座に Blender プロパティに反映される

---

*Last Updated: 2026-01-17*
