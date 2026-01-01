# CLAUDE.md

このファイルは、Claude Code（claude.ai/code）がこのリポジトリ（特に `pme2-dev` / `v2.0.0-alpha.0`）で作業する際の基本方針を示します。
詳細なルールや手順は、今後 `rules/` 以下に分割していきます。

---

## 1. プロジェクト概要（PME2 / pme2-dev）

Pie Menu Editor (PME) は、Blender 用の UI 拡張アドオンです。ユーザーは以下のような UI を自由に作成できます。

| 機能名 | 内部モード ID | エディタファイル |
|--------|--------------|-----------------|
| Pie Menu | `PMENU` | `ed_pie_menu.py` |
| Regular Menu | `RMENU` | `ed_menu.py` |
| Pop-up Dialog | `DIALOG` | `ed_popup.py` |
| Sticky Key | `STICKY` | `ed_sticky_key.py` |
| Stack Key | `SCRIPT` | `ed_stack_key.py` |
| Macro Operator | `MACRO` | `ed_macro.py` |
| Modal Operator | `MODAL` | `ed_modal.py` |
| Side Panel (Panel Group) | `PANEL` | `ed_panel_group.py` |
| Hiding Unused Panels | `HPANEL` | `ed_hpanel_group.py` |
| Property | `PROPERTY` | `ed_property.py` |

本リポジトリは、roaoao によるオリジナル PME の **メンテナンスフォーク（PME-F）** をベースにしたものです。

`pme2-dev` ブランチは以下の位置づけです。

* **PME2 Experimental**: 次世代版 PME2 の試験実装ブランチ
* **Blender 対応想定**: **5.0 以降専用**（詳細は `.claude/rules/compatibility.md`）
* **現在のフェーズ**: **Phase 2-B (Module Separation)** ⏳ 進行中

### PME1 と PME2 の関係

| ブランチ | 状態 |
|----------|------|
| `main` / `pme1-lts` | **PME1 安定版**: Hotfix のみ、積極的開発なし |
| `pme2-dev` | **PME2 開発版**: アクティブ開発中 |

* **PME1 への還元は行わない**: pme2-dev の成果は PME2 専用
* **リリース計画**: プレリリース → ユーザーからの安定報告 → 正式リリース

### 開発の焦点

**物理的モジュール分割** を最優先とする。pme 外部 API の設計は完了しているが、**実装は凍結中**（内部構造が安定するまで）。

