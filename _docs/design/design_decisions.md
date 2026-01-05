# PME2 Schema Design Decisions

> Date: 2026-01-05
> Status: Finalized for 2.0.0
> Mentor Review: Incorporated

---

## 概要

メンターレビューを踏まえた JSON Schema v2 の設計判断を記録する。

---

## 2.0.0 で確定した変更（コア）

### D1: $schema と version の分離

| 決定 | 採用 |
|------|------|
| 旧 | `$schema: "PME2"`, `version: "2.0.0"` |
| 新 | `$schema: URL`, `schema_version: "2.0"`, `addon_version: "2.0.0"` |

**根拠**:
- スキーマのバージョンとアドオンのバージョンは別物
- 将来 JSONSchema バリデーションを導入する際に URL が必要
- 2.1, 2.2…とスキーマを回した時に判別ロジックが明確

---

### D2: uid の導入（ID と Name の分離）

| 決定 | 採用 |
|------|------|
| 旧 | `name` で参照（一意制約） |
| 新 | `uid` で参照、`name` は表示用（重複可） |

**uid 形式**: `{mode_prefix}_{base32_random_8chars}`
- 例: `pm_9f7c2k3h`, `rm_a7xk01qz`

**根拠**:
- メニュー名のリネームがサブメニュー参照を壊す問題を解消
- CSM や AI 統合で自然言語を参照キーにするのは危険
- 編集したくならない ID で安定性を確保

**移行**:
- PME1 インポート時に uid を自動生成
- 既存 API は `name` 指定も許容（最初に見つかったものを使用）

---

### D3: description と description_expr の分離

| 決定 | 採用 |
|------|------|
| 旧 | `description` が Python 評価可能 |
| 新 | `description`（静的）+ `description_expr`（Python 式） |

**根拠**:
- 静的テキストと動的コードの混在は事故の元
- i18n が死ぬ（翻訳抽出できない）
- 将来セキュリティを気にし始めた時に全部見直しになる

**使い方**:
```json
// 静的のみ
{ "description": "立方体を追加", "description_expr": null }

// 動的のみ
{ "description": null, "description_expr": "'Selected: ' + str(len(C.selected_objects))" }

// 両方（結合して表示）
{ "description": "立方体を追加", "description_expr": "'（' + str(C.scene.cursor.location) + '）'" }
```

---

### D4: Style オブジェクト化

| 決定 | 採用 |
|------|------|
| 旧 | `color`, `use_color_bar` がフラット |
| 新 | `style` オブジェクト（継承モデル） |

**構造**:
```json
{
  "style": {
    "accent_color": "#4CAF50",
    "accent_usage": "bar"
  }
}
```

**accent_usage 列挙**: `none`, `bar`, `dot`, `background`

**根拠**:
- `use_color_bar` は実装詳細すぎる
- 将来「ドット」「背景」など別パターンを増やす時に困る
- Menu → MenuItem の継承モデルが自然に表現できる

---

### D5: extensions の vendor/feature 2階層構造

| 決定 | 採用 |
|------|------|
| 旧 | `extensions: { conditions: {...} }` |
| 新 | `extensions: { pme: { conditions: {...} } }` |

**根拠**:
- 外部ツールが独自拡張を入れられる
- PME 公式拡張と外部拡張の衝突を防ぐ
- 昇格時のマイグレーションパスが明確

**昇格ルール**:
1. 新スキーマで first-class フィールドを追加
2. 読み込み時: なければ `extensions.pme.{feature}` から引き継ぐ
3. 書き出し時: 新スキーマのみ

---

### D6: Hotkey の keymaps 配列化

| 決定 | 採用 |
|------|------|
| 旧 | `hotkey.keymap: "Window"` (単一) |
| 新 | `hotkey.keymaps: ["Window", "3D View"]` (複数可) |

**根拠**:
- 既存実装: PM は複数キーマップに登録可能（`km_name` が `;` 区切り）
- `keymaps` 配列で既存互換を維持しつつ構造化
- PME1 インポート時: `"Window; 3D View"` → `["Window", "3D View"]`

---

### D7: Settings キー名ルール

| 決定 | 採用 |
|------|------|
| モード固有 | 短い名前（`radius`, `flick`） |
| 複数モード共有 | 接頭辞付き（`pm_confirm`, `dlg_confirm`） |

