# CLAUDE.md

Claude Code がこのリポジトリで作業する際の基本方針。

---

## 1. プロジェクト概要

**Pie Menu Editor (PME)** は Blender 用 UI 拡張アドオン。`pme2-dev` ブランチは **PME2** の試験実装。

| 項目 | 値 |
|------|-----|
| 対象 Blender | **5.0 以降専用** |
| 現在のフェーズ | **Phase 4-B** ⏳ |
| 開発の焦点 | Core 層の設計・実装 |

### ブランチ構成

| ブランチ | 状態 |
|----------|------|
| `pme2-dev` | PME2 開発版（アクティブ） |
| `pme1-lts` | PME1 最終アーカイブ（凍結） |

**PME1 への還元は行わない**。pme2-dev の成果は PME2 専用。

---

## 2. レイヤ構造

```
prefs      (5)  アドオン設定、全体のハブ
operators  (4)  オペレーター
editors    (3)  エディタロジック
ui         (2)  UI 描画ヘルパー
infra      (1)  Blender API との橋渡し
core       (0)  Blender 非依存のロジック
```

**依存方向**: 上位 → 下位のみ許可

### 禁止パターン

- `core → 他すべて`（core は Blender 非依存）
- `infra → ui/editors/operators/prefs`（下位から上位への依存）
- `下位 → prefs` 直接 import（`addon.get_prefs()` を使う）

**例外**: `TYPE_CHECKING` ブロック内は許可

---

## 3. 基本方針

### 挙動を変えない

- ユーザー操作・ショートカット・データ形式は変更しない
- リファクタリング = 「動きを保ったまま中身を整理」

### 大規模リライト禁止

- ファイル丸ごとの書き換え / 大量の関数名変更 / API 変更は NG
- 小さなステップに分解してから提案

### Blender API は高リスク

- `bpy`, context override, handler, timer, keymap, PropertyGroup
- 変更範囲を極小に保ち、テスト方法を明記

### 触るべきでない領域

- `WM_OT_pme_user_pie_menu_call` など runtime 呼び出しオペレーター
- `PME_OT_modal_*`, `PME_OT_sticky_key_*` など modal/timer/state handler
- `KeymapHelper`, `Hotkey` など keymap 初期化まわり
- `PMEPreferences` のフィールド構造・保存形式

---

## 4. モジュール移動の手順

1. 新モジュールを作成してクラスをコピー
2. 旧モジュールからは `from .ui.layout import LayoutHelper` のように**再エクスポート**
3. いきなり元ファイルを空にしない

**新ローダー** (`DBG_DEPS=True`) でレイヤ違反を可視化できる。

---

## 5. データ互換性

### 維持必須

- PME 1.19.x 系の JSON / backup → PME2 で読み込み可能

### 破壊許容

- 1.18.x 以前の JSON
- エクスポート JSON フォーマット（ただし 1.19.x 形式は読み込めること）
- UI レイアウト、内部クラス名

---

## 6. テスト（毎回実施）

- [ ] Blender 5.0+ で PME2 を有効化 → エラーなし
- [ ] Preferences パネルが表示される
- [ ] Pie Menu を呼び出し → 動作する
- [ ] Blender 再起動後も設定が残る

---

## 7. GitHub 運用 (`gh` コマンド)

### Issue 作成

```bash
gh issue create --title "タイトル" --body "本文" --label "ラベル"
```

- **言語**: Issue 本文は**英語**で書く（国際化・検索性のため）
- **関連 Issue**: 本文に `Related: #XX, #YY` を含める
- **ブランチ情報**: 作業ブランチがあれば末尾に記載

### トラッキング Issue

複数のサブタスクを束ねる親 Issue。タイトルに `[Tracking]` を付ける。

```markdown
## Overview
Brief description of the feature/phase.

## Sub-issues
- [ ] #101 - Sub-task 1
- [ ] #102 - Sub-task 2
- [ ] #103 - Sub-task 3

## Acceptance Criteria
- [ ] All sub-issues closed
- [ ] Tests passing
- [ ] Documentation updated
```

### マイルストーン

| ID | 名前 | 用途 |
|----|------|------|
| 1 | **2.0.0 - JSON Schema v2** | PME2 初回リリース |
| 2 | Phase 8-D: pme API facade | API ファサード実装 |

Issue 作成時: `--milestone "2.0.0 - JSON Schema v2"`

### 主要ラベル

| ラベル | 用途 |
|--------|------|
| `bug` | バグ報告 |
| `enhancement` | 新機能・改善 |
| `schema` | JSON Schema v2 関連 |
| `core` | Core 層の変更 |
| `api` | API 変更・追加 |
| `migration` | データ移行・互換性 |
| `ui/ux` | UI/UX 改善 |
| `documentation` | ドキュメント |
| `ideas` | PME 使用例の共有 |

複数ラベル: `--label "bug,schema"`

### よく使うコマンド

```bash
# Issue 一覧
gh issue list --state open

# Issue 詳細
gh issue view 88

# Issue 編集
gh issue edit 88 --body "新しい本文"

# マイルストーン付きで作成
gh issue create --title "Title" --body "Body" --label "schema" --milestone "2.0.0 - JSON Schema v2"

# Issue をクローズ
gh issue close 88 --reason completed
```

---

## 8. 参照ドキュメント

詳細は `_docs/` に配置。必要時に `@_docs/...` で参照。

| ディレクトリ | 内容 |
|-------------|------|
| `_docs/design/` | API 設計、Core Layer 設計 |
| `_docs/guides/` | 違反整理、オペレーター整理の手順 |
| `_docs/analysis/` | UI リスト分析、依存関係マップ |
| `_docs/archive/` | 完了フェーズの詳細、完全版ドキュメント |

---

Claude は **物理的モジュール分割** を着実に進める役割を担う。
**今あるコードを小さく安全に移動／分離する** ことに集中。
