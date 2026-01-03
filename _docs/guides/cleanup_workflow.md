---
title: Dependency Cleanup Workflow
status: stable
last_updated: 2026-01-01
---

# Dependency Cleanup Workflow

Claude Code を使ったレイヤ違反クリーンアップの自動化ワークフロー。

---

## 概要

1. **ログ生成**: Blender を起動して NDJSON ログを出力
2. **ログ解析**: Python スクリプトで違反を抽出・分類
3. **修正実施**: Low risk な違反から順に修正
4. **検証**: 再度ログを生成して違反数を確認

---

## 1. ログ生成

### 方法 A: GUI で起動

1. Blender を通常起動
2. PME2 アドオンを有効化
3. `.cursor/debug.log` に NDJSON が出力される

### 方法 B: Background モードで起動（推奨）

```bash
# Windows
blender --background --python-expr "import bpy; bpy.ops.preferences.addon_enable(module='pie_menu_editor')"

# ログは .cursor/debug.log に出力
```

### 前提条件

ログ出力には以下のデバッグフラグが必要（現在はデフォルトで有効）：

```python
# __init__.py
DBG_DEPS = True        # レイヤ違反検出
DBG_STRUCTURED = True  # NDJSON 形式出力
```

---

## 2. ログ解析

### スクリプトの使い方

```bash
# デフォルト: .cursor/debug.log を解析
python .claude/scripts/analyze_deps_log.py

# 別のログファイルを指定
python .claude/scripts/analyze_deps_log.py path/to/debug.log

# JSON 形式で出力
python .claude/scripts/analyze_deps_log.py --json

# ログをクリア
python .claude/scripts/analyze_deps_log.py --clear
```

### 出力例

```markdown
## Summary

- **Total violations**: 49
- **High risk**: 5 (Phase 3+ まで禁止)
- **Medium risk**: 16 (Phase 3 で対処)
- **Low risk**: 28 (Phase 2-B から着手可能)
```

### 優先度の判定基準

| Priority | Patterns | Action |
|----------|----------|--------|
| High | runtime, modal, keymap_helper, previews_helper | 触らない |
| Medium | editors → operators, ui → prefs | Phase 3 で対処 |
| Low | legacy wrappers, `from X import *` | すぐ着手可能 |

---

## 3. 修正パターン

### Pattern A: Legacy ラッパーの整理

**Before:**
```python
# editors/menu.py
from ..addon import get_prefs, ic
```

**After:**
```python
# editors/menu.py
from .. import pme
prefs = pme.get_prefs()  # 将来のファサード経由
```

### Pattern B: 明示的インポート

**Before:**
```python
from ..operators import *
```

**After:**
```python
from ..operators import (
    PME_OT_exec,
    PME_OT_pm_hotkey_remove,
)
```

### Pattern C: 再エクスポートの削除

旧パスからの re-export が不要な場合は削除：

```python
# ed_pie_menu.py (旧)
from .editors.pie_menu import Editor  # 削除候補
```

---

## 4. 検証

### 修正後のチェックリスト

1. **ログ再生成**
   ```bash
   python .claude/scripts/analyze_deps_log.py --clear
   # Blender を再起動
   python .claude/scripts/analyze_deps_log.py
   ```

2. **違反数の確認**
   - Low risk が減っていること
   - 新しい違反が増えていないこと

3. **動作テスト**
   - [ ] アドオン有効化でエラーなし
   - [ ] 基本操作（PM 作成・呼び出し）が動作
   - [ ] 永続化（再起動後も設定が残る）

---

## 5. Claude Code での使い方

### ログ解析の依頼

```
.cursor/debug.log を解析して、Low risk な違反を一覧表示して
```

→ Python スクリプトを実行して結果を返す

### 修正の依頼

```
addon への依存を pme ファサード経由に変更して（Low risk のみ）
```

→ 具体的な修正箇所と変更案を提示

### 進捗確認

```
現在の違反数を確認して
```

→ ログを再解析して前回との差分を報告

---

## ファイル構成

```
.claude/
├── scripts/
│   └── analyze_deps_log.py    # ログ解析スクリプト
├── agents/
│   └── deps-log-analyzer.md   # サブエージェント定義（プラグイン化予定）
└── rules/
    ├── dependency_cleanup_plan.md  # 優先度と方針
    └── cleanup_workflow.md         # 本ドキュメント

.cursor/
└── debug.log                  # NDJSON 形式のデバッグログ
```

---

## 参照

- `rules/dependency_cleanup_plan.md` — 優先度と対象候補
- `rules/architecture.md` — レイヤ構造の定義
- `rules/milestones.md` — フェーズ計画
- `infra/debug.py` — `DBG_DEPS`, `detect_layer_violations()`
