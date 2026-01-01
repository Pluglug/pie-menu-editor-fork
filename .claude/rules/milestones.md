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

- [ ] `WM_UL_pm_list`, `PME_UL_pm_tree` の責務と依存先の洗い出し
  - どの関数が「UI 表示のみ」か
  - どの部分が `prefs` や `pme_types` の実データに触れているか
  - 観測結果は `rules/ui_list_analysis.md` (新設) にまとめる

#### Editor 基盤の観測

- [ ] `EditorBase` と各 Editor (`editors/*.py`) の依存マップ作成
  - `editors → ui` / `editors → pme` / `editors → operators` などの矢印を整理
  - 観測結果は `rules/editor_dependency_map.md` (新設) にまとめる

#### pme API の観測

- [ ] `pme.props` / `PMEProps` / `ParsedData` / `pme.context` の **現状 API と使用箇所のインベントリ作成**
  - 観測結果は `rules/pme_api_current.md` (本タスクで新設) にまとめる
- [ ] 「どのシンボルが、どのモジュールから呼ばれているか」のマップ作成

### ゴール

- Editor / UI / pme / props の依存関係が `rules/*.md` 上で文章と簡単な図で説明できること
- **このフェーズでは「EditorBase が ui 層から完全に独立」などの大きな構造変更は行わない**
- 「観測」と「設計メモ」の段階までに留める

### 成果物（予定）

- `rules/pme_api_current.md` — pme モジュールの現状インベントリ
- `rules/ui_list_analysis.md` — UI リストの責務分析
- `rules/editor_dependency_map.md` — Editor の依存関係マップ

---

## v2.0.0-alpha.2 (Phase 2-B: pme API Design + Reload Hotfix)

**目標**:
1. `pme` を「外部 API 候補」として設計し、Stable / Experimental / Internal のレベルを決める
2. `editors` / `ui` の一部が `pme` API 経由で動く最小構成を作る
3. Reload Scripts の「即死級」問題をホットフィックスで抑え、開発ループに使えるレベルに戻す

### 計画タスク

#### pme API 設計

- [ ] `rules/pme_api_current.md` をベースに、公開 API の設計案を策定
- [ ] `rules/pme_api_plan.md` (本タスクで新設) で Stable / Experimental / Internal を定義
- [ ] 外部スクリプトや他アドオンからの利用シナリオを文書化

#### 最小限の統合実装

- [ ] `editors` 側のごく一部から、`prefs` を直接舐めるのではなく `pme` API 経由でアクセスする実験的な導線を作る（規模は小さく）
- [ ] 依存方向のルール (`operators → prefs` 禁止) の実践

#### Reload Scripts ホットフィックス

**目標**: ライフサイクルの完全設計は Phase 3 で行う。ここでは「F3 → Reload で毎回クラッシュ」を止めるラインまで回復。

**Issue #64 (ParsedData / props)**:
- [ ] `ParsedData.__init__()` が `prop_map` 空で呼ばれたときに死なないガード追加
- [ ] `props.parse()` で未登録 type を受けたときの fallback 処理
- [ ] `pm_flick` などの属性アクセスが AttributeError で落ちる箇所に `getattr(..., default)` を入れる

**Issue #65 (previews / icons)**:
- [ ] `previews_helper.unregister()` が null collection で落ちないガード
- [ ] Reload 後に `preview_collections` が空のまま描画に入るパスの暫定対処
- [ ] アイコンが出ない状態は許容、クラッシュだけを止める

**やらないこと（Phase 3 送り）**:
- props 登録タイミングの再設計
- ParsedData キャッシュのライフサイクル管理
- previews の正しい再初期化フロー

### 受け入れ基準

- [ ] `pme` の public surface が `rules/pme_api_plan.md` に明文化されている
- [ ] F3 → Reload Scripts 実行時に、Prefs 画面と基本的な Pie 呼び出しがエラーなしで動作する
  - ライフサイクルの完全設計は Phase 3 で行う
  - この時点では「死なない」が最低ライン

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
  レイヤ分離の ─→   UI/Editor/pme を ─→   pme API 設計 + ─→   Props/ParsedData ─→   Previews/Handlers ─→   安定
  土台作り            「観測」             Reload Hotfix       のライフサイクル       のライフサイクル      リリース
                                                                   再設計                 整理
```

### フェーズの方針

| フェーズ | 方針 | コード変更 |
|----------|------|-----------|
| alpha.1 | 観測に徹する | 最小限（文書化中心） |
| alpha.2 | 設計 + 最小実装 | 小規模（API 導線 + ホットフィックス） |
| beta.1 | 再設計 + 実装 | 中規模（props/ParsedData 周り） |
| beta.2 | 再設計 + 実装 | 中規模（handlers/timers/previews） |
| RC | 整理 + テスト | 削除・整理中心 |
