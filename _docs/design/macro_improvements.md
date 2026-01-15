# Macro Improvements Milestone

> **Issue**: #102
> **Branch**: `feature/macro-improvements`
> **Status**: In Progress

## Overview

PME で動的生成されるマクロオペレーターの改善計画。

### 現状の問題

1. **ツールチップ問題**: マクロを Blender UI ウィジェットに登録すると「undocumented operator」と表示される
2. **引数問題**: `bpy.ops.pme.macro_xxx(...)` を呼ぶにはすべてのサブオペレーター引数を手動指定する必要がある
3. **統合問題**: PME の uid/name からマクロオペレーターへの直接的なマッピングがない

### 技術的背景

```python
# 現在の add_macro() - bl_description なし
defs = {
    "bl_label": pm.name,
    "bl_idname": tp_bl_idname,
    "bl_options": {'REGISTER', 'UNDO'},
}
tp = type(tp_name, (bpy.types.Macro,), defs)
```

- `bpy.types.Macro` はサブオペレーターの連鎖実行機構
- `tp.define(sub_tp)` でサブオペレーターを登録
- 呼び出し時に各サブオペレーターのプロパティを `props` 辞書で渡す
- `execute_macro(pm)` は内部で `_fill_props()` を使い引数を自動構築済み

---

## Phase A: description 追加（独立・低リスク）

### A-1: PMItem.description フィールド追加

**ファイル**: `pme_types.py`

```python
class PMItem(PropertyGroup):
    # 既存フィールド...
    description: StringProperty(
        name="Description",
        description="Tooltip description for this menu item",
        default="",
    )
```

**状態**: [x] 完了

### A-2: add_macro() で bl_description 設定

**ファイル**: `infra/macro.py`

```python
def add_macro(pm):
    # ...
    description = getattr(pm, 'description', "") or ""
    if not description:
        description = f"Execute {pm.name} macro"

    defs = {
        "bl_label": pm.name,
        "bl_idname": tp_bl_idname,
        "bl_description": description,
        "bl_options": {'REGISTER', 'UNDO'},
    }
```

**状態**: [x] 完了

### A-3: Blender UI で tooltip 表示確認

**テスト手順**:
1. マクロメニューを作成
2. description を設定
3. Blender のメニューやツールバーにマクロを登録
4. ホバーして tooltip を確認

**状態**: [x] 完了

**テスト結果**:
- デフォルトの `"Execute {name} macro"` が機能
- アイテム追加でマクロ再ビルド → description 反映
- F3 検索でカスタム tooltip 表示を確認

### A-4: UI フィールド追加（追加タスク）

**ファイル**: `editors/macro.py`, `pme_types.py`

- `draw_extra_settings()` に "Tooltip" テキストフィールド追加
- `PMItem.description` に `update` コールバック追加
- description 変更時に自動で `MAU.update_macro(pm)` を呼び出し

**状態**: [x] 完了

---

## Phase B: 引数なし呼び出し（コア設計）

### B-1: ラッパーオペレーター設計・実装

**ファイル**: `operators/macro.py` (新規作成)

```python
class PME_OT_invoke_macro(Operator):
    """Execute a PME macro by name"""
    bl_idname = "pme.invoke_macro"
    bl_label = "Invoke Macro"
    bl_description = "Execute a PME macro"

    pm_name: StringProperty(...)

    @classmethod
    def description(cls, context, properties):
        # 動的 description - properties.pm_name から pm.description を取得
        pr = get_prefs()
        pm = pr.pie_menus.get(properties.pm_name)
        if pm and pm.description:
            return pm.description
        return f"Execute {properties.pm_name} macro"

    def execute(self, context):
        # execute_macro(pm) を呼び出し → 引数自動構築
        ...
```

**状態**: [x] 完了

### B-2: テスト

**テスト手順**:
```python
# Blender Python コンソールで

# 1. マクロメニューを作成し、description を設定
import bpy
pr = bpy.context.preferences.addons['pie_menu_editor'].preferences
pm = pr.pie_menus["My Macro"]  # マクロ名
pm.description = "My custom macro tooltip"

# 2. ラッパーオペレーターを layout.operator() で呼ぶ
# 例: カスタムパネルで
def draw(self, context):
    op = self.layout.operator("pme.invoke_macro", text="Run Macro")
    op.pm_name = "My Macro"
    # ↑ ホバーすると "My custom macro tooltip" が表示されるはず

# 3. F3 検索から実行
# F3 → "pme.invoke_macro" → pm_name を入力 → 実行
```

**状態**: [x] 完了 ✅

**テスト結果**:
- `pme.invoke_macro` が正常に動作
- 動的 description が tooltip として表示される
- `execute_macro()` 経由で引数が自動構築される

---

## Phase C: UI 統合（Phase B 完了後）

### C-1: uid/name → bl_idname マッピング

**目的**: PME メニューの uid または name から対応するオペレーターの bl_idname を取得

```python
def get_macro_bl_idname(pm_name: str) -> str | None:
    """Get the bl_idname of a macro operator by menu name."""
    from .infra.macro import _macros
    tp = _macros.get(pm_name)
    return tp.bl_idname if tp else None
```

**状態**: [ ] 未着手

### C-2: スロットエディタでマクロ選択時の挙動

**検討事項**:
- マクロを選択したとき、どのオペレーターを配置するか
  - 選択肢 A: 動的生成された `pme.macro_xxx`
  - 選択肢 B: ラッパー `pme.invoke_macro(pm_name=...)`
- ユーザーにとってどちらが使いやすいか

**状態**: [ ] 未着手

### C-3: UI ウィジェットに直接オペレーター配置

**状態**: [ ] 未着手

---

## 関連ファイル

| ファイル | 役割 |
|----------|------|
| `pme_types.py` | PMItem 定義（description 追加先） |
| `infra/macro.py` | マクロ動的生成 |
| `operators/` | 新規ラッパーオペレーター配置候補 |

## 関連 Issue

- #100: GPU-rendered tooltips for Pie Menu（PME 内部ツールチップ）
- #102: Macro operator improvements（この計画）

---

## 進捗ログ

| 日付 | 内容 |
|------|------|
| 2026-01-15 | **Phase B 完了** - `PME_OT_invoke_macro` 実装、動的 description テスト成功！複数ボタン同時表示でも個別の tooltip が正しく表示 |
| 2026-01-14 | **Phase A 完了** - description フィールド追加、bl_description 設定、tooltip 表示確認 |
| 2026-01-13 | マイルストーン作成、Phase A 着手開始 |
