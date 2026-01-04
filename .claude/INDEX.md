# .claude/ ディレクトリ索引

Claude Code 用のプロジェクト指示。

---

## 構造

```
CLAUDE.md           ← メイン指示（自動ロード）
.claude/
├── rules/          ← 作業指示（自動ロード、最小限）
│   ├── architecture.md
│   ├── milestones.md
│   ├── compatibility.md
│   └── testing.md
├── agents/         ← カスタムエージェント
├── skills/         ← スキル定義
└── scripts/        ← ツールスクリプト

_docs/              ← 参照ドキュメント（@参照でオンデマンドロード）
├── design/         ← API 設計、Core Layer 設計
├── guides/         ← 手順書
├── analysis/       ← 分析結果
└── archive/        ← 完了フェーズの詳細
```

---

## rules/ ファイル（5 件、自動ロード）

| ファイル | 内容 |
|----------|------|
| `architecture.md` | レイヤ構造・依存ルール（要約） |
| `milestones.md` | 現在のフェーズ・状態（要約） |
| `compatibility.md` | Blender バージョンポリシー |
| `testing.md` | 最小テスト手順 |
| `bpy_imports.md` | bpy import スタイルガイド（NEW） |

---

## _docs/ ファイル（オンデマンドロード）

### design/

- `api/pme_api_plan.md` — 外部 API 設計仕様
- `api/pme_api_current.md` — 現行 API インベントリ
- `core-layer/` — Core Layer 設計ドキュメント群
- `schema-rename-plan.md` — pme.props → pme.schema リネーム計画（NEW）

### guides/

- `cleanup_workflow.md` — 違反クリーンアップ手順
- `dependency_cleanup_plan.md` — レイヤ違反削減計画
- `operators_reorganization.md` — operators/ 再編計画
- `rc_roadmap.md` — RC までのロードマップ（NEW）

### analysis/

- `ui_list_analysis.md` — UIList 責務分析
- `editor_dependency_map.md` — Editor 依存関係マップ
- `core_layer_design.md` — Core 層設計（Phase 3）
- `remaining_violations_analysis.md` — 残存違反の本質分析（NEW）

### archive/

- `milestones_full.md` — フェーズ履歴の完全版
- `architecture_full.md` — アーキテクチャの完全版
- `runtime_lifecycle.md` — ライフサイクル問題分析

---

## 使い方

```
# オンデマンドで参照
@_docs/design/api/pme_api_plan.md
@_docs/guides/cleanup_workflow.md
```

---

*最終更新: 2026-01-04*