**根拠**:
- 将来「やっぱり共有したい」になった時の rename 事故を減らせる

---

### D8: ActionType.operator の削除

| 決定 | 採用 |
|------|------|
| 旧 | `operator` タイプ（プロパティ指定付き） |
| 新 | 削除（`command` で十分） |

**根拠**:
- 既存実装の `MODE_ITEMS` に `OPERATOR` は無い
- `command` でオペレーター引数を直接指定可能（既存 UI あり）

---

### D9: action.type:command の undo 削除

| 決定 | 採用 |
|------|------|
| 旧 | `undo: true` |
| 新 | 削除 |

**根拠**:
- オペレーター引数 `bpy.ops.xxx(undo=True)` で制御可能（既存機能）
- 複雑な処理には `ed.undo_push()` を使用

---

### D10: action.type:menu の name 検索削除

| 決定 | 採用 |
|------|------|
| 旧 | `value` が uid または name |
| 新 | `value` は必ず uid |

**根拠**:
- name 検索は `command`/`custom` で内部関数を使う場合のみ
- uid で参照することでメニューリネームに強くなる

---

### D11: poll のデフォルト値

| 決定 | 採用 |
|------|------|
| 旧 | `null` |
| 新 | `"return True"` |

**根拠**:
- 既存実装: `constants.DEFAULT_POLL = "return True"`

---

### D12: DragDirection の 8方向化

| 決定 | 採用 |
|------|------|
| 旧 | `UP`, `DOWN`, `LEFT`, `RIGHT` |
| 新 | `NORTH`, `NORTH_EAST`, ..., `NORTH_WEST` (8方向) |

**根拠**:
- 既存実装: `constants.DRAG_DIR_ITEMS` が 8方向定義

---

### D13: accent_usage に bar-left/bar-right

| 決定 | 採用 |
|------|------|
| 旧 | `bar` |
| 新 | `bar-left`, `bar-right` |

**根拠**:
- 左右どちらに表示するか制御可能に

---

### D14: ActionType に Modal 専用モード追加

| 決定 | 採用 |
|------|------|
| 旧 | 6 種類（command, custom, prop, menu, hotkey, empty） |
| 新 | 10 種類（+ invoke, finish, cancel, update） |

**根拠**:
- 既存実装: `constants.MODAL_CMD_MODES` が定義
- `MODAL` タイプメニュー内のアイテム専用モード
- これがないと Modal Operator のエクスポート/インポートが不可能

**用途**:
| モード | 説明 |
|--------|------|
| `invoke` | Modal: On Invoke（開始時実行） |
| `finish` | Modal: On Confirm（確定時実行） |
| `cancel` | Modal: On Cancel（キャンセル時実行） |
| `update` | Modal: On Update（操作中実行） |

---

### D15: Hotkey に any/key_mod/chord 追加

| 決定 | 採用 |
|------|------|
| 旧 | key, ctrl, shift, alt, oskey のみ |
| 新 | + any, key_mod, chord |

**根拠**:
- 既存実装: `pme_types.PMItem` が定義
- `any`: すべての修飾キーを無視（Blender の kmi.any 相当）
- `key_mod`: 通常キー（A, B 等）を修飾キーとして使用
- `chord`: CHORDS アクティベーション時の 2 番目のキー

**欠落時の影響**:
- any=true で登録されたホットキーの情報喪失
- Key Chords 機能のエクスポート/インポートが不完全

---

### D16: アイコンフラグ記号の正確な定義

| 決定 | 採用 |
|------|------|
| 誤 | `!` = icon_only, `@` = hidden |
| 正 | `#` = icon_only, `!` = hidden, `@` = expand |

**根拠**:
- 既存実装: `constants.F_ICON_ONLY = "#"`, `F_HIDDEN = "!"`, `F_EXPAND = "@"`
- `^` (F_CB) は checkbox mode だが、現在エクスポート対象外

---

### D17: Settings プロパティ名の変換方針

| 決定 | 採用 |
|------|------|
| 内部形式 | `pm_radius`, `pm_flick` 等（接頭辞あり） |
| スキーマ形式 | `radius`, `flick` 等（接頭辞なし） |

**根拠**:
- スキーマは簡潔で読みやすくする
- 変換レイヤーで接頭辞の付与/除去を行う
- エクスポート時: `pm_` を除去
- インポート時: mode に応じた接頭辞を付加

