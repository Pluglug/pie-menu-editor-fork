# PME2 JSON Schema Design

> Version: 2.0.0-draft
> Status: Design Phase
> Copied from: pme_mini/.claude/design/json_schema_v2.md

---

## 設計原則

| 原則 | 説明 |
|------|------|
| **名前付きキー** | 位置ベースのタプルではなくオブジェクトを使用 |
| **フラット設定** | mode でスキーマが決まるため settings はネストしない |
| **分離されたフラグ** | icon フラグ等は別フィールドに展開 |
| **null 許容** | オプショナルな値は null を許容 |
| **後方互換** | PME1 形式からのインポート変換をサポート |

---

## 全体構造

```json
{
  "$schema": "PME2",
  "version": "2.0.0",
  "exported_at": "2026-01-03T12:00:00Z",
  "menus": [Menu, ...],
  "tags": ["tag1", "tag2"]
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `$schema` | string | ✓ | スキーマ識別子 `"PME2"` |
| `version` | string | ✓ | エクスポートしたアドオンのバージョン |
| `exported_at` | string | - | ISO 8601 形式のタイムスタンプ |
| `menus` | Menu[] | ✓ | メニューの配列 |
| `tags` | string[] | - | 使用されているタグの一覧 |

---

## Menu オブジェクト

```json
{
  "name": "My Pie Menu",
  "mode": "PMENU",
  "enabled": true,

  "hotkey": {
    "key": "A",
    "ctrl": false,
    "shift": true,
    "alt": false,
    "oskey": false,
    "keymap": "Window",
    "activation": "PRESS",
    "drag_direction": null
  },

  "settings": {
    "radius": 100,
    "flick": true,
    "confirm": -1,
    "threshold": -1
  },

  "poll": null,
  "tags": ["modeling"],

  "items": [MenuItem, ...]
}
```

### Menu フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `name` | string | ✓ | メニュー名（一意） |
| `mode` | MenuMode | ✓ | メニュータイプ |
| `enabled` | boolean | ✓ | 有効/無効 |
| `hotkey` | Hotkey | ✓ | ホットキー設定 |
| `settings` | object | ✓ | モード別設定（フラット） |
| `poll` | string \| null | - | ポーリング条件（Python式） |
| `tags` | string[] | - | タグの配列 |
| `items` | MenuItem[] | ✓ | メニューアイテムの配列 |

### MenuMode 列挙

```
PMENU    - Pie Menu
RMENU    - Regular Menu
DIALOG   - Pop-up Dialog
PANEL    - Side Panel (Panel Group)
HPANEL   - Hiding Unused Panels
SCRIPT   - Stack Key
MACRO    - Macro Operator
MODAL    - Modal Operator
STICKY   - Sticky Key
PROPERTY - Property
```

---

## Hotkey オブジェクト

```json
{
  "key": "A",
  "ctrl": false,
  "shift": true,
  "alt": false,
  "oskey": false,
  "keymap": "Window",
  "activation": "PRESS",
  "drag_direction": null
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `key` | string | ✓ | キー名 (`"A"`, `"SPACE"`, `"F1"` 等) |
| `ctrl` | boolean | ✓ | Ctrl 修飾キー |
| `shift` | boolean | ✓ | Shift 修飾キー |
| `alt` | boolean | ✓ | Alt 修飾キー |
| `oskey` | boolean | ✓ | OS キー (Cmd/Super) |
| `keymap` | string | ✓ | キーマップ名 |
| `activation` | ActivationMode | ✓ | アクティベーションモード |
| `drag_direction` | DragDirection \| null | - | ドラッグ方向（CLICK_DRAG時のみ） |

### ActivationMode 列挙

```
PRESS        - キーを押した瞬間
HOLD         - キーを押し続けている間
CLICK        - クリック（押して離す）
CLICK_DRAG   - クリックドラッグ
DOUBLE_CLICK - ダブルクリック
ONE_SHOT     - ワンショット
CHORDS       - コード（複数キー）
```

### DragDirection 列挙

```
ANY   - 任意の方向
UP    - 上
DOWN  - 下
LEFT  - 左
RIGHT - 右
```

---

## Settings（モード別プロパティ）

settings はフラット構造で、mode に応じて異なるプロパティが入る。

### PMENU (Pie Menu)

```json
{
  "radius": 100,
  "flick": true,
  "confirm": -1,
  "threshold": -1
}
```

| プロパティ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `radius` | integer | -1 | 半径（-1 = デフォルト） |
| `flick` | boolean | true | フリック確定 |
| `confirm` | integer | -1 | 確定時間 |
| `threshold` | integer | -1 | しきい値 |

### RMENU (Regular Menu)

```json
{
  "title": true
}
```

### DIALOG (Pop-up Dialog)

```json
{
  "title": true,
  "box": false,
  "width": 300,
  "auto_close": true,
  "expand": false,
  "panel": false
}
```

### PANEL (Panel Group)

```json
{
  "space": "VIEW_3D",
  "region": "UI",
  "context": "NONE",
  "category": "My Panel",
  "icons": false
}
```

### MODAL (Modal Operator)

```json
{
  "confirm": false,
  "block_ui": true,
  "lock": true
}
```

### SCRIPT / STICKY

```json
{
  "undo": false,
  "state": false,
  "block_ui": false
}
```

---

## MenuItem オブジェクト

```json
{
  "name": "Add Cube",
  "action": {
    "type": "command",
    "value": "bpy.ops.mesh.primitive_cube_add()",
    "undo": true,
    "context": null
  },
  "icon": "MESH_CUBE",
  "icon_only": false,
  "hidden": false,
  "enabled": true
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `name` | string | ✓ | 表示名 |
| `action` | Action | ✓ | 実行アクション（空スロットの場合も必須） |
| `icon` | string | - | アイコン名 |
| `icon_only` | boolean | - | アイコンのみ表示 |
| `hidden` | boolean | - | 非表示 |
| `enabled` | boolean | ✓ | 有効/無効 |

---

## Action オブジェクト

アクションの種類によって異なる構造を持つ。`type` フィールドで判別。

### 共通フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `type` | ActionType | ✓ | アクションの種類 |
| `value` | string | ✓ | 実行内容（コマンド/スクリプト/パス等） |

### ActionType 列挙

```
command  - Blender オペレーター
custom   - カスタム Python スクリプト
prop     - プロパティ表示/編集
menu     - サブメニュー
hotkey   - ホットキー実行
operator - オペレーター（UI設定付き）
empty    - 空スロット
```

### type: "command" (Blender オペレーター)

```json
{
  "type": "command",
  "value": "bpy.ops.mesh.primitive_cube_add()",
  "undo": true,
  "context": null
}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `undo` | boolean | true | Undo 履歴に追加 |
| `context` | string \| null | null | コンテキストオーバーライド（Python式） |

### type: "custom" (カスタムスクリプト)

```json
{
  "type": "custom",
  "value": "print('Hello')\nbpy.ops.mesh.primitive_cube_add()",
  "undo": false,
  "use_try": true
}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `undo` | boolean | false | Undo 履歴に追加 |
| `use_try` | boolean | true | try-except でエラーをキャッチ |

### type: "prop" (プロパティ)

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

### type: "menu" (サブメニュー)

```json
{
  "type": "menu",
  "value": "Other Menu Name",
  "mode": "inherit"
}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `mode` | string | "inherit" | 表示モード（"inherit", "popup", "pie"） |

### type: "hotkey" (ホットキー実行)

```json
{
  "type": "hotkey",
  "value": "CTRL+Z"
}
```

### type: "operator" (オペレーター with UI)

```json
{
  "type": "operator",
  "value": "mesh.primitive_cube_add",
  "properties": {
    "size": 2.0,
    "enter_editmode": true
  }
}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `properties` | object | {} | オペレータープロパティ |

### type: "empty" (空スロット)

```json
{
  "type": "empty",
  "value": ""
}
```

空スロット用。Pie Menu の固定スロット数を維持するために使用。

---

## PME1 からの変換マッピング

### Menu タプル → Menu オブジェクト

| PME1 Index | PME1 Field | PME2 Field |
|------------|-----------|------------|
| 0 | name | `name` |
| 1 | km_name | `hotkey.keymap` |
| 2 | hotkey | `hotkey.*` (パース) |
| 3 | items | `items` (変換) |
| 4 | mode | `mode` |
| 5 | data | `settings` (パース) |
| 6 | open_mode | `hotkey.activation` |
| 7 | poll_cmd | `poll` |
| 8 | tag | `tags` (分割) |
| 9 | enabled | `enabled` (v1.19.x+) |
| 10 | drag_dir | `hotkey.drag_direction` (v1.19.x+) |

### MenuItem タプル → MenuItem オブジェクト

| PME1 Index | PME1 Field | PME2 Field |
|------------|-----------|------------|
| 0 | name | `name` |
| 1 | mode | `action.type` (小文字に変換) |
| 2 | icon | `icon` + フラグ分離 |
| 3 | text | `action.value` |
| 4 | flags | `enabled` (ビット0) |

### アイコンフラグの分離

```
PME1: "!@MESH_CUBE"
↓
PME2: {
  "icon": "MESH_CUBE",
  "icon_only": true,   // !
  "hidden": true       // @
}
```

### Action オブジェクトへの変換

```
PME1: mode="COMMAND", text="bpy.ops.mesh.primitive_cube_add()"
↓
PME2: {
  "action": {
    "type": "command",
    "value": "bpy.ops.mesh.primitive_cube_add()",
    "undo": true,
    "context": null
  }
}
```

mode から type への変換表：
| PME1 mode | PME2 action.type |
|-----------|-----------------|
| COMMAND | command |
| CUSTOM | custom |
| PROP | prop |
| MENU | menu |
| HOTKEY | hotkey |
| OPERATOR | operator |
| EMPTY | empty |

### data 文字列のパース

```
PME1: "pm?pm_radius=100&pm_flick=False"
↓
PME2: {
  "radius": 100,
  "flick": false
}
```

- プレフィックス（`pm_`, `pd_`, `pg_` 等）を除去
- 型を復元（`"True"` → `true`, `"100"` → `100`）

---

## 変換コード例（Python）

```python
# PME1 mode → PME2 action.type
MODE_MAP = {
    "COMMAND": "command",
    "CUSTOM": "custom",
    "PROP": "prop",
    "MENU": "menu",
    "HOTKEY": "hotkey",
    "OPERATOR": "operator",
    "EMPTY": "empty",
}

def convert_pme1_menu(pme1_tuple: list) -> dict:
    """PME1 タプル → PME2 オブジェクト"""
    name, km_name, hotkey_str, items, mode, data, open_mode, poll_cmd, tag, *rest = pme1_tuple

    enabled = rest[0] if len(rest) > 0 else True
    drag_dir = rest[1] if len(rest) > 1 else None

    return {
        "name": name,
        "mode": mode,
        "enabled": enabled,
        "hotkey": parse_hotkey(hotkey_str, km_name, open_mode, drag_dir),
        "settings": parse_data_string(data),
        "poll": poll_cmd if poll_cmd else None,
        "tags": tag.split(",") if tag else [],
        "items": [convert_pme1_item(item) for item in items],
    }

def convert_pme1_item(pme1_tuple: list) -> dict:
    """PME1 アイテムタプル → PME2 オブジェクト"""
    if len(pme1_tuple) == 1:
        # EMPTY モード
        return {
            "name": pme1_tuple[0],
            "action": {"type": "empty", "value": ""},
            "enabled": True,
        }

    name, mode, icon_str, text, flags = pme1_tuple
    icon, icon_only, hidden = parse_icon_flags(icon_str)
    action_type = MODE_MAP.get(mode, "command")

    return {
        "name": name,
        "action": build_action(action_type, text),
        "icon": icon,
        "icon_only": icon_only,
        "hidden": hidden,
        "enabled": not (flags & 1),
    }

def build_action(action_type: str, value: str) -> dict:
    """アクションタイプに応じたデフォルトメタデータを付与"""
    action = {"type": action_type, "value": value}

    # タイプ別のデフォルトメタデータ
    if action_type == "command":
        action["undo"] = True
        action["context"] = None
    elif action_type == "custom":
        action["undo"] = False
        action["use_try"] = True
    elif action_type == "prop":
        action["expand"] = False
        action["slider"] = False
        action["toggle"] = False
    elif action_type == "menu":
        action["mode"] = "inherit"
    elif action_type == "operator":
        action["properties"] = {}

    return action
```

---

## バージョン互換性

| バージョン | 形式 | 検出方法 |
|-----------|------|---------|
| < 1.13.6 | リスト（タプルの配列） | `isinstance(data, list)` |
| 1.13.6 - 1.18.x | dict + version | `"menus" in data` |
| 1.19.x (PME-F) | dict + version + 11項目 | `len(menu) >= 11` |
| 2.0.0+ (PME2) | dict + $schema | `data.get("$schema") == "PME2"` |

---

## 今後の拡張

1. **JSONSchema 定義**: 正式な JSONSchema ファイルを作成しバリデーション可能に
2. **差分エクスポート**: 変更されたメニューのみをエクスポート
3. **参照解決**: サブメニュー参照の整合性チェック
4. **圧縮形式**: 大量のメニュー用にバイナリ形式を検討
