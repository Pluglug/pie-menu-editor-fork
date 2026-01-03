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

## 次のフェーズ候補

- Phase 4-C: 外部ツール連携の実証（Gizmo Creator 等）
- Phase 5-B: EditorBase 責務整理（5-A 完了後に再検討）
- RC 準備: マイグレーションガイド作成

## RC への条件

- レイヤ違反 < 30 件
- Reload Scripts が安定動作
- 旧ローダー削除
- マイグレーションガイド作成

## 参照

| ドキュメント | 用途 |
|-------------|------|
| `@_docs/archive/milestones_full.md` | 完了フェーズの詳細 |
| `@_docs/guides/cleanup_workflow.md` | 違反整理手順 |
| `@_docs/design/api/pme_api_plan.md` | API 設計 |
