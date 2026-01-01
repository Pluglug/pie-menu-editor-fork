# rules/milestones.md

PME2 開発のマイルストーンとフェーズ定義。

---

## v2.0.0-alpha.0 (Phase 1: Layer Separation) ✅ COMPLETED

**目標**: 内部構造の可視化とレイヤ分離の土台作り

### 完了した作業

- [x] 新ローダー (`init_addon` / `register_modules`) の実装
- [x] レイヤ構造の定義: `core → infra → ui → editors → operators → prefs`
- [x] デバッグインフラの整備 (`DBG_DEPS`, `DBG_PROFILE`, 構造化ログ)
- [x] 一部モジュールの新パッケージへの移動
  - `core/constants.py`
  - `infra/debug.py`
  - `ui/layout.py`, `ui/lists.py`, `ui/panels.py`
  - `editors/` 配下 (各エディタ)
- [x] 旧モジュールからの薄いラッパー（後方互換性維持）
- [x] インポートパスの正規化

### 既知の未解決問題

- ⚠️ **Reload Scripts が壊れている** (Issue #64, #65)
  - `ParsedData.pm_flick` 属性エラー
  - カスタムアイコンが読み込まれない
  - **Phase 1 のスコープ外として意図的に保留**

### 成果物

- レイヤ違反 49 件の可視化
- 54 モジュールの線形ロード順序
- register/unregister の両方で新ローダーが動作

---

## v2.0.0-alpha.1 (Phase 2: UI & Editor Foundation)

**目標**: UI リストとエディタ基盤の「観測的整理」

### 計画タスク

- [ ] `WM_UL_pm_list`, `PME_UL_pm_tree` の責務分離
- [ ] `EditorBase` と各 Editor の依存関係整理
- [ ] `pme.props` / `PMEProps` / `ParsedData` の core data model 整理検討
- [ ] `pme.context` の責務整理（実行コンテキスト vs UI 依存）

### ゴール

- EditorBase が ui 層に依存せず動作
- pme API の public surface が文書化される

---

## v2.0.0-beta (Phase 3: Runtime Lifecycle)

**目標**: Reload Scripts の完全サポート

### 計画タスク

- [ ] Issue #64 (ParsedData lifecycle) の根本修正
- [ ] Issue #65 (previews lifecycle) の根本修正
- [ ] props 登録のタイミング見直し（集中登録 or 遅延登録）
- [ ] ハンドラ/タイマーのライフサイクル監査

### 受け入れ基準

- [ ] F3 → Reload Scripts でエラーが出ない
- [ ] カスタムアイコンが Reload 後も表示される
- [ ] 既存のパイメニューが Reload 後も動作する

---

## v2.0.0 (Release Candidate)

**目標**: PME2 の安定リリース

### 前提条件

- Phase 1-3 の全タスク完了
- Reload Scripts が安定動作
- レイヤ違反ゼロ（または許容範囲内）

### 追加作業

- [ ] ドキュメント整備
- [ ] マイグレーションガイド (PME1 → PME2)
- [ ] 自動テストの導入（core 層）

---

## 将来計画 (Post v2.0.0)

### pme API の外部公開

- `pme` を外部ファサードとして安定化
- Stability levels: Stable / Experimental / Internal
- ユーザースクリプトからの安全なアクセス

### パフォーマンス最適化

- 大量のパイメニュー時の起動速度
- PropertyGroup の遅延初期化

### 新機能

- (未定義 - ユーザーフィードバック次第)
