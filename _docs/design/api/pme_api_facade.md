# PME API Facade Design

> Phase 8-D: pme API facade & context split

## 目的

1. **`api/` パッケージ**を公開 API ファサードとして導入
2. **`sys.modules["pme"]`** で安定した `import pme` を提供（Extensions 対応）
3. **実行コンテキスト**と**公開 API**の分離
4. **`__all__`** で公開 API サーフェスを制御

---

## 現状分析

### `pme.py` の現在の責務

1. **実行コンテキスト管理**: `PMEContext`, `UserData`, `context`
2. **公開 API ファサード**: `execute()`, `evaluate()`, `find_pm()`, etc.
3. **スキーマ再エクスポート**: `schema`, `SchemaRegistry`, etc.
4. **名前空間定義再エクスポート**: `Stability`, `NAMESPACE_*`, etc.

### `add_global()` で注入される変数（50+個）

| カテゴリ | 変数 | 定義場所 |
|---------|------|----------|
| **Core Blender** | `C`, `D`, `O`, `P`, `T`, `bpy`, `context` | `bl_utils.py`, `__init__.py` |
| **Properties** | `BoolProperty`, `IntProperty`, etc. | `__init__.py` |
| **Standard Library** | `sys`, `os`, `re`, `traceback` | 各所 |
| **UI Helpers** | `lh`, `operator`, `panel`, `overlay` | `ui/layout.py`, `ui/panels.py`, etc. |
| **Menu Helpers** | `open_menu`, `draw_menu`, `header_menu`, `execute_script`, `toggle_menu` | `ui/utils.py` |
| **Screen Helpers** | `focus_area`, `move_header`, `toggle_sidebar`, `override_context`, `exec_with_override` | `ui/screen.py` |
| **Execution Helpers** | `SK`, `call_operator`, `find_by`, `keep_pie_open` | `keymap_helper.py`, etc. |
| **Paint Helpers** | `paint_settings`, `unified_paint_panel`, `ups`, `brush` | `bl_utils.py`, `scripts/autorun/` |
| **PME Internal** | `prefs`, `_prefs`, `get_prefs`, `temp_prefs`, `pme`, `PMEData` | `preferences.py` |
| **User Data** | `U` | `pme.py` |
| **Event** | `E`, `delta`, `drag_x`, `drag_y` | `pme.py`, `operators/__init__.py` |
| **UI Context** | `L`, `text`, `icon`, `icon_value` | `pme.py` |
| **Misc** | `message_box`, `input_box`, `close_popups`, `tag_redraw`, `custom_icon` | 各所 |

### `pme` モジュールの使用パターン

**内部使用（23+ モジュール）:**
```python
from . import pme
# または
from .. import pme
```

