# Dynamic Description System Design

> **Status**: Planning → Implementation Ready
> **Related Issue**: #102
> **Branch**: `feature/macro-improvements`
> **Created**: 2026-01-15
> **Updated**: 2026-01-18

---

## 1. Background

### 発見

Blender は `description(cls, context, properties)` クラスメソッドをサポートしており、
オペレーターのプロパティに基づいて動的に tooltip を生成できる。

```python
@classmethod
def description(cls, context, properties):
    # properties.xxx でオペレーターのプロパティにアクセス
    # context で現在の Blender 状態にアクセス
    return "Dynamic tooltip"
```

### 実験結果

- `PME_OT_invoke_macro` に実装 → 成功
- `WM_OT_pme_user_pie_menu_call` に実装 → 成功
- 複数ボタン同時表示でもそれぞれ正しい tooltip が表示される

---

## 2. 調査結果: PME ラッパーオペレーター一覧

### 2.1 メインラッパーオペレーター

| オペレーター | bl_idname | プロパティ | description() 効果 |
|-------------|-----------|-----------|-------------------|
| **`WM_OT_pme_user_pie_menu_call`** | `wm.pme_user_pie_menu_call` | `pie_menu_name`, `invoke_mode`, `keymap`, `slot` | ✅ **最優先** - 全メニュー呼び出し |
| **`WM_OT_pme_user_command_exec`** | `wm.pme_user_command_exec` | `menu`, `slot`, `cmd` | ✅ **高優先** - COMMAND フォールバック |
| `WM_OT_pme_user_dialog_call` | `wm.pme_user_dialog_call` | `pie_menu_name` | △ INTERNAL なので効果限定 |
| `WM_OT_pme_hotkey_call` | `wm.pme_hotkey_call` | `hotkey` | △ ホットキー文字列のみ |

### 2.2 Modal/Sticky オペレーター

| オペレーター | bl_idname | プロパティ | description() 効果 |
|-------------|-----------|-----------|-------------------|
| `PME_OT_sticky_key_base` | `pme.sticky_key` | `pm_name` | 🔄 **保留** |
| `PME_OT_modal_base` | `pme.modal` | `pm_name` | 🔄 **保留** |
| `PME_OT_modal_grab` | `pme.modal_grab` | `pm_name` | 🔄 **保留** |

> **保留理由**: 呼び出し時に `WM_OT_pme_user_pie_menu_call` が使われる場合、効果が限定的。

### 2.3 汎用実行オペレーター

| オペレーター | bl_idname | プロパティ | description() 効果 |
|-------------|-----------|-----------|-------------------|
| `PME_OT_exec` | `pme.exec` | `cmd` | ✗ 識別情報なし |

### 2.4 動的生成オペレーター

| オペレーター | 生成場所 | 対応方法 |
|-------------|---------|---------|
| 動的 Macro (`pme.macro_*`) | `infra/macro.py:add_macro()` | `bl_description` を設定 |
| 動的 Modal (`pme.modal*`) | `infra/macro.py:_gen_modal_op()` | 同上 |

---

## 3. COMMAND モードの動作フロー

### 3.1 分岐ロジック

`_draw_item()` (`operators/__init__.py:1183-1216`) で COMMAND モードは以下のように処理される:

```
pmi.text を解析
    ↓
operator_utils.find_operator(pmi.text)
    ↓
    返り値: (op_bl_idname, args, pos_args)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Case 1: 単一オペレーター呼び出し（pos_args なし）            │
│ 条件: op_bl_idname が見つかり、pos_args が空               │
│                                                            │
│ 例:                                                        │
│   bpy.ops.mesh.primitive_cube_add()                        │
│   bpy.ops.mesh.primitive_cube_add(size=2)                  │
│   bpy.ops.view3d.snap_selected_to_cursor(use_offset=True)  │
│                                                            │
│ 処理:                                                       │
│   lh.operator(op_bl_idname, text, icon)  # 直接呼び出し    │
│   → Blender 標準の bl_description が tooltip に表示        │
│                                                            │
├─────────────────────────────────────────────────────────────┤
│ Case 2: フォールバック                                      │
│ 条件: op_bl_idname が見つからない OR pos_args がある       │
│                                                            │
│ 例:                                                        │
│   bpy.ops.mesh.primitive_cube_add('INVOKE_DEFAULT')        │
│   print("hello"); bpy.ops.mesh.primitive_cube_add()        │
│   C.object.location = (0, 0, 0)                            │
│   for obj in C.selected_objects: obj.hide_set(True)        │
│                                                            │
│ 処理:                                                       │
│   lh.operator(                                             │
│       WM_OT_pme_user_command_exec.bl_idname,               │
│       text, icon,                                          │
│       cmd=pmi.text,                                        │
│       menu=pm.name,                                        │
│       slot=pmi.name,                                       │
│   )                                                        │
│   → 現在は "Execute python code" が tooltip に表示         │
│   → ★ここで pmi.description を使えば効果的！              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 設計方針

**ユーザー視点**:
- COMMAND モードのときだけ description を設定できる（シンプルな理解）
- pmi.description を設定すれば tooltip に反映される

**内部動作**:
- Blender オペレーターが直接呼べる場合 → Blender 標準の description を使用（既存フロー維持）
- フォールバック（`WM_OT_pme_user_command_exec`）の場合 → pmi.description を使用

---

## 4. 実装計画

### Phase 1: PM レベル（最小実装・最大効果）

**対象**: `WM_OT_pme_user_pie_menu_call`

**実装内容**:
```python
@classmethod
def description(cls, context, properties):
    pr = get_prefs()
    pm = pr.pie_menus.get(properties.pie_menu_name)
    if not pm:
        return "Call PME menu"
    if pm.description:
        return pm.description
    return f"Call {pm.name}"
