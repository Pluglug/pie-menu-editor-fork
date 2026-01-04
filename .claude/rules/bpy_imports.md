# bpy Import Style Guide

## 目的

1. **bpy 依存の明示化**: `bpy.types.*` / `bpy.props.*` 参照を明示的なシンボルに置換
2. **エイリアス削減**: `import X as Y` パターンを明示的な cherry-pick import に置き換え
3. **pyright 対応**: 型エラーを抑制

---

## 推奨パターン

### 基本構成

```python
# pyright: reportInvalidTypeForm=false
import bpy
from bpy import types as bpy_types  # 動的型参照用（必要な場合のみ）
from bpy.props import BoolProperty, IntProperty, StringProperty, EnumProperty
from bpy.types import Operator, Panel, Menu, Header, PropertyGroup
```

### 使い分け

| 用途 | 推奨パターン | 例 |
|------|-------------|-----|
| クラス継承 | `from bpy.types import Operator` | `class MyOp(Operator):` |
| プロパティ定義 | `from bpy.props import IntProperty` | `prop: IntProperty()` |
| 動的型アクセス | `bpy_types` エイリアス | `getattr(bpy_types, name)` |
| モジュールアクセス | `bpy.props`, `bpy.types` | `bpy.props._PropertyDeferred` |

---

## 禁止パターンと修正方法

### ❌ エイリアスからの import

```python
# NG: Python ではエイリアスからの import は不可
from bpy import types as bpy_types
from bpy_types import Operator  # ← ModuleNotFoundError

from bpy import props
from props import IntProperty  # ← ModuleNotFoundError

# ✅ 正しい書き方
from bpy.types import Operator
from bpy.props import IntProperty
```

**理由**: Python のエイリアスは「変数」であり「パッケージ」ではない。

### ❌ 自己代入

```python
# NG: ローカル変数として扱われ UnboundLocalError になる
def register():
    bpy_types = bpy_types  # ← UnboundLocalError
    for name in dir(bpy_types):
        ...

# ✅ この行を削除、または global 宣言を追加
def register():
    # bpy_types はモジュールレベルで定義済みなのでそのまま使える
    for name in dir(bpy_types):
        ...
```

### ❌ 未定義シンボルの使用

```python
# NG: props が import されていない
def prop_by_type(prop_type):
    return getattr(props, name)  # ← NameError

# ✅ bpy.props を直接使用
def prop_by_type(prop_type):
    return getattr(bpy.props, name)
```

---

## PME Schema と bpy.props の区別

PME には2つの「props」系システムが存在する:

| シンボル | 正体 | 用途 |
|---------|------|------|
| `bpy.props` | Blender モジュール | PropertyGroup 定義 |
| `pme.schema` | PME の SchemaRegistry | メニュースキーマ定義 |

### 現在（後方互換）

```python
# PME スキーマ登録 (core/props.py)
from ..core.props import props
props.IntProperty("pm", "pm_radius", -1)  # ← PME 専用

# Blender プロパティ作成 (bpy.props)
import bpy
bpy.props.IntProperty(name="Radius")  # ← Blender 標準
```

### 将来（Phase 8-C 以降）

```python
# PME スキーマ登録 (core/schema.py)
from ..core.schema import schema
schema.IntProperty("pm", "pm_radius", -1)  # ← 明確に区別

# Blender プロパティ作成 (bpy.props)
from bpy.props import IntProperty
prop: IntProperty(name="Radius")
```

**詳細**: `@_docs/design/schema-rename-plan.md`

---

## pyright 対応

Blender の PropertyGroup やオペレータープロパティは pyright で型エラーになる:

```python
# pyright: reportInvalidTypeForm=false
```

をファイル先頭に追加する。

---

## Codex 作業時のチェックリスト

Codex が bpy import の正規化を行う際:

- [ ] `from bpy_types import ...` → `from bpy.types import ...`
- [ ] `from props import ...` → `from bpy.props import ...`
- [ ] `bpy_types = bpy_types` のような自己代入を削除
- [ ] `props` が `bpy.props` を期待している箇所は `bpy.props` に修正
- [ ] `bpy_types` エイリアスは動的アクセス用に残してOK
- [ ] 各ファイルに `# pyright: reportInvalidTypeForm=false` を追加

---

## 参照

- Blender Python API: [bpy.types](https://docs.blender.org/api/current/bpy.types.html)
- Blender Python API: [bpy.props](https://docs.blender.org/api/current/bpy.props.html)