**外部使用（scripts/*, docs）:**
```python
from pie_menu_editor import pme
```

---

## シンボル分類

### 1. 公開 API（`pme.*` として公開）

| シンボル | 種別 | 説明 | 安定性 |
|---------|------|------|--------|
| `execute()` | 関数 | コード実行 | Experimental |
| `evaluate()` | 関数 | 式評価 | Experimental |
| `ExecuteResult` | クラス | 実行結果 | Experimental |
| `find_pm()` | 関数 | メニュー検索 | Experimental |
| `list_pms()` | 関数 | メニュー一覧 | Experimental |
| `invoke_pm()` | 関数 | メニュー呼び出し | Experimental |
| `PMHandle` | クラス | メニューハンドル | Experimental |
| `schema` | インスタンス | スキーマレジストリ | Experimental |
| `SchemaRegistry` | クラス | スキーマ定義 | Experimental |
| `SchemaProp` | クラス | プロパティ定義 | Experimental |
| `ParsedData` | クラス | パース結果 | Experimental |
| `Stability` | クラス | 安定性レベル | Experimental |
| `get_stability()` | 関数 | 安定性取得 | Experimental |
| `is_public()` | 関数 | 公開判定 | Experimental |

**Deprecated エイリアス（後方互換）:**
- `PMEProp` → `SchemaProp`
- `PMEProps` → `SchemaRegistry`
- `props` → `schema`

### 2. スクリプト名前空間用（`add_global` で注入、公開しない）

これらは PME スクリプト内でのみ使用され、`pme.*` としては公開しない：

- `C`, `D`, `O`, `P`, `T`, `bpy`, `context`, `bl_context`
- `lh`, `operator`, `panel`, `overlay`
- `open_menu`, `draw_menu`, `header_menu`, etc.
- `focus_area`, `move_header`, `toggle_sidebar`, etc.
- `SK`, `call_operator`, `find_by`, `keep_pie_open`
- `prefs`, `get_prefs`, `temp_prefs`, `PMEData`
- `message_box`, `input_box`, `close_popups`, `tag_redraw`
- etc.

### 3. 純粋な内部実装（外部から見えない）

- `PMEContext`, `UserData` - 実行コンテキスト
- `context` シングルトン - 内部状態管理
- `NAMESPACE_*` 定数 - 名前空間定義
- `PUBLIC_NAMES`, `NAMESPACE_INTERNAL` - 検証用
- `validate_public_namespace()`, `get_namespace_report()` - デバッグ

---

## 提案アーキテクチャ

### ディレクトリ構造

```
pie_menu_editor/
├── __init__.py              # Blender エントリ
├── addon.py                 # ライフサイクル・ローダー
├── pme.py                   # レガシーシム（後方互換）
├── api/                     # 公開 API ファサード（薄いラッパー）
│   ├── __init__.py          # 公開 API エントリ
│   └── _types.py            # ExecuteResult, PMHandle（型定義）
├── core/                    # Blender 非依存ロジック
├── infra/                   # Blender API 橋渡し
│   ├── runtime_context.py   # PMEContext, UserData（実行コンテキスト）
│   └── ...
├── ui/                      # UI 描画ヘルパー
├── editors/                 # エディタロジック
├── operators/               # オペレーター
└── preferences.py           # 設定
```

設計原則:
- **api/** は薄いファサード。ロジックは infra/ や core/ に置く
- **infra/runtime_context.py** が実行コンテキストの正体
- **api/__init__.py** は infra.runtime_context をラップ

### `api/__init__.py` の構造

```python
"""PME Public API Facade.

外部ツールは `import pme` でこのモジュールを使用する。

Example:
    >>> import pme
    >>> pme.execute("print(C.mode)")
    >>> pme.find_pm("My Menu")
"""
LAYER = "api"

# 公開 API のみをエクスポート
__all__ = [
    # Execution
    "execute",
    "evaluate",
    "ExecuteResult",
    # Menu API
    "PMHandle",
    "find_pm",
    "list_pms",
    "invoke_pm",
    # Schema
    "schema",
    "SchemaRegistry",
    "SchemaProp",
    "ParsedData",
    # Deprecated (backward compat)
    "props",
    "PMEProp",
    "PMEProps",
    # Stability
    "Stability",
    "get_stability",
    "is_public",
]

# 内部モジュールからインポート
from ._context import context as _context  # 内部用
from ._types import ExecuteResult, PMHandle
from ..core.schema import (
    schema, SchemaRegistry, SchemaProp, ParsedData,
    props, PMEProp, PMEProps,  # deprecated
)
from ..core.namespace import Stability, get_stability, is_public

# 公開関数
def execute(code: str, *, extra_globals: dict | None = None) -> ExecuteResult:
    ...

def evaluate(expr: str, *, extra_globals: dict | None = None):
    ...

def find_pm(name: str) -> PMHandle | None:
    ...

def list_pms(mode: str | None = None) -> list[PMHandle]:
    ...

def invoke_pm(pm_or_name: PMHandle | str) -> bool:
    ...
```

### `sys.modules["pme"]` エイリアス

```python
# addon.py または __init__.py の register()

import sys

_pme_alias_module = None

def _install_pme_alias():
    global _pme_alias_module
    from . import api
    _pme_alias_module = api
    sys.modules["pme"] = api
    return api

def _uninstall_pme_alias():
    global _pme_alias_module
    if _pme_alias_module is not None:
        if sys.modules.get("pme") is _pme_alias_module:
            del sys.modules["pme"]
        _pme_alias_module = None

def register():
    _install_pme_alias()
    # ...

def unregister():
    _uninstall_pme_alias()
    # ...
```

---

## 移行計画

### Step 1: `api/` パッケージ導入

1. `api/__init__.py` 作成
2. `api/_context.py` に `PMEContext`, `UserData` を移動
3. `api/_types.py` に `ExecuteResult`, `PMHandle` を移動
4. 公開関数を `api/__init__.py` に実装

### Step 2: `sys.modules["pme"]` エイリアス

1. `addon.py` に `_install_pme_alias()` / `_uninstall_pme_alias()` 追加
2. `register()` / `unregister()` でエイリアスを管理
3. Reload Scripts での動作確認

### Step 3: `pme.py` をレガシーシムに

1. `pme.py` を `api` の薄いラッパーに変更
2. 後方互換のため `from .api import *` パターン
3. 非推奨コメントを追加

### Step 4: global-only ユーティリティの整理（段階的）

1. 各モジュールの `register()` で `add_global()` を呼び出す現在のパターンは維持
2. 将来的に一部を `pme.helpers.*` などに移動検討
3. 今回は構造変更のみで、動作変更は行わない

---

## 後方互換性

### 維持するパス

| パス | 動作 |
|------|------|
| `import pme` | `api` モジュールを返す（新規） |
| `from pie_menu_editor import pme` | 従来通り動作 |
| `pme.context` | 非推奨だが動作（警告なし） |
| `pme.context.add_global()` | 従来通り動作 |
| `pme.props`, `pme.PMEProps` | 非推奨だが動作 |

### 非推奨（将来削除予定）

| パス | 代替 |
|------|------|
| `pme.context` 直接アクセス | `pme.execute()` / `pme.evaluate()` |
| `pme.NAMESPACE_*` | 削除（内部用） |
| `pme.PUBLIC_NAMES` | 削除（内部用） |
| `pme.validate_public_namespace()` | `pme.debug.validate_namespace()` |
| `pme.get_namespace_report()` | `pme.debug.report()` |

---

## テスト項目

1. `import pme` が動作する
2. `from pie_menu_editor import pme` が動作する
3. `pme.execute("print('ok')")` が動作する
4. `pme.find_pm("...")` が動作する
5. `pme.context.add_global()` が動作する（後方互換）
6. Reload Scripts で正しくリロードされる
7. Extensions パッケージパスでも動作する

---

## 参照

- `@_docs/design/api/pme_api_plan.md` - 既存 API 計画
- `@_docs/design/api/pme_standard_namespace.md` - 標準名前空間
- `@.claude/rules/milestones.md` - マイルストーン
