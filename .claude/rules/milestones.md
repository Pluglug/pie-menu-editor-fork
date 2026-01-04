# PME2 Milestones (Summary)

> 詳細な履歴: `@_docs/archive/milestones_full.md`

## 現在のステータス

| フェーズ | 状態 | 主要成果 |
|----------|------|---------|
| Phase 1 (alpha.0) | ✅ | 新ローダー、レイヤ分離 |
| Phase 2-A/B/C (alpha.1-2) | ✅ | モジュール分割、違反 49→21件 |
| Phase 4-A (alpha.3) | ✅ | `core/props.py` 分離、#64 解消 |
| Phase 4-B | ✅ | 標準名前空間、外部 API ファサード |
| Phase 5-A | ✅ | オペレーター分離（#74）、base.py 71%削減 |

## 基本方針

- **Core 層の設計・実装**を最優先
- `use_reload` パターンは保留（Issue #67）
- `DBG_DEPS=True` でレイヤ違反を可視化

## 現在の構造

```
core/namespace.py → Stability, NAMESPACE_*, PUBLIC_NAMES, is_public()
core/props.py     → PMEProp, PMEProps, ParsedData, props
pme.py            → PMEContext, UserData, context
                  → execute(), evaluate() (Experimental)
                  → find_pm(), list_pms(), invoke_pm() (Experimental)
```

## 解決済み Issue

| Issue | 内容 | 解決方法 |
|-------|------|---------|
| #64 | ParsedData の cross-type property binding | `is_empty` で `__dict__` 直接参照 |

## 関連 Issue

| Issue | 内容 | 状態 |
|-------|------|------|
| #70 | Phase 4-B 外部 API 実装 | ✅ 完了 |
| #69 | Extend Panel の name 設計問題 | PME2 スキーマで対応予定 |
| #65 | icon previews の Reload 問題 | 解消済み、モジュール移動待ち |
| #67 | use_reload パターン | 保留 |
| #73 | モジュール読み込み順序問題 | ✅ workaround 適用、設計問題は #74 へ |
| #74 | Phase 5-A オペレーター分離 | ✅ 完了 |

## Phase 4-B 完了サマリー

- [x] `core/namespace.py` に標準名前空間を定義
- [x] `pme.execute()` / `pme.evaluate()` ファサード実装
- [x] `pme.find_pm()` / `list_pms()` / `invoke_pm()` 実装
- [x] ドキュメント同期（PR #72）

## Phase 5-A: オペレーター分離

**目標**: `editors/base.py` から 33 個のオペレーターを `operators/` に移動

**背景** (Issue #73 から):
- `editors/base.py` に EditorBase と 33 個のオペレーターが同居
- `preferences.py` が 8 個のオペレーターをインポート → `editors` レイヤへの依存
- これが循環的な読み込み順序問題を引き起こした

**成果**:
- [x] 33 個のオペレーターを `operators/ed/` に移動（8 ファイル）
- [x] `editors/base.py` を 2662 → 768 行に削減（71%）
- [x] `preferences` → `editors` 依存を解消
- [x] `pm.ed` null safety guards 追加

**Phase 5-B（将来検討）**:
- EditorBase の責務整理（Behavior / View 分離）
- 理想アーキテクチャに向けた段階的移行

## 完了したフェーズ

| フェーズ | 内容 | 結果 |
|---------|------|------|
| Phase 5-B | pme_types LAYER 変更 | 17 → 13 件 (-4) ✅ |
| Phase 7 | bl_idname リテラル化 | 13 → 12 件 (-1) ✅ |

## 保留中のフェーズ

| フェーズ | 内容 | 理由 |
|---------|------|------|
| Phase 6 | constants → previews_helper 分離 | Issue #65 関連 |

## 残存違反の本質分析

12 件の違反は 3 つの本質的問題に分類される:

1. **`_draw_item` 配置問題**: オペレーターに置かれた UI 描画ロジック (3件)
2. **`screen.py`/`utils.py` 責務混在**: infra と ui 関数の同居 (4件)
3. **ランタイム依存**: popup/base のオペレーター呼び出し (3件)

**詳細**: `@_docs/analysis/remaining_violations_analysis.md`

## Phase 8: 薄いラッパー削除

**目標**: プロジェクトルートを `addon.py`, `pme.py` のみにする

### 8-A: 低リスク移動（優先）

| ファイル | 移動先 | 状態 |
|----------|--------|------|
| `macro_utils.py` | `infra/macro.py` | 未着手 |
| `keymap_helper.py` | `infra/keymap.py` | 未着手 |
| `operator_utils.py` | `operators/utils.py` | 未着手 |
| `utils.py` | `infra/utils.py` | 未着手 |
| `property_utils.py` | `infra/property.py` | 未着手 |

### 8-B: 高リスク分離

| タスク | 注意点 | 状態 |
|--------|--------|------|
| `WM_OT_pme_user_pie_menu_call` 切り出し | `_draw_item` が 3 箇所から参照 | 未着手 |
| `prefs` UI 分離 | draw 系メソッドの依存が複雑 | 未着手 |

## 次のステップ候補

- **Phase 8-A**: 薄いラッパー移動（Codex タスク候補）
- **RC 準備**: 許容リスト文書化、旧ローダー削除
- **Issue #65**: OPEN_MODE_ITEMS アイコン問題
- **理想アーキテクチャ**: v2.1.0 以降で Schema/Behavior/View 分離

詳細は `@_docs/guides/rc_roadmap.md` を参照。

## RC への条件

- レイヤ違反 < 30 件 ✅ (現在 12 件)
- Reload Scripts が安定動作
- 旧ローダー削除
- マイグレーションガイド作成

## 参照

| ドキュメント | 用途 |
|-------------|------|
| `@_docs/archive/milestones_full.md` | 完了フェーズの詳細 |
| `@_docs/guides/cleanup_workflow.md` | 違反整理手順 |
| `@_docs/guides/rc_roadmap.md` | RC ロードマップ |
| `@_docs/design/api/pme_api_plan.md` | API 設計 |
