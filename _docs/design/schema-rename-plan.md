---
title: Schema Rename Plan - pme.props → pme.schema
phase: Phase 8-C
status: completed
created: 2026-01-04
completed: 2026-01-04
---

# Schema Rename Plan: `pme.props` → `pme.schema`

## 背景

現在 `pme.props` / `from core.props import props` という名前を使用しているが、
`bpy.props` と混同しやすいため、より明確な名前に変更する。

### 混乱の例

```python
# どちらの props？
props.IntProperty(...)  # PME? Blender?

# 現在のスタイルガイドでは区別が必要
from ..core.props import props as pme_props  # PME
import bpy.props  # Blender
```

---

## 決定事項

| 項目 | 旧 | 新 |
|------|-----|-----|
| モジュール | `core/props.py` | `core/schema.py` |
| クラス名 | `PMEProps` | `SchemaRegistry` |
| インスタンス | `props` | `schema` |
| pme.py エクスポート | `pme.props` | `pme.schema` |

---

## 理由

### 1. ideal-architecture との整合性

```python
# 現在
pme.props.IntProperty("pm", "pm_radius", -1)

# 将来 (ideal-architecture.md)
@dataclass
class PieMenuSchema(MenuSchemaBase):
    radius: int = -1
```

`schema` という名前は将来の `MenuSchemaBase` への移行と自然に繋がる。

### 2. JSON v2 との関係

```json
{
  "mode": "PMENU",
  "settings": {
    "radius": 100,
    "flick": true
  }
}
```

`schema` はこの `settings` の**定義**を管理するシステム。

### 3. 明確な責務

| 名前 | 責務 |
|------|------|
| `bpy.props` | Blender PropertyGroup の定義 |
| `pme.schema` | PME メニュースキーマの定義 |

---

## 実装計画

### Step 1: クラス・変数リネーム

```python
# core/props.py → core/schema.py

class SchemaRegistry:  # 旧 PMEProps
    """
    PME Menu Schema Definition Registry.

    Registers property definitions for each menu type.
    These definitions control how data is parsed from
    the legacy 'data' string and what defaults are used.
    """

    def IntProperty(self, type_key: str, name: str, default: int = 0):
        ...

    def BoolProperty(self, type_key: str, name: str, default: bool = False):
        ...

    def StringProperty(self, type_key: str, name: str, default: str = ""):
        ...

    def EnumProperty(self, type_key: str, name: str, default: str, items: list):
        ...

# シングルトンインスタンス
schema = SchemaRegistry()

# 後方互換エイリアス (deprecated)
props = schema
PMEProps = SchemaRegistry
```

### Step 2: pme.py エクスポート更新

```python
# pme.py
from .core.schema import schema, SchemaRegistry

# 後方互換
from .core.schema import props  # deprecated
```

### Step 3: 利用箇所の更新

```python
# editors/pie_menu.py
# Before
from ..core.props import props
props.IntProperty("pm", "pm_radius", -1)

# After
from ..core.props import schema
schema.IntProperty("pm", "pm_radius", -1)
```

### Step 4: ドキュメント更新

- `bpy_imports.md` の PME props セクション更新
- `pme_api_*.md` の API リファレンス更新

---

## 影響範囲

### 直接参照 (要更新)

```
editors/pie_menu.py      - props.IntProperty(...)
editors/modal.py         - props.BoolProperty(...)
editors/menu.py          - props.BoolProperty(...)
editors/panel_group.py   - props.BoolProperty/StringProperty(...)
editors/popup.py         - props.EnumProperty/BoolProperty/IntProperty(...)
editors/sticky_key.py    - props.BoolProperty(...)
editors/stack_key.py     - props.BoolProperty(...)
editors/property.py      - pme_props.IntProperty/BoolProperty(...)
```

### 間接参照 (後方互換で対応)

- `from core.props import props` → 引き続き動作
- `pme.props.IntProperty(...)` → 引き続き動作

---

## 後方互換性

### 内部コード

- `props` エイリアスを残すため、既存コードは引き続き動作
- 新規コードは `schema` を使用

### 外部ユーザー

PME のスクリプト内で `pme.props` を使っているユーザーは稀と想定。
万一いる場合も `pme.props` エイリアスで動作継続。

---

## 完了ステータス

| フェーズ | 内容 | 状態 |
|---------|------|------|
| 8-C-1 | `core/props.py` → `core/schema.py` リネーム | ✅ 完了 |
| 8-C-2 | クラス名・変数名更新 | ✅ 完了 |
| 8-C-3 | editors/ の import 更新 | ✅ 完了 |
| 8-C-4 | pme.py エクスポート更新 | ✅ 完了 |
| 8-C-5 | ドキュメント更新 | ✅ 完了 |

**完了日**: 2026-01-04

---

## 参照

- `@_docs/design/core-layer/ideal-architecture.md` — 理想アーキテクチャ
- `@pme_mini/.claude/design/json_schema_v2.md` — JSON v2 スキーマ
- `@.claude/rules/bpy_imports.md` — bpy import スタイルガイド
