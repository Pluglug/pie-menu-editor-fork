# PME2 Architecture (Summary)

> 詳細: `@_docs/archive/architecture_full.md`

## レイヤ構造

```
prefs      (5)  アドオン設定、全体のハブ
operators  (4)  オペレーター
editors    (3)  エディタロジック
ui         (2)  UI 描画ヘルパー
infra      (1)  Blender API との橋渡し
core       (0)  Blender 非依存のロジック
```

**依存方向**: 上位 → 下位のみ許可

## 禁止パターン

| パターン | 理由 |
|---------|------|
| `core → 他すべて` | core は Blender 非依存 |
| `infra → ui/editors/operators/prefs` | 下位から上位への依存 |
| `下位 → prefs` 直接 import | `addon.get_prefs()` を使う |

**例外**: `TYPE_CHECKING` ブロック内は許可

## ファサードパターン

```python
# ✅ 推奨
from . import addon
prefs = addon.get_prefs()

# ❌ 非推奨
from .preferences import PMEPreferences
```

## 違反検出

```bash
# Blender 起動時に DBG_DEPS=True で自動検出
# または
python .claude/scripts/analyze_deps_log.py
```

## 現在の構造（Phase 9 進行中）

| モジュール | レイヤ | 内容 |
|-----------|--------|------|
| `core/schema.py` | core | SchemaProp, SchemaRegistry, ParsedData |
| `core/namespace.py` | core | 標準名前空間、公開 API 定義 |
| `core/uid.py` | core | uid 生成・検証 |
| `core/constants.py` | core | 定数 |
| `pme.py` | infra | PMEContext + 再エクスポート |
| `infra/extend.py` | infra | ExtendManager, ExtendEntry |
| `infra/compat.py` | infra | マイグレーション処理 |
| `infra/io.py` | infra | ファイル I/O |
| `ui/layout.py` | ui | LayoutHelper |
| `editors/` | editors | 各エディタ |
| `operators/` | operators | オペレーター群 |

## 参照

- `@_docs/archive/architecture_full.md` — 詳細なルールと図
- `@_docs/analysis/editor_dependency_map.md` — Editor 依存関係
