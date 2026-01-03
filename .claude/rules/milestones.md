# PME2 Milestones (Summary)

> 詳細な履歴: `@_docs/archive/milestones_full.md`

## 現在のステータス

| フェーズ | 状態 | 主要成果 |
|----------|------|---------|
| Phase 1 (alpha.0) | ✅ | 新ローダー、レイヤ分離 |
| Phase 2-A/B/C (alpha.1-2) | ✅ | モジュール分割、違反 49→21件 |
| Phase 4-A (alpha.3) | ✅ | `core/props.py` 分離 |
| **Phase 4-B** | ⏳ 次 | 標準名前空間、外部 API |

## 基本方針

- **Core 層の設計・実装**を最優先（Issue #64 の根本解決）
- `use_reload` パターンは保留（Issue #67）
- `DBG_DEPS=True` でレイヤ違反を可視化

## 現在の構造

```
core/props.py   → PMEProp, PMEProps, ParsedData, props
pme.py          → UserData, PMEContext, context + 再エクスポート
```

## Issue #64 の状況

**ロード順は改善したが、根本原因は別**:
- `type=pm` の ParsedData が `rm_title`（type=rm）にアクセス
- **仮説**: 型を跨いだプロパティアクセスが原因
- **次の調査**: EditorBase の汎用描画コード

## 次のフェーズ: Phase 4-B

- [ ] `core/namespace.py` に標準名前空間を定義
- [ ] `pme.execute()` / `pme.evaluate()` のファサード実装
- [ ] 外部ツールからの利用シナリオを検証

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
