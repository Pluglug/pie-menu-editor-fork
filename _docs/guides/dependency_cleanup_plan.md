---
title: Dependency Cleanup Plan
phase: 2-C
status: in_progress
last_updated: 2026-01-02
---

# Dependency Cleanup Plan

レイヤ違反を段階的に削減するための横串プロセスを定義する。

---

## 目的

**物理的モジュール分割** を進めながら、レイヤ違反を削減していく。

新ローダー (`DBG_DEPS=True`) をコンパスとして使い、違反を可視化しながら作業する。
詳細なワークフローは `rules/cleanup_workflow.md` を参照。

---

## 基本方針

### 1. 一気に直さず、フェーズごとに少量ずつ削る

- 各フェーズで 3〜10 件程度の違反を修正
- 大規模なリファクタリングは避け、安全に進める
- 修正後は必ずテスト（有効化・基本操作・永続化）を実施

### 2. `DBG_DEPS` を「コンパス」として使う

```bash
# ログ解析スクリプト
python .claude/scripts/analyze_deps_log.py
```

- 起動時にレイヤ違反一覧が出力される
- 新たな違反を持ち込まないよう、定期的にチェック

### 3. レイヤ構造の再確認

```
prefs      (5) ← 最上位：アドオン設定、全体のハブ
operators  (4) ← 編集・検索・ユーティリティ系オペレーター
editors    (3) ← 各モード（PMENU/RMENU/DIALOG等）のエディタロジック
ui         (2) ← LayoutHelper, UIList, menus, popups
infra      (1) ← Blender 依存の基盤（pme.context, overlay, keymap）
core       (0) ← 最下位：Blender 非依存のロジック・データ構造
```

**許可される依存**: 上位 → 下位のみ
**禁止される依存**: 下位 → 上位

---

## 優先度の付け方

### High: 絶対に触らない（Phase 3 以降まで禁止）

以下は Reload Scripts 問題の解決まで変更禁止:

| 対象 | 理由 |
|------|------|
| `runtime/modal/handlers` に絡む違反 | 動作が複雑、Blender ライフサイクルに依存 |
| `keymap_helper` 周辺 | ホットキー登録のタイミングが繊細 |
| `previews_helper` 周辺 | Issue #65 の対象 |
| `pme.props` / `ParsedData` 周辺 | Issue #64 の対象 |

### Medium: Phase 3 で集中的に対処

| 対象 | 理由 |
|------|------|
| `editors → prefs` の直接依存 | ファサード経由への移行が必要 |
| `editors → operators` の一部 | インターフェース分離が必要 |
| `ui → prefs` の状態管理 | `PME_UL_pm_tree` のクラス変数問題 |

### Low: Phase 2-B から着手可能

| 対象 | 理由 |
|------|------|
| 旧パスからの再エクスポート | 後方互換ラッパーを整理 |
| `from ..operators import *` | 明示的インポートへ置換 |
| 不要な infra → ui 依存 | 純粋なリファクタリング |
| `lh` グローバルインスタンスの整理 | 影響範囲を確認しながら |

---

## 各フェーズでの目標

### Phase 2-A (alpha.1): 分析のみ

- [x] 違反のクラスタリング（`ui_list_analysis.md`, `editor_dependency_map.md`）
- [x] 優先度付け（本ドキュメント）
- 違反件数の記録: **49 件**（Phase 1 完了時点）

### Phase 2-B (alpha.2): モジュール分割 + Low risk な違反 3〜5 件 ⏳

**モジュール分割タスク**（最優先）:

| タスク | 移動先 | リスク | 状態 |
|--------|--------|--------|------|
| `Overlay`, `Painter`, `Text`, etc. | `infra/overlay.py` | 低 | ✅ 完了 |

**レイヤ違反修正タスク**:

1. ~~`editors/hpanel_group.py`: `from ..operators import *` → 明示的インポート~~ ✅ 完了
2. ~~旧 `ed_*.py` ファイルの薄いラッパー整理~~ ✅ 確認済み (7/11 移行済み、残り4つは Phase 3)
3. ~~不要になった compatibility shim の削除~~ → 調査完了（削除対象なし、下記参照）

**Compatibility shim の調査結果**:
- `re_enable_data` / `tmp_data` (`__init__.py`) — **保持**: Issue #63 でユーザー要望あり、将来復活予定
- `compatibility_fixes.py` の `fix_*` 関数群 — **保持**: マイグレーションパス維持

**やらないこと**:
- `EditorBase` の構造変更
- `PME_UL_pm_tree` の状態管理変更
- `pme.props` 登録タイミングの変更
- pme 外部 API の実装（設計文書のみ）

### Phase 2-C (alpha.3): モジュール分割継続

**モジュール分割タスク**:

| タスク | 移動先 | リスク |
|--------|--------|--------|
| IO 系オペレーター | `infra/io.py` | 低〜中 |
| `operators/` 整理 | 編集系・検索系に分類 | 中 |
| `pme_types.py` | `core/` への移動検討 | 中 |