---

### D18: type:custom から undo/use_try を削除

| 決定 | 採用 |
|------|------|
| 旧 | `undo`, `use_try` フィールドあり |
| 新 | `value` のみ |

**根拠**:
- CUSTOM モードは「UI 描画」であり「コマンド実行」ではない
- `use_try` は内部で常に `False` に固定（`operators/__init__.py:1360`）
- `undo` は描画コードには無関係
- 利用可能な変数: `L` (layout), `text`, `icon`, `icon_value`

---

## 2.1.0+ で検討するサブアイディア

以下は 2.0.0 のスコープ外。別 Issue で追跡する。

### I1: カラーパレット機能

**概要**: PME 内部に共有カラーパレットリソースを持つ

```json
{
  "palettes": [
    { "id": "danger", "color": "#ff5555" },
    { "id": "primary", "color": "#4a90d9" }
  ]
}
```

**メリット**:
- 色の一括管理
- Blender Theme 参照の足がかり

**Issue**: 別途作成

---

### I2: シーケンスホットキー

**概要**: `Ctrl+G` → `S` のような連続キー入力

```json
{
  "hotkey": {
    "type": "sequence",
    "items": [
      { "key": "G", "ctrl": true },
      { "key": "S", "ctrl": false }
    ]
  }
}
```

**メリット**:
- Emacs/Vim スタイルのキーバインド
- キー衝突の回避

**Issue**: 別途作成

---

### I3: Hotkey オブジェクトの items 配列化

**概要**: 単一キーも `items` 配列に統一

**現状**:
```json
{ "key": "A", "ctrl": false, "shift": true, "alt": false, "oskey": false }
```

**提案**:
```json
{
  "type": "single",
  "items": [{ "key": "A", "ctrl": false, "shift": true, "alt": false, "oskey": false }]
}
```

**判断**: シーケンスホットキー導入時に合わせて検討
**Issue**: I2 と同じ

---

### I4: Action type: "hotkey" の構造化

**概要**: `value: "CTRL+Z"` を Hotkey オブジェクトに置き換え

**Issue**: I2 と同じ

---

### I5: conditions 昇格（Context Sensitive Menu）

**概要**: `extensions.pme.conditions` を first-class に

**Issue**: 別途作成（2.1.0 ロードマップ）

---

## 2.0.0 実装の最小スコープ

| 項目 | 状態 |
|------|------|
| D1: $schema/version 分離 | ✅ 確定 |
| D2: uid 導入 | ✅ 確定 |
| D3: description/description_expr 分離 | ✅ 確定 |
| D4: Style オブジェクト化 | ✅ 確定 |
| D5: extensions 2階層 | ✅ 確定 |
| D6: keymaps 配列化 | ✅ 確定 |
| D7: Settings キー名ルール | ✅ 確定 |
| D8: ActionType.operator 削除 | ✅ 確定 |
| D9: action.undo 削除 | ✅ 確定 |
| D10: menu の uid 参照のみ | ✅ 確定 |
| D11: poll デフォルト "return True" | ✅ 確定 |
| D12: DragDirection 8方向 | ✅ 確定 |
| D13: accent_usage bar-left/right | ✅ 確定 |
| D14: ActionType に Modal 専用モード追加 | ✅ 確定 |
| D15: Hotkey に any/key_mod/chord 追加 | ✅ 確定 |
| D16: アイコンフラグ記号の正確な定義 | ✅ 確定 |
| D17: Settings プロパティ名の変換方針 | ✅ 確定 |
| D18: type:custom から undo/use_try 削除 | ✅ 確定 |

| 項目 | 状態 |
|------|------|
| I1: カラーパレット | ⏳ 2.1.0+ |
| I2: シーケンスホットキー | ⏳ 2.1.0+ |
| I3: items 配列化 | ⏳ 2.1.0+ |
| I4: hotkey 構造化 | ⏳ 2.1.0+ |
| I5: conditions 昇格 | ⏳ 2.1.0 |

---

## 参照

- メンターレビュー: 2026-01-05
- 関連ドキュメント:
  - `@_docs/design/json_schema_v2.md` — JSON 形式仕様
  - `@_docs/design/schema_v2_analysis.md` — 可能性と限界の分析
  - `@_docs/design/schema_v2_future_extensibility.md` — 将来拡張性

---

*Last Updated: 2026-01-05*
