# Core Layer ドキュメント

PME Core Components Guide の詳細解説ドキュメント集。

## メインドキュメント

- [CORE_LAYER_DESIGN_GUIDE.md](./CORE_LAYER_DESIGN_GUIDE.md) - 全体概要
- [PME2 理想アーキテクチャ](./ideal-architecture.md) - 再設計のビジョン

## サブページ

| ドキュメント | 説明 |
|------------|------|
| [PMEProps スキーマシステム](./pmeprops-schema-system.md) | 現行プロパティスキーマ管理、dataclass 移行検討 |
| [EditorBase 分解計画](./editorbase-decomposition.md) | PME2 再設計の中心提案、Schema/Behavior/View 分離 |
| [BlContext プロキシ](./blcontext-proxy.md) | コンテキストプロキシの分析と簡素化提案 |
| [Editor と PMItem の関係](./editor-pmitem-relationship.md) | データと振る舞いの分離パターン、アダプターパターン |

## 今後追加予定

- PMEContext - 実行エンジン
- PMItem / PMIItem データモデル