**目標**: レイヤ違反 40 件未満（Phase 1 時点: 49 件）

---

### Phase 3-A (beta.1): props/ParsedData 周辺 5〜10 件

**対象候補**:

1. `pme.props.*Property()` のモジュールレベル呼び出しを `register()` へ移動
2. `ParsedData` キャッシュのライフサイクル管理
3. `editors → prefs` の一部をファサード経由に

### Phase 3-B (beta.2): handlers/previews 周辺 5〜10 件

**対象候補**:

1. `previews_helper` のライフサイクル整理
2. handler/timer 登録パターンの統一
3. `ui → prefs` の状態管理分離

### RC: 残りを棚卸し

- 残存する違反を「許容」リストとしてドキュメント化
- 例: `legacy → 新レイヤ` は後方互換のため許容

---

## 実務フロー

### 1. 違反リストの生成

```bash
# Blender を起動して DBG_DEPS=True で確認
# または
python -c "from pie_menu_editor.infra.debug import detect_layer_violations; detect_layer_violations()"
```

### 2. 対象の選定

1. 本ドキュメントの「対象候補」から選ぶ
2. Low risk から着手
3. 1 回の PR で 1〜3 件に留める

### 3. 修正の実施

```python
# 例: 明示的インポートへの置換

# Before
from ..operators import *

# After
from ..operators import (
    PME_OT_exec,
    PME_OT_pm_hotkey_remove,
)
```

### 4. テスト

- [ ] アドオン有効化でエラーなし
- [ ] 基本操作（PM 作成・呼び出し）が動作
- [ ] 永続化（再起動後も設定が残る）

### 5. ドキュメント更新

- `rules/architecture.md` に変更を反映（必要に応じて）
- 本ドキュメントの「対象候補」から完了項目を削除

---

## 現在のレイヤ違反一覧（Phase 1 完了時点）

> **注意**: これは Phase 1 完了時点のスナップショット。
> 最新の違反リストは `DBG_DEPS=True` で確認すること。

### 主な違反パターン

| パターン | 件数（概算） | 優先度 |
|---------|-------------|--------|
| `editors → operators` | 10+ | Medium |
| `editors → prefs` (via addon) | 多数 | Medium |
| `ui → prefs` (UIList 内) | 5+ | Medium |
| `infra → ui` (一部) | 3+ | Low |
| Legacy ラッパー経由 | 10+ | Low |

### Phase 2-B の最初の対象（具体例）

以下を最初の修正対象として提案:

1. **`editors/hpanel_group.py:14`**: `from ..operators import *`
   - 明示的インポートへ置換
   - リスク: 低
   - 工数: 小

2. **旧 `ed_pie_menu.py` → `editors/pie_menu.py` の薄いラッパー**
   - 既に移行済みなら削除検討
   - リスク: 低
   - 工数: 小

3. **`PME_UL_pm_tree` のファイル I/O**
   - `save_state()` / `load_state()` を `infra/` に抽出（準備のみ）
   - リスク: 中
   - 工数: 中

---

## 許容される違反（最終的に残すもの）

以下は意図的に残す可能性がある違反:

| パターン | 理由 |
|---------|------|
| 旧パスからの再エクスポート | 後方互換性のため |
| `TYPE_CHECKING` ブロック内の import | 型ヒントのみで実行時に影響なし |
| `prefs` からの下位レイヤ参照 | `prefs` は全体のハブなので許容 |

---

## 長期目標（Post v2.0.0）

### `import X as Y` パターンの削減

**目標**: モジュールをコンポーネント単位で明確に分離するため、エイリアス import を明示的な cherry-pick import に置き換える。

**現状の問題パターン**:
```python
# Before: エイリアス import（依存が不明確）
from . import utils as U
from .ui import panels as PAU
from ..core import constants as CC

# After: 明示的 import（依存が明確）
from .utils import some_function, another_function
from .ui.panels import hide_panel, unhide_panel
from ..core.constants import MAX_STR_LEN, EMODE_ITEMS
```

**メリット**:
- 依存関係が一目で分かる
- 未使用の import を検出しやすい
- IDE の自動補完・リファクタリングが効く
- モジュール分割時の影響範囲が明確

**対象候補**:
| パターン | 使用箇所（概算） | 優先度 |
|---------|-----------------|--------|
| `from . import utils as U` | 多数 | 低 |
| `from .ui import panels as PAU` | 5+ | 中 |
| `from ..core import constants as CC` | 多数 | 低 |
| `from . import keymap_helper as KH` | 多数 | 低 |

**実施時期**: v2.0.0 リリース後、内部構造が安定してから段階的に実施。

---

## 参照

- `rules/architecture.md` — レイヤ構造の定義
- `rules/ui_list_analysis.md` — UIList の責務分析
- `rules/editor_dependency_map.md` — Editor の依存関係マップ
- `rules/milestones.md` — フェーズ計画
- `infra/debug.py` — `DBG_DEPS`, `detect_layer_violations()`
