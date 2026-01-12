# _docs/ Index

> 最終更新: 2026-01-13

## 構造

```
_docs/
├── design/           # 現行設計ドキュメント
│   ├── api/          # API 設計（別ブランチで作業中）
│   └── core-layer/   # コアレイヤ設計
└── archive/          # アーカイブ済み
```

---

## design/

### PME2_FEATURE_REQUESTS.md
ユーザー要望調査レポート (Blender Artists フォーラムアーカイブ)

### user_pie_menu_call_analysis.md
`WM_OT_pme_user_pie_menu_call` の詳細分析

### api/ (別ブランチで作業中)
pme API 設計ドキュメント群

### core-layer/
将来のコアレイヤ再設計に向けた設計ドキュメント

| ファイル | 内容 |
|----------|------|
| CORE_LAYER_DESIGN_GUIDE.md | PME Core Components Guide |
| ideal-architecture.md | 理想アーキテクチャ |
| editorbase-decomposition.md | EditorBase 分解計画 |
| editor-pmitem-relationship.md | Editor と PMItem の関係 |
| pmeprops-schema-system.md | スキーマシステム解説 |
| blcontext-proxy.md | コンテキストプロキシ |

---

## archive/

完了したフェーズの履歴。参照用に保持。

### phase8-9/
Phase 8-9 (JSON Schema v2) 関連の作業ドキュメント

### analysis/
レイヤ違反分析、依存関係マップなど

### guides/
完了したガイド (cleanup_workflow, rc_roadmap)

### その他
- architecture_full.md - アーキテクチャ詳細
- milestones_full.md - マイルストーン詳細履歴
- runtime_lifecycle.md - ランタイムライフサイクル

---

## 主要ドキュメントの場所

| ドキュメント | 場所 |
|-------------|------|
| JSON Schema v2 | `.claude/rules/json_schema_v2.md` |
| マイルストーン | `.claude/rules/milestones.md` |
| アーキテクチャ | `.claude/rules/architecture.md` |
| 互換性ポリシー | `.claude/rules/compatibility.md` |