```

**効果**:
- 全 PM タイプ（Pie, Regular, Macro, Modal, Sticky 等）に description 機能
- PMItem.description フィールドを使用

**変更ファイル**:
- `operators/__init__.py`: `WM_OT_pme_user_pie_menu_call` に description() 追加
- `pme_types.py`: `PMItem.description` フィールド追加（実験で追加済み）

### Phase 2: PMI レベル（COMMAND フォールバック）

**対象**: `WM_OT_pme_user_command_exec`

**実装内容**:
```python
@classmethod
def description(cls, context, properties):
    pr = get_prefs()
    pm = pr.pie_menus.get(properties.menu)
    if not pm:
        return "Execute python code"

    # slot から pmi を特定
    pmi = pm.pmis.get(properties.slot)
    if pmi and pmi.description:
        return pmi.description

    return "Execute python code"
```

**効果**:
- COMMAND モードで `WM_OT_pme_user_command_exec` 経由の場合のみ
- pmi.description を tooltip に反映

**変更ファイル**:
- `operators/__init__.py`: `WM_OT_pme_user_command_exec` に description() 追加
- `pme_types.py`: `PMIItem.description` フィールド追加
- エディタ UI: description 入力フィールド追加（COMMAND モードのみ表示）

### Phase 3: 動的 Macro（オプション）

**対象**: `infra/macro.py:add_macro()`

**実装内容**:
```python
def add_macro(pm):
    # ...
    description = getattr(pm, 'description', "") or f"Execute {pm.name} macro"

    defs = {
        "bl_label": pm.name,
        "bl_idname": tp_bl_idname,
        "bl_description": description,  # 追加
        "bl_options": {'REGISTER', 'UNDO'},
    }
    # ...
```

**効果**:
- 動的生成された Macro オペレーターに bl_description を設定
- `WM_OT_pme_user_pie_menu_call` 経由でなく直接呼ばれる場合に有効

---

## 5. 優先順位

| 優先度 | 対象 | 効果 | 実装難易度 |
|-------|------|------|-----------|
| 🥇 **1位** | `WM_OT_pme_user_pie_menu_call` | 全 PM タイプをカバー | 低 |
| 🥈 **2位** | `WM_OT_pme_user_command_exec` | COMMAND フォールバック | 中 |
| 🥉 **3位** | 動的 Macro (`add_macro()`) | 直接呼び出しケース | 低 |
| ⏸️ **保留** | `PME_OT_sticky_key_base`, `PME_OT_modal_base` | 効果限定的 | 中 |

---

## 6. JSON Schema v2 との統合

### PM レベル

既に設計済み（`json_schema_v2.md`）:
```json
{
  "uid": "pm_9f7c2k3h",
  "name": "My Pie Menu",
  "description": "モデリング作業用のメインメニュー",
  "description_expr": null,
  // ...
}
```

### PMI レベル

```json
{
  "name": "Add Cube",
  "action": { "type": "command", "value": "..." },
  "description": "シーンに立方体を追加",
  "description_expr": null,
  // ...
}
```

---

## 7. 実験コードの記録

### 実験 1: PME_OT_invoke_macro（stash 内）

```python
# operators/macro.py (新規作成)
class PME_OT_invoke_macro(Operator):
    bl_idname = "pme.invoke_macro"
    pm_name: StringProperty()

    @classmethod
    def description(cls, context, properties):
        pr = get_prefs()
        pm = pr.pie_menus.get(properties.pm_name)
        if pm and pm.description:
            return pm.description
        return f"Execute {properties.pm_name} macro"

    def execute(self, context):
        execute_macro(pm)
        return {'FINISHED'}
```

### 実験 2: WM_OT_pme_user_pie_menu_call（stash 内）

```python
# operators/__init__.py に追加
@classmethod
def description(cls, context, properties):
    pr = get_prefs()
    pm = pr.pie_menus.get(properties.pie_menu_name)
    if not pm:
        return "Call PME menu"
    if pm.description:
        return pm.description
    return f"Call {pm.name}"
```

両方とも動作確認済み。

---

## 8. 参考資料

### Blender API

- [Operator.description()](https://docs.blender.org/api/current/bpy.types.Operator.html)
- [Dynamic operator description - Interplanety](https://b3d.interplanety.org/en/dynamic-operator-description/)

### PME 関連ファイル

- `operators/__init__.py:1137` - `WM_OT_pme_user_pie_menu_call` 定義
- `operators/__init__.py:190` - `WM_OT_pme_user_command_exec` 定義
- `operators/__init__.py:1183-1216` - COMMAND モード `_draw_item()` 処理
- `operator_utils.py:371` - `find_operator()` 定義
- `infra/macro.py:99` - `add_macro()` 定義
- `pme_types.py` - PMItem, PMIItem 定義

---

*Last Updated: 2026-01-18*
