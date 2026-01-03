# PME2 Milestones (Summary)

> 詳細な履歴: `@_docs/archive/milestones_full.md`

## 現在のステータス

| フェーズ | 状態 | 主要成果 |
|----------|------|---------|
| Phase 1 (alpha.0) | ✅ | 新ローダー、レイヤ分離 |
| Phase 2-A/B/C (alpha.1-2) | ✅ | モジュール分割、違反 49→21件 |
| Phase 4-A (alpha.3) | ✅ | `core/props.py` 分離、#64 解消 |
| **Phase 4-B** | ⏳ 進行中 | 標準名前空間、外部 API |

## 基本方針

- **Core 層の設計・実装**を最優先
- `use_reload` パターンは保留（Issue #67）
- `DBG_DEPS=True` でレイヤ違反を可視化

## 現在の構造

```
core/props.py   → PMEProp, PMEProps, ParsedData, props
pme.py          → UserData, PMEContext, context + 再エクスポート
```

## 解決済み Issue

| Issue | 内容 | 解決方法 |
|-------|------|---------|
| #64 | ParsedData の cross-type property binding | `is_empty` で `__dict__` 直接参照 |

## 関連 Issue

| Issue | 内容 | 状態 |
|-------|------|------|
| #69 | Extend Panel の name 設計問題 | PME2 スキーマで対応予定 |
| #65 | icon previews の Reload 問題 | 解消済み、モジュール移動待ち |
| #67 | use_reload パターン | 保留 |

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
