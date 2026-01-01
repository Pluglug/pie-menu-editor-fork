# rules/milestones.md

PME2 開発のマイルストーンとフェーズ定義。

「観測 → 設計 → 実装 → ライフサイクル」の時間軸に沿って構成し、各フェーズで混線なく作業を進められるようにする。

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

### ローダー構成

現在、2 つのローダーが共存しています：

| フラグ | ローダー | 説明 |
|--------|----------|------|
| `USE_PME2_LOADER = False` | 旧ローダー | `MODULES` タプル + `get_classes()` による手動順序管理 |
| `USE_PME2_LOADER = True` | 新ローダー | `init_addon()` + `register_modules()` による自動依存解決 |

α 系列では両方を共存させながら、漸進的に新ローダーへ移行します。旧ローダーの削除は RC フェーズで実施予定。

### 既知のリグレッション

- ⚠️ **Reload Scripts が壊れている** (Issue #64, #65)
  - `ParsedData.pm_flick` 属性エラー（props 登録タイミングの問題）
  - カスタムアイコンが読み込まれない（previews ライフサイクルの問題）
  - **Phase 1 のスコープ外として意図的に保留**
  - **v2.0.0-alpha.2 までに「最低限死なない状態」に戻す予定**

### 成果物

- レイヤ違反 49 件の可視化
- 54 モジュールの線形ロード順序
- register/unregister の両方で新ローダーが動作

---

## v2.0.0-alpha.1 (Phase 2-A: UI & Editor Observation)

**目標**: UI リスト・Editor 基盤・pme API の **現状を「観測」し、文書化する**

このフェーズでは構造を大きく動かさず、「見る・書く」に徹する。

### 計画タスク

#### UI リストの観測

- [x] `WM_UL_pm_list`, `PME_UL_pm_tree` の責務と依存先の洗い出し ✅
  - どの関数が「UI 表示のみ」か
  - どの部分が `prefs` や `pme_types` の実データに触れているか
  - 観測結果は `rules/ui_list_analysis.md` にまとめた

#### Editor 基盤の観測

- [x] `EditorBase` と各 Editor (`editors/*.py`) の依存マップ作成 ✅
  - `editors → ui` / `editors → pme` / `editors → operators` などの矢印を整理
  - 観測結果は `rules/editor_dependency_map.md` にまとめた

#### pme API の観測

- [x] `pme.props` / `PMEProps` / `ParsedData` / `pme.context` の **現状 API と使用箇所のインベントリ作成** ✅
  - 観測結果は `rules/api/pme_api_current.md` にまとめた
- [x] 「どのシンボルが、どのモジュールから呼ばれているか」のマップ作成 ✅

### ゴール ✅ 達成

- Editor / UI / pme / props の依存関係が `rules/*.md` 上で文章と簡単な図で説明できること
- **このフェーズでは「EditorBase が ui 層から完全に独立」などの大きな構造変更は行わない**
- 「観測」と「設計メモ」の段階までに留める

### 成果物

- `rules/api/pme_api_current.md` — pme モジュールの現状インベントリ ✅
- `rules/ui_list_analysis.md` — UI リストの責務分析 ✅
- `rules/editor_dependency_map.md` — Editor の依存関係マップ ✅

---

## v2.0.0-alpha.2 (Phase 2-B: Reload Hotfix + pme API Specification)

**目標**:
1. Reload Scripts の「即死級」問題をホットフィックスで抑え、開発ループに使えるレベルに戻す
2. `pme` 外部 API の **仕様を確定**する（Stable / Experimental / Internal のラベリング）
3. Executor Bundle (`pme.execute/evaluate`) の **設計検討**（実装は最小限 or 後ろへ送る）

> **方針変更**: 「`editors` / `ui` が `pme` API 経由で動く構成」の実装は **Phase 3 以降に送る**。
> α 段階では設計と仕様策定に徹し、大規模なコード変更は避ける。

### 計画タスク

#### Reload Scripts ホットフィックス（最優先） ✅ 完了

**目標**: ライフサイクルの完全設計は Phase 3 で行う。ここでは「F3 → Reload で毎回クラッシュ」を止めるラインまで回復。

**Issue #64 (ParsedData / props)** ✅:
- [x] `ParsedData.__getattr__()` を追加し、`prop_map` が空でも既知のプロパティにはフォールバックデフォルト値を返す
- [x] `_FALLBACK_DEFAULTS` 辞書で既知のプロパティのデフォルト値をハードコード
- [x] 警告ログで問題箇所を追跡可能にした

**Issue #65 (previews / icons)** ✅:
- [x] `refresh()` と `unregister()` に try-except ガードを追加
- [x] `ph.unregister()` 呼び出しをコメントアウト（警告スパム対策）
- [x] アイコンは Reload 後も維持される（一度目のロードが残る）

**やらないこと（Phase 3 送り）**:
- props 登録タイミングの再設計
- ParsedData キャッシュのライフサイクル管理
- previews の正しい再初期化フロー

#### pme API 仕様確定 ✅ 完了

- [x] `rules/api/pme_api_current.md` の観測結果を確認 ✅ (Phase 2-A で完了)
- [x] `rules/api/pme_api_plan.md` で Stability level を最終確定 ✅
- [x] 外部スクリプトからの利用シナリオを文書化 ✅

**v2.0.0 での方針**:
- **全ての公開 API は Experimental** とする
- Stable ラベルは v2.1.0 以降で、利用実績を見て付与
- 今の段階で Stable を約束すると、将来のリファクタの自由度を失う

#### Executor Bundle（設計のみ）

Executor API (`pme.execute()`, `pme.evaluate()`) について:

- [ ] API シグネチャを `rules/api/pme_api_plan.md` に確定（既存の Draft を確認）
- [ ] エラーハンドリング方針を決定（例外 vs Result オブジェクト）
- [ ] **実装は検討のみ**: 内部利用 + 実験レベルに留め、外部公開は Phase 3 以降

**Phase 3 以降に送るもの（実装）**:
- `editors` から `pme` API 経由でアクセスする導線の実装
- Menu Integration API (`find_pm`, `invoke_pm`) の実装
- `pme.add_global()` の外部公開

#### 依存クリーンアップ（横串）

- [ ] Low risk なレイヤ違反を 3〜5 件修正
- [ ] 対象は `rules/dependency_cleanup_plan.md` に従う

### 受け入れ基準

- [x] F3 → Reload Scripts 実行時に、Prefs 画面と基本的な Pie 呼び出しがエラーなしで動作する ✅
  - ライフサイクルの完全設計は Phase 3 で行う
  - この時点では「死なない」が最低ライン → **達成**
- [x] `pme` の public surface と Stability level が `rules/api/pme_api_plan.md` に明文化されている ✅
- [ ] Low risk なレイヤ違反が 3〜5 件削減されている (Phase 2-B 残タスク)

---

## v2.0.0-beta.1 (Phase 3-A: Runtime Lifecycle – Props & ParsedData)

**目標**: `pme.props`, `PMEProps`, `ParsedData` と PropertyGroup 登録タイミングを正面から再設計し、Reload 前後で一貫した状態になるようにする

### 計画タスク

- [ ] PropertyGroup / props 登録を「モジュール import 時」から切り離し、`register()` / `unregister()` に集約する設計検討と実装
- [ ] `ParsedData` の生成とキャッシュが、Reload 前後で不整合を起こさないようにする
- [ ] `pme.props` の `prop_map` が「未定義のまま parse に入る」パスを潰す
- [ ] ライフサイクル設計を `rules/runtime_lifecycle.md` (新設) に文書化

### 受け入れ基準

- [ ] Reload Scripts 実行後も、Pie データのパースと実行が一貫して動作する
- [ ] `ParsedData` / `props` 周りの挙動が `rules/runtime_lifecycle.md` に文章化されている

---

## v2.0.0-beta.2 (Phase 3-B: Runtime Lifecycle – Previews & Handlers)

**目標**: previews / icons / handlers / timers のライフサイクルを整理し、register / unregister / Reload 全てで矛盾が起きないようにする

### 計画タスク

- [ ] `previews_helper` の `ph.unregister()` を含む全ライフサイクルを定義し直す
- [ ] ハンドラ / タイマー / modal オペレーターの登録・削除パターンを全て棚卸し
- [ ] 「null handler で `callback_remove` が落ちる」パターンを構造的に潰す
- [ ] ライフサイクルポリシーを `rules/runtime_lifecycle.md` に追記

### 受け入れ基準

- [ ] Reload 前後で handlers / timers / previews に関するエラーが出ない
- [ ] ライフサイクルポリシーが `rules/runtime_lifecycle.md` で説明されている

---

## v2.0.0-RC (Release Candidate)

**目標**: PME2 の安定リリース準備

### 前提条件

- Phase 1〜3 の全タスク完了
- Reload Scripts が安定動作
- レイヤ違反が許容範囲内

### 計画タスク

#### ローダーの整理

- [ ] 旧ローダーの削除または完全封印
  - `USE_PME2_LOADER` を常時 `True` に固定
  - 旧コード (`MODULES` タプル、`get_classes()`) を削除

#### レイヤ違反の最終整理

- [ ] レイヤ違反の許容範囲を明文化
  - 例: `legacy → 新レイヤ` は OK（後方互換ラッパー）
  - 例: `core → operators` は禁止
- [ ] 残存するレイヤ違反を修正またはドキュメント化

#### テスト整備

- [ ] `core/` 層の最低限の自動テスト導入
  - round-trip テスト（`to_dict` / `from_dict`）
  - JSON パース / シリアライズテスト
- [ ] `rules/testing.md` の更新

#### ドキュメント

- [ ] ドキュメント整備
- [ ] マイグレーションガイド (PME1 → PME2)

---

## Post v2.0.0 (将来計画)

v2.0.0 リリース後の計画。API 仕様は v2 系列で既に確定している前提。

### pme API の外部公開

- `pme` を外部ファサードとして正式公開
- v2.x 系での互換性維持を約束する Stable API の提供
- ユーザースクリプトや他アドオンからの安全なアクセス

### パフォーマンス最適化

- 大量のパイメニュー時の起動速度改善
- PropertyGroup の遅延初期化
- キャッシュ戦略の見直し

### 新機能

- (未定義 - ユーザーフィードバック次第)

---

## フェーズ間の関係図

```
Phase 1 (alpha.0)    Phase 2-A (alpha.1)    Phase 2-B (alpha.2)    Phase 3-A (beta.1)    Phase 3-B (beta.2)    RC
       │                    │                      │                      │                     │            │
  レイヤ分離の ─→   UI/Editor/pme を ─→   Reload Hotfix + ─→   Props/ParsedData ─→   Previews/Handlers ─→   安定
  土台作り            「観測」             API 仕様確定        のライフサイクル       のライフサイクル      リリース
                                                                   再設計                 整理
       │                    │                      │                      │                     │            │
  ─────┴────────────────────┴──────────────────────┴──────────────────────┴─────────────────────┴────────────┤
                                         Dependency Cleanup Track（横串）                                      │
  ─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### フェーズの方針

| フェーズ | 方針 | コード変更 | 依存クリーンアップ |
|----------|------|-----------|-------------------|
| alpha.1 | 観測に徹する | 最小限（文書化中心） | 分析のみ（違反クラスタリング） |
| alpha.2 | 設計 + Hotfix | 小規模（Reload 修正 + 仕様確定） | Low risk 3〜5 件 |
| beta.1 | 再設計 + 実装 | 中規模（props/ParsedData 周り） | props 周辺 5〜10 件 |
| beta.2 | 再設計 + 実装 | 中規模（handlers/timers/previews） | handlers 周辺 5〜10 件 |
| RC | 整理 + テスト | 削除・整理中心 | 残りを許容リストへ |

---

## Dependency Cleanup Track

レイヤ違反を段階的に削減する横串プロセス。詳細は `rules/dependency_cleanup_plan.md` を参照。

### 概要

- `DBG_DEPS=True` で違反を可視化
- 各フェーズで少量ずつ修正（一気に直さない）
- Phase 1 完了時点: **49 件** の違反

### 各フェーズの目標

| フェーズ | 削減目標 | 対象 |
|----------|---------|------|
| alpha.1 | 0 件 | 分析のみ |
| alpha.2 | 3〜5 件 | Low risk（明示的 import 等） |
| beta.1 | 5〜10 件 | props/ParsedData 周辺 |
| beta.2 | 5〜10 件 | handlers/previews 周辺 |
| RC | 残りを整理 | 許容リストをドキュメント化 |
