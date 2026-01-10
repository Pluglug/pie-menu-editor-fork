# PME2 JSON Schema Design v2.0

> Version: 2.0.0-rc1
> Status: **Design Finalized**
> Last Updated: 2026-01-05
> Design Review: Mentor feedback incorporated
> GitHub Milestone: [2.0.0 - JSON Schema v2](https://github.com/Pluglug/pie-menu-editor-fork/milestone/1)
> Tracking Issue: [#78](https://github.com/Pluglug/pie-menu-editor-fork/issues/78)

---

## 関連 Issue

| Issue | タイトル |
|-------|---------|
| #79 | PME2: Menu name/uid separation and reference redesign |
| #80 | PME2: Style system - Color bar visualization like Node Pie |
| #81 | PME2: description / description_expr implementation |
| #82 | PME2: Action.context implementation for operator context override |

---

## 設計原則

| 原則 | 説明 |
|------|------|
| **名前付きキー** | 位置ベースのタプルではなくオブジェクトを使用 |
| **ID と Name の分離** | 参照用 uid と表示用 name を分ける |
| **暗黙のデフォルトゼロ** | 全フィールドに明示的なデフォルト値を定義 |
| **静的/動的の分離** | description (静的) と description_expr (Python式) を分ける |
| **Style オブジェクト化** | 色・装飾は style にまとめ、継承モデルを適用 |
| **vendor/feature 拡張** | extensions は 2 階層構造で管理 |
| **後方互換** | PME1 形式からのインポート変換をサポート |

---

## 全体構造

```json
{
  "$schema": "https://pluglug.github.io/pme/schema/pme2-2.0.json",
  "schema_version": "2.0",
  "addon_version": "2.0.0",
  "exported_at": "2026-01-05T12:00:00Z",

  "menus": [Menu, ...],
  "tags": ["modeling", "sculpting"],
  "extensions": {}
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `$schema` | string | ✓ | - | スキーマ URL（将来の JSONSchema 検証用） |
| `schema_version` | string | ✓ | - | スキーマのバージョン（`"2.0"`, `"2.1"` 等） |
| `addon_version` | string | ✓ | - | エクスポートしたアドオンのバージョン |
| `exported_at` | string | - | null | RFC 3339 形式のタイムスタンプ |
| `menus` | Menu[] | ✓ | - | メニューの配列 |
| `tags` | string[] | - | [] | 使用されているタグの一覧（検索/フィルタ用） |
| `extensions` | object | - | {} | ファイルレベルの拡張フィールド |

---

## Menu オブジェクト

```json
{
  "uid": "pm_9f7c2k3h",
  "name": "My Pie Menu",
  "mode": "PMENU",
  "enabled": true,

  "hotkey": {
    "key": "A",
    "ctrl": false,
    "shift": true,
    "alt": false,
    "oskey": false,
    "keymaps": ["Window", "3D View"],
    "activation": "PRESS",
    "drag_direction": null
  },

  "settings": {
    "radius": 100,
    "flick": true,
    "confirm": -1,
    "threshold": -1
  },

  "description": "モデリング作業用のメインメニュー",
  "description_expr": null,

  "poll": null,
  "tags": ["modeling"],

  "items": [MenuItem, ...],

  "extensions": {}
}
```

### Menu フィールド

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `uid` | string | ✓ | - | 一意 ID（`{mode_prefix}_{base32_random}`）|
| `name` | string | ✓ | - | 表示名（重複可、ただし UI で警告） |
| `mode` | MenuMode | ✓ | - | メニュータイプ |
| `enabled` | boolean | ✓ | true | 有効/無効 |
| `hotkey` | Hotkey \| null | - | null | ホットキー設定 |
| `settings` | object | ✓ | {} | モード別設定（フラット） |
| `description` | string \| null | - | null | 静的な説明文（`\n` で改行） |
| `description_expr` | string \| null | - | null | Python 式による動的説明文 |
| `poll` | string | - | "return True" | ポーリング条件（Python式） |
| `tags` | string[] | - | [] | タグの配列 |
| `items` | MenuItem[] | ✓ | [] | メニューアイテムの配列 |
| `extensions` | object | - | {} | 拡張フィールド |

### uid の形式

```
{mode_prefix}_{random_id}

mode_prefix:
  pm  - Pie Menu (PMENU)
  rm  - Regular Menu (RMENU)
  pd  - Pop-up Dialog (DIALOG)
  pg  - Panel Group (PANEL)
  hpg - Hiding Panel (HPANEL)  # Note: hpg not hp (PME v1 official)
  sk  - Stack Key (SCRIPT)
  mc  - Macro Operator (MACRO)
  md  - Modal Operator (MODAL)
  st  - Sticky Key (STICKY)
  pr  - Property (PROPERTY)

random_id:
  uuid4 を base32 エンコードした 8 文字（例: 9f7c2k3h）
```

**uid 生成ルール**:
- メニュー作成時に一度だけ生成
- 複製時は新しい uid を生成
- インポート時は既存 uid を維持（衝突時は再生成）
- 編集不可（UI で変更できない）

### MenuMode 列挙

| 値 | 説明 | uid prefix |
|----|------|-----------|
| `PMENU` | Pie Menu | pm |
| `RMENU` | Regular Menu | rm |
| `DIALOG` | Pop-up Dialog | pd |
| `PANEL` | Side Panel (Panel Group) | pg |
| `HPANEL` | Hiding Unused Panels | hpg |
| `SCRIPT` | Stack Key | sk |
| `MACRO` | Macro Operator | mc |
| `MODAL` | Modal Operator | md |
| `STICKY` | Sticky Key | st |
| `PROPERTY` | Property | pr |

---

## Hotkey オブジェクト

```json
{
  "key": "A",
  "ctrl": false,
  "shift": true,
  "alt": false,
  "oskey": false,
  "any": false,
  "key_mod": "NONE",
  "chord": "NONE",
  "keymaps": ["Window", "3D View"],
  "activation": "PRESS",
  "drag_direction": "ANY"
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `key` | string | ✓ | "NONE" | キー名 (`"A"`, `"SPACE"`, `"F1"` 等) |
| `ctrl` | boolean | - | false | Ctrl 修飾キー |
| `shift` | boolean | - | false | Shift 修飾キー |
| `alt` | boolean | - | false | Alt 修飾キー |
| `oskey` | boolean | - | false | OS キー (Cmd/Super) |
| `any` | boolean | - | false | Any キー（すべての修飾キーを無視） |
| `key_mod` | string | - | "NONE" | 通常キーを修飾キーとして使用 |
| `chord` | string | - | "NONE" | Key Chords の 2 番目のキー（CHORDS モード時） |
| `keymaps` | string[] | - | ["Window"] | 登録先キーマップ（複数可） |
| `activation` | ActivationMode | - | "PRESS" | アクティベーションモード |
| `drag_direction` | DragDirection | - | "ANY" | ドラッグ方向（CLICK_DRAG時のみ有効） |

**Note**:
- `keymaps` は既存の `km_name` の `;` 区切りと互換
- PME1 インポート時は `"Window; 3D View"` → `["Window", "3D View"]` に変換
- `any` は Blender の kmi.any に対応（全修飾キーを無視）
- `key_mod` は通常キー（A, B, etc.）を修飾キーとして使うための設定
- `chord` は CHORDS アクティベーション時のみ有効（連続キー入力の 2 番目）

### ActivationMode 列挙

> 準拠: `constants.OPEN_MODE_ITEMS`

| 値 | 説明 |
|----|------|
| `PRESS` | キーを押した瞬間 |
| `HOLD` | キーを押し続けている間 |
| `DOUBLE_CLICK` | ダブルクリック |
| `TWEAK` | Click Drag（ホールド＆ドラッグ） |
| `CHORDS` | Key Chords（2キー連続） |
| `CLICK` | Click (Experimental) |
| `CLICK_DRAG` | Click Drag (Experimental) |

### DragDirection 列挙

> 準拠: `constants.DRAG_DIR_ITEMS`

| 値 | 説明 |
|----|------|
| `ANY` | 任意の方向 |
| `NORTH` | 北（上） |
| `NORTH_EAST` | 北東 |
| `EAST` | 東（右） |
| `SOUTH_EAST` | 南東 |
| `SOUTH` | 南（下） |
| `SOUTH_WEST` | 南西 |
| `WEST` | 西（左） |
| `NORTH_WEST` | 北西 |

---

## Style オブジェクト（extensions 配下）

> **Note**: Style は将来機能（Issue #80）のため、`extensions.pme.style` に配置。
> 安定後に first-class フィールドに昇格予定。

Menu と MenuItem で共通の構造。MenuItem は Menu の style を継承し、上書きできる。

```json
{
  "extensions": {
    "pme": {
      "style": {
        "accent_color": "#4CAF50",
        "accent_usage": "bar-left"
      }
    }
  }
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `accent_color` | string \| null | - | null | 直接指定の色（`#RRGGBB`） |
| `accent_usage` | AccentUsage | - | "none" | 色の表示方法 |

**色の解決順序**:
1. `accent_color` が指定されていればそれを使用
2. どちらもなければ親（Menu）の style を継承
3. 親もなければデフォルト（色なし）

### AccentUsage 列挙

| 値 | 説明 |
|----|------|
| `none` | 色を表示しない |
| `bar-left` | 左端にカラーバー表示 |
| `bar-right` | 右端にカラーバー表示 |
| `dot` | アイコン横にドット表示(将来のAPI期待) |
| `background` | 背景色として表示(将来のAPI期待) |

---

## Settings（モード別プロパティ）

settings はフラット構造で、mode に応じて異なるプロパティが入る。

### 内部形式との対応

> **方針**: JSON Schema のプロパティ名は内部形式（`pm.data`）と**同一**にする。
> 変換処理を不要とし、シンプルさと AI フレンドリーを優先。

| JSON Schema | 内部形式 (pm.data) | 備考 |
|-------------|-------------------|------|
| `pm_radius` | `pm_radius` | 同一（変換不要） |
| `pd_panel` | `pd_panel` | 同一（変換不要） |
| `confirm` | `confirm` | MODAL は接頭辞なし |
| `vector` | `vector` | PROPERTY は接頭辞なし |

### 接頭辞パターン

| モード | 接頭辞 | 例 |
|--------|--------|-----|
| PMENU | `pm_` | `pm_radius`, `pm_flick` |
| RMENU | `rm_` | `rm_title` |
| DIALOG | `pd_` | `pd_panel`, `pd_width` |
| PANEL | `pg_` | `pg_space`, `pg_wicons` |
| MODAL | なし | `confirm`, `block_ui` |
| SCRIPT | `s_` | `s_undo`, `s_state` |
| STICKY | `sk_` | `sk_block_ui` |
| PROPERTY | なし/混在 | `vector`, `prop_type` |

### PMENU (Pie Menu)

```json
{
  "pm_radius": -1,
  "pm_flick": true,
  "pm_confirm": -1,
  "pm_threshold": -1
}
```

| プロパティ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `pm_radius` | integer | -1 | 半径（-1 = デフォルト） |
| `pm_flick` | boolean | true | フリック確定 |
| `pm_confirm` | integer | -1 | 確定時間（-1 = デフォルト） |
| `pm_threshold` | integer | -1 | しきい値（-1 = デフォルト） |

### RMENU (Regular Menu)

```json
{
  "rm_title": true,
  "rm_extend_target": null,
  "rm_extend_position": "append"
}
```

| プロパティ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `rm_title` | boolean | true | タイトルを表示 |
| `rm_extend_target` | string \| null | null | 拡張対象の Blender Menu ID |
| `rm_extend_position` | string | "append" | 挿入位置（"append" / "prepend"） |

### DIALOG (Pop-up Dialog)

```json
{
  "pd_title": true,
  "pd_box": true,
  "pd_width": 300,
  "pd_auto_close": false,
  "pd_expand": false,
  "pd_panel": 1,
  "pd_extend_target": null,
  "pd_extend_position": "append"
}
```

| プロパティ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `pd_title` | boolean | true | タイトルを表示 |
| `pd_box` | boolean | true | ボックス表示 |
| `pd_width` | integer | 300 | ダイアログ幅 |
| `pd_auto_close` | boolean | false | 自動クローズ |
| `pd_expand` | boolean | false | 展開表示 |
| `pd_panel` | integer | 1 | 表示モード（0=PIE, 1=PANEL, 2=POPUP） |
| `pd_extend_target` | string \| null | null | 拡張対象の Blender Panel ID |
| `pd_extend_position` | string | "append" | 挿入位置（"append" / "prepend"） |

### PANEL (Panel Group)

```json
{
  "pg_space": "VIEW_3D",
  "pg_region": "TOOLS",
  "pg_context": "ANY",
  "pg_category": "My Category",
  "pg_wicons": false,
  "pg_extend_target": null,
  "pg_extend_position": "append"
}
```

| プロパティ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `pg_space` | string | "VIEW_3D" | スペースタイプ |
| `pg_region` | string | "TOOLS" | リージョンタイプ |
| `pg_context` | string | "ANY" | コンテキスト |
| `pg_category` | string | "My Category" | カテゴリ名 |
| `pg_wicons` | boolean | false | アイコン表示 |
| `pg_extend_target` | string \| null | null | 拡張対象の Blender Panel ID |
| `pg_extend_position` | string | "append" | 挿入位置（"append" / "prepend"） |

### MODAL (Modal Operator)

```json
{
  "confirm": false,
  "block_ui": true,
  "lock": true
}
```

| プロパティ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `confirm` | boolean | false | 確認ダイアログ |
| `block_ui` | boolean | true | UI ブロック |
| `lock` | boolean | true | ロック |

### SCRIPT (Stack Key)

```json
{
  "s_undo": false,
  "s_state": false
}
```

| プロパティ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `s_undo` | boolean | false | Undo 有効 |
| `s_state` | boolean | false | 状態保持 |

### STICKY (Sticky Key)

```json
{
  "sk_block_ui": false
}
```

| プロパティ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `sk_block_ui` | boolean | false | UI ブロック |

### PROPERTY

```json
{
  "prop_type": "FLOAT",
  "vector": 1,
  "mulsel": false,
  "hor_exp": true,
  "exp": true,
  "save": true
}
```

| プロパティ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `prop_type` | string | "BOOL" | プロパティタイプ（必須） |
| `vector` | integer | 1 | ベクトル次元 |
| `mulsel` | boolean | false | 複数選択対応 |
| `hor_exp` | boolean | true | 水平展開 |
| `exp` | boolean | true | 展開表示 |
| `save` | boolean | true | 設定を保存 |

**prop_type の値**:
| 値 | 説明 |
|----|------|
| `BOOL` | Boolean プロパティ |
| `INT` | Integer プロパティ |
| `FLOAT` | Float プロパティ |
| `STRING` | String プロパティ |
| `ENUM` | Enum プロパティ |

> **PME1 互換性**: PME1 では `poll_cmd` フィールドが PROPERTY モードでプロパティタイプを格納していた。
> PME2 では `settings.prop_type` に分離し、`poll` は常に poll 条件として使用する。

> **実装注意**: 内部実装では `prop_type` は `pm.poll_cmd` に直接格納されており、
> `pm.data` 経由ではない。converter/serializer で特別な処理が必要。

### MACRO

追加設定なし（内部データタイプ: `m?`）

### HPANEL (Hiding Panel)

追加設定なし（内部データタイプ: `hpg?`）

---

## MenuItem オブジェクト

```json
{
  "name": "Add Cube",
  "action": {
    "type": "command",
    "value": "bpy.ops.mesh.primitive_cube_add()",
    "context": null
  },
  "icon": "MESH_CUBE",
  "icon_only": false,
  "hidden": false,
  "enabled": true,

  "description": "シーンに立方体プリミティブを追加",
  "description_expr": null,

  "extensions": {
    "pme": {
      "style": {
        "accent_color": "#4CAF50",
        "accent_usage": "bar-left"
      }
    }
  }
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| `name` | string | ✓ | - | 表示名 |
| `action` | Action | ✓ | - | 実行アクション |
| `icon` | string \| null | - | null | アイコン名 |
| `icon_only` | boolean | - | false | アイコンのみ表示 |
| `hidden` | boolean | - | false | 非表示 |
| `enabled` | boolean | ✓ | true | 有効/無効 |
| `description` | string \| null | - | null | 静的な説明文 |
| `description_expr` | string \| null | - | null | Python 式による動的説明文 |
| `extensions` | object | - | {} | 拡張フィールド（`pme.style` など） |

### description と description_expr の使い分け

```json
// 静的テキストのみ
{
  "description": "シーンに立方体を追加します",
  "description_expr": null
}

// 動的テキストのみ
{
  "description": null,
  "description_expr": "'Selected: ' + str(len(C.selected_objects)) + ' objects'"
}

// 両方（description_expr の結果を description の後に追加）
{
  "description": "立方体を追加",
  "description_expr": "'（カーソル位置: ' + str(C.scene.cursor.location) + '）'"
}
// → "立方体を追加（カーソル位置: <0, 0, 0>）"
```

**i18n への配慮**: `description` は翻訳可能な静的テキスト。`description_expr` は翻訳対象外。

---

## Action オブジェクト

アクションの種類によって異なる構造を持つ。`type` フィールドで判別。

### 共通フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `type` | ActionType | ✓ | アクションの種類 |
| `value` | string | ✓ | 実行内容 |

### ActionType 列挙

> 準拠: `constants.MODE_ITEMS` / `constants.EMODE_ITEMS`

| 値 | 説明 | 用途 |
|----|------|------|
| `command` | Blender オペレーター / Python コード | 全メニュー |
| `custom` | カスタムレイアウト Python コード | 全メニュー |
| `prop` | プロパティ表示/編集 | 全メニュー |
| `menu` | サブメニュー | 全メニュー |
| `hotkey` | ホットキー実行 | 全メニュー |
| `empty` | 空スロット | 全メニュー |
| `invoke` | Modal: On Invoke | MODAL のみ |
| `finish` | Modal: On Confirm | MODAL のみ |
| `cancel` | Modal: On Cancel | MODAL のみ |
| `update` | Modal: On Update | MODAL のみ |

**Note**: `invoke`, `finish`, `cancel`, `update` は `MODAL_CMD_MODES` に含まれる Modal Operator 専用モード。

### type: "command"

```json
{
  "type": "command",
  "value": "bpy.ops.mesh.primitive_cube_add()",
  "context": null
}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `context` | string \| null | null | コンテキストオーバーライド（Python式、with 構文用） |

### type: "custom"

カスタム UI レイアウトを描画する Python コード。

```json
{
  "type": "custom",
  "value": "L.label(text, icon=icon)\nL.operator('mesh.primitive_cube_add')"
}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `value` | string | - | レイアウト描画コード |

### type: "prop"

```json
{
  "type": "prop",
  "value": "C.object.location",
  "expand": false,
  "slider": false,
  "toggle": false
}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `expand` | boolean | false | ベクトルを展開表示 |
| `slider` | boolean | false | スライダー表示 |
| `toggle` | boolean | false | トグルボタン表示 |

### type: "menu"

```json
{
  "type": "menu",
  "value": "pm_9f7c2k3h",
  "mode": "inherit"
}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `value` | string | - | 参照先メニューの **uid** |
| `mode` | string | "inherit" | 表示モード（`"inherit"`, `"popup"`, `"pie"`） |

**PME1 変換時の注意**:
- PME1 では `value` が name（表示名）で参照されている
- インポート時に name → uid への参照解決が必要
- 解決できない場合はエラーまたは警告を出力

### type: "hotkey"

```json
{
  "type": "hotkey",
  "value": "CTRL+Z"
}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `value` | string | - | ホットキー文字列（`"CTRL+Z"`, `"SHIFT+A"` 等） |

**Note**: 2.1.0+ でより構造化された形式を検討予定。

### type: "empty"

```json
{
  "type": "empty",
  "value": ""
}
```

空スロット用。Pie Menu の固定スロット数を維持するために使用。

---

## extensions の設計

extensions は **vendor/feature の 2 階層構造**で管理する。

```json
{
  "extensions": {
    "pme": {
      "conditions": {
        "when": "context.mode == 'EDIT_MESH'",
        "fallback": "hidden"
      }
    },
    "other_addon": {
      "custom_feature": { "enabled": true }
    }
  }
}
```

### 構造ルール

| 階層 | 説明 | 例 |
|------|------|-----|
| vendor | 拡張の提供者 | `"pme"`, `"other_addon"` |
| feature | 機能名 | `"conditions"`, `"spatial"` |

### 昇格ポリシー

extensions 内で試験的に導入した機能は、安定後に first-class フィールドに昇格できる。

**昇格時のマイグレーション**:
1. 新スキーマバージョンで first-class フィールドを追加
2. 読み込み時: first-class フィールドがなければ `extensions.pme.{feature}` から引き継ぐ
3. 書き出し時: 新スキーマのみ（extensions から削除）

---

## PME1 からの変換マッピング

### Menu タプル → Menu オブジェクト

| PME1 Index | PME1 Field | PME2 Field |
|------------|-----------|------------|
| 0 | name | `name` (+ uid 自動生成) |
| 1 | km_name | `hotkey.keymaps` (`;` 区切り → 配列) |
| 2 | hotkey | `hotkey.*` (パース、下記参照) |
| 3 | items | `items` (変換) |
| 4 | mode | `mode` |
| 5 | data | `settings` (パース) |
| 6 | open_mode | `hotkey.activation` |
| 7 | poll_cmd | `poll` または `settings.prop_type`（※） |
| 8 | tag | `tags` (分割) |
| 9 | enabled | `enabled` (v1.19.x+) |
| 10 | drag_dir | `hotkey.drag_direction` (v1.19.x+) |

> **※ poll_cmd の特殊処理**:
> - 通常モード: `poll_cmd` → `poll`（poll 条件）
> - PROPERTY モード: `poll_cmd` → `settings.prop_type`（プロパティタイプ）
>
> PME1 では PROPERTY モードで `poll_cmd` フィールドがプロパティタイプ
> (`"BOOL"`, `"INT"`, `"FLOAT"`, `"STRING"`, `"ENUM"`) を格納していた。

### Hotkey 文字列のパース

PME1 の `hotkey` は encode された文字列形式。以下のフィールドを含む：

| PME1 エンコード | PME2 Field |
|----------------|------------|
| key | `hotkey.key` |
| ctrl | `hotkey.ctrl` |
| shift | `hotkey.shift` |
| alt | `hotkey.alt` |
| oskey | `hotkey.oskey` |
| any | `hotkey.any` |
| key_mod | `hotkey.key_mod` |
| chord | `hotkey.chord` |

### uid の自動生成

PME1 からのインポート時:
1. mode から prefix を決定
2. uuid4 を base32 エンコードして 8 文字の random_id を生成
3. `{prefix}_{random_id}` を uid として設定

### MenuItem タプル → MenuItem オブジェクト

| PME1 Index | PME1 Field | PME2 Field |
|------------|-----------|------------|
| 0 | name | `name` |
| 1 | mode | `action.type` (小文字に変換) |
| 2 | icon | `icon` + フラグ分離 |
| 3 | text | `action.value` |
| 4 | flags | `enabled` (ビット0) |

### アイコンフラグの分離

> 準拠: `constants.F_ICON_ONLY`, `F_HIDDEN`, `F_EXPAND`, `F_CB`

```
PME1: "#!MESH_CUBE"
↓
PME2: {
  "icon": "MESH_CUBE",
  "icon_only": true,   // # (F_ICON_ONLY)
  "hidden": true       // ! (F_HIDDEN)
}
```

| フラグ文字 | 定数 | PME2 フィールド |
|-----------|------|-----------------|
| `#` | F_ICON_ONLY | `icon_only: true` |
| `!` | F_HIDDEN | `hidden: true` |
| `@` | F_EXPAND / F_CUSTOM_ICON | `expand: true`（custom 用） |
| `^` | F_CB | 未エクスポート（checkbox mode） |

---

## バージョン互換性

| バージョン | 形式 | 検出方法 |
|-----------|------|---------|
| < 1.13.6 | リスト（タプルの配列） | `isinstance(data, list)` |
| 1.13.6 - 1.18.x | dict + version | `"menus" in data` and no `$schema` |
| 1.19.x (PME-F) | dict + version + 11項目 | `len(menu) >= 11` |
| 2.0.0+ (PME2) | dict + $schema | `"$schema" in data` |

### スキーマバージョン

| schema_version | 変更点 |
|---------------|--------|
| 2.0 | 初版（uid, description/description_expr, extend_target in settings, style in extensions） |
| 2.1 | conditions, style 昇格予定 |

---

## 参照

- `@_docs/design/design_decisions.md` — 設計判断の記録
- `@_docs/design/schema_v2_analysis.md` — 可能性と限界の分析
- `@_docs/design/schema_v2_future_extensibility.md` — 将来拡張性の検討

---

*Last Updated: 2026-01-10*
*Design Review: 9-D diagnosis incorporated*