> **Phase 2-B の状況**:
> - Reload Scripts Hotfix 完了 ✅ (Issue #64, #65)
> - 新ローダー (`init_addon` / `register_modules`) がコンパス
> - `infra/overlay.py` 作成など、モジュール分割を加速中
>
> 詳細は `.claude/rules/milestones.md` を参照

PME1 / PME-F の挙動そのものをすぐに変えることは目的ではありません。
当面は **「挙動はほぼそのまま / 中身だけ段階的に整理」** というスタンスを維持します。

---

## 2. PME2 の設計方針（高レベル）

pme2-dev ブランチでは、次のようなレイヤ構造を目標とします。

```text
core    →   infra   →   ui   →   editors   →   operators   →   prefs
（基盤）      （インフラ）   （UI部品）    （エディタ）        （オペ）         （アドオン設定）
```

おおまかな役割は以下の通りです。

* `core/`

  * Blender 依存をできるだけ薄くした「モデル／プロパティ／コンテキスト」の中核。
  * 例: PM/PMI/Tag 等のデータモデル、プロパティ定義・パース、実行コンテキストなど。

* `infra/`

  * 入力（keymap）、オーバーレイ描画、インポート・エクスポートなど、下回りのインフラ層。
  * Blender ライフサイクルに依存する部分が多いため、変更は高リスク。

* `ui/`

  * `UILayout` ラッパー、リスト／ツリー表示、ポップアップ UI などの「描画ヘルパー／UI 部品」。
  * ここから順番に安全に整理していく。

* `editors/`

  * 各モード（PMENU / RMENU / DIALOG / …）ごとのエディタロジック。
  * `EditorBase` / `Editor` を中心に、「PMEPreferences から徐々に責務を剥がす」予定。

* `operators/`

  * 編集系オペレーター（設定編集）と、ランタイム系オペレーター（Pie 呼び出し・modal 等）。
  * `runtime_*` / `modal_*` / keymap 周りは **最後まで触らない領域** として扱う。

* `prefs/`

  * `PMEPreferences` を含むアドオン設定まわり。
  * 現状は「すべてのハブ」であり、最終フェーズで依存を薄める対象。

現時点では、旧来の構造と新しい構造が混在する移行期です。
Claude は「理想形に向けて一気に揃える」のではなく、「今あるコードを小さく安全に移動／分離する」ことを優先してください。

---

## 3. モジュールロードと互換性

### 3.1 新ローダーが基準

**Phase 1 完了により、新ローダー (`init_addon` / `register_modules`) が動作しています。**

* `USE_PME2_LOADER` フラグで切り替え可能（デフォルト: False）
* 新ローダーは以下を提供:
  * 依存関係に基づくトポロジカルソート
  * レイヤ違反の検出 (`DBG_DEPS=True`)
  * 構造化ログ出力 (`DBG_STRUCTURED=True`)
  * パフォーマンスプロファイル (`DBG_PROFILE=True`)

**今後は新ローダーをコンパスとして進めてください。**
レイヤ違反やロード順の問題は、新ローダーのログで可視化されます。

### 3.2 レガシーローダーとの互換性

* 旧 PME では、`__init__.py` の `MODULES` タプルがロード順序を管理していました。
* レガシーローダーも引き続き動作しますが、**新規開発は新ローダー前提** で進めます。

Claude が行うべきこと:

* モジュールを移動する場合は、
  * まず「新モジュールを作成してクラスをコピー」
  * 旧モジュールからは `from .ui.layout import LayoutHelper` のように **再エクスポート** する
  * という手順にとどめる（いきなり元ファイルを空にしない）。

ロード順や依存方向に関する詳細なルールは、`.claude/rules/architecture.md` を参照してください。

---

## 4. リファクタリングの進め方（Claude 用ガイド）

### 4.1 全体の基本方針

* PME1/PME-F の既存ユーザーの設定や挙動を壊さないことを最優先とする。
* pme2-dev ブランチでは、**挙動変更ではなく構造整理** が主目的。
* 「書き換え」ではなく、「分離」「移動」「依存の見える化」を優先する。

### 4.2 優先して触ってよい領域（安全側）

今後の詳細は `rules/refactor_phases.md` に切り出しますが、pme2-dev 初期フェーズでは以下を優先します。

* `infra/overlay` 相当

  * オーバーレイ描画に関するクラス（`Overlay`, `Painter`, `Text`, `TablePainter`, `OverlayPrefs`, `PME_OT_overlay` など）。
  * 挙動が崩れても致命的ではないため、「最初の分離対象」として扱う。

* `ui/layout` 相当

  * `LayoutHelper`, `CLayout`, `Row`, `Col` など、`UILayout` ラッパー。
  * レイアウト崩れで済む範囲なので、段階的に `ui/` へ移動してよい。

* `ui/lists` 相当

  * `WM_UL_pm_list`, `WM_UL_panel_list`, `PME_UL_pm_tree` など UIList / TreeView。
  * ただし `PME_UL_pm_tree` の状態保存（`save_state` / `load_state`）は `PMEPreferences` と密結合のため、
    **最初は UI 表示ロジックだけ移動し、状態管理は後回し** にする。

### 4.3 触るべきでない領域（高リスク）

詳細は `rules/blender_risks.md` に分離予定ですが、pme2-dev 初期フェーズでは以下は基本触らない前提です。

* `WM_OT_pme_user_pie_menu_call` などの **runtime 呼び出しオペレーター**
* `PME_OT_modal_*`, `PME_OT_sticky_key_*`, `PME_OT_mouse_state_*`, `PME_OT_key_state_*` など **modal / timer / state handler**
* `KeymapHelper`, `Hotkey`, `_KMList*` など **keymap 初期化まわり**
* `BlContext`, `ContextOverride`, `PMEContext` など **context 操作ラッパー**
* `PMEPreferences` 本体（`prefs`）

  * 中身の責務を薄めるために「他方から剥がす」のは OK だが、
    `PMEPreferences` のフィールド構造・保存形式そのものを書き換えるのは後半フェーズまで禁止。

これらに変更を加える必要が出る場合は、
**必ず専用のルールファイル（例: `.claude/rules/runtime_changes.md`）を先に更新し、そこに合意済みの方針を書いてから** パッチを提案してください。

---

## 5. .claude/rules/ ディレクトリとの関係

この `CLAUDE.md` は、「プロジェクト全体の概要」と「大きな方針」だけを書きます。
具体的なルールは `.claude/rules/` 以下のファイルに記載しています。

### 現在存在するルールファイル

* **`.claude/rules/compatibility.md`**
  * 対応 Blender バージョン、データ互換性ポリシー、古いバージョンガードの扱い

* **`.claude/rules/architecture.md`**
  * 目標とするパッケージ構造、レイヤ間の依存方向ルール、init_addon の使い方

* **`.claude/rules/testing.md`**
  * 変更ごとに最低限実施すべき手動テスト項目
  * **Note**: Reload Scripts は現在 KNOWN BROKEN

* **`.claude/rules/milestones.md`**
  * フェーズ定義とマイルストーン (v2.0.0-alpha.0 → beta → RC)
  * 各フェーズの完了条件と計画タスク

### 関連ドキュメント

* **`.claude/rules/api/`**
  * pme 外部 API の設計文書（設計完了、**実装は凍結中**）
  * 内部構造が安定するまで実装は行わない
  * Stability levels: Stable / Experimental / Internal

Claude は、**具体的な作業指示や禁止事項を決めるときは、`CLAUDE.md` よりも `.claude/rules/` の内容を優先**してください。
`CLAUDE.md` は「全体の羅針盤」、`.claude/rules/` は「そのときの具体的な交通ルール」という位置づけです。

---

## 6. Claude 用 行動指針（高レベル）

細かい禁止事項やコードスタイルは `rules/` に委ねますが、pme2-dev で作業する AI エージェントとして、最低限守るべき原則をまとめます。

1. **挙動を変えないことをデフォルトとする**

   * ユーザー操作・ショートカット・データ形式・既存メニュー構造は、明示的な指示がない限り変更しない。
   * リファクタリングの目的は「動きを変えること」ではなく「動きを保ったまま中身を整理すること」。

2. **大規模リライトは禁止**

   * ファイル丸ごとの書き換え / 大量の関数名変更 / API 変更は原則 NG。
   * どうしても必要な場合は、先に小さなステップに分解して `rules/` に計画を書くこと。

3. **Blender API は高リスクとして扱う**

   * `bpy`, context override, handler, timer, keymap, PropertyGroup 周りに触れる変更は、

     * 変更範囲を極小に保ち
     * 「どの Blender バージョンで何をテストすべきか」を明記したうえで提案すること。

4. **パッチ単位で考える**

   * 1 回の変更提案では、1〜数個の論理的にまとまった小さな変更だけを含める。
   * 各パッチには必ず

     * 目的
     * リスクレベル（low / medium / high）
     * 簡易な動作確認手順
       を書くこと。

5. **まず「今の構造」を要約してから手を入れる**

   * いきなり修正案を出すのではなく、

     * 関連モジュール／クラスがどう依存しているか
     * どこがボトルネックか
       を短くまとめてから、その前提に基づいた修正案を出すこと。

---

このブランチは **PME2 のための実験場** です。
PME1 は安定版として別途維持されており、pme2-dev の成果を PME1 に還元する予定はありません。

Claude は、**物理的モジュール分割** を着実に進める役割を担っています。
新ローダー (`DBG_DEPS=True`) をコンパスとして使い、レイヤ違反を削減しながら、
**今あるコードを小さく安全に移動／分離する** ことに集中してください。
