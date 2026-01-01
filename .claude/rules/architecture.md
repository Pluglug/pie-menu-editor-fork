# rules/architecture.md

## 1. レイヤ構造（目標）

下に行くほど「土台」側。依存は上位→下位のみ許可。

```
prefs      (5) ← 最上位：アドオン設定、全体のハブ
operators  (4) ← 編集・検索・ユーティリティ系オペレーター
editors    (3) ← 各モード（PMENU/RMENU/DIALOG等）のエディタロジック
ui         (2) ← LayoutHelper, UIList, menus, popups
infra      (1) ← Blender 依存の基盤（pme.context, overlay, keymap）
core       (0) ← 最下位：Blender 非依存のロジック・データ構造
```

### 各レイヤの責務

| レイヤ | 責務 | 配置すべきもの |
|--------|------|---------------|
| `core/` | Blender 非依存のロジック | データモデル、パーサー、ユーティリティ関数 |
| `infra/` | Blender API との橋渡し | `pme.context`, `overlay`, `keymap_helper`, `bl_utils` |
| `ui/` | UI 描画ヘルパー | `LayoutHelper`, `UIList`, menus, popups |
| `editors/` | エディタロジック | `ed_*.py` の Editor クラス |
| `operators/` | オペレーター | 編集系・検索系・ユーティリティ系 |
| `prefs/` | アドオン設定 | `PMEPreferences`, 設定 UI |

## 2. 依存方向のルール

### 許可される依存（上位 → 下位）

```
prefs     → operators, editors, ui, infra, core
operators → editors, ui, infra, core
editors   → ui, infra, core
ui        → infra, core
infra     → core
core      → (なし)
```

### 禁止される依存（下位 → 上位）

- `core` → 他のすべてのレイヤ
- `infra` → `ui`, `editors`, `operators`, `prefs`
- `ui` → `editors`, `operators`, `prefs`
- `editors` → `operators`, `prefs`
- `operators` → `prefs`

### 例外

- `TYPE_CHECKING` ブロック内の import は依存違反としてカウントしない
- `prefs` から下位レイヤへの参照は許可（`prefs` は全体のハブなので）

### 違反検出

- `debug_utils.py` の `detect_layer_violations()` で自動検出
- `DBG_DEPS=True` で起動時にレイヤ違反を警告表示

## 3. モジュールローダー（Phase 1 完了）

### ✅ 新ローダー実装済み

Phase 1 で新ローダーが実装され、動作しています。

```python
# __init__.py (USE_PME2_LOADER=True の場合)
from . import addon

def on_context():
    addon.init_addon(
        module_patterns=PME2_MODULE_PATTERNS,
        use_reload=False,
    )
    addon.register_modules()
```

### `init_addon()` の処理フロー

1. `collect_modules()`: module_patterns に基づいてモジュールを収集
2. `load_modules()`: 各モジュールをロード（必要に応じてリロード）
3. `sort_modules()`: import 文と PropertyGroup 依存を解析 → トポロジカルソート
4. `MODULE_NAMES` に格納

### デバッグフラグ

| フラグ | 出力内容 |
|--------|---------|
| `DBG_DEPS=True` | レイヤ違反一覧、Mermaid 形式の依存グラフ |
| `DBG_PROFILE=True` | 各フェーズの所要時間 |
| `DBG_STRUCTURED=True` | NDJSON 形式のログ |

### レガシーローダー（互換用）

```python
# __init__.py (USE_PME2_LOADER=False の場合)
MODULES = ("addon", "pme", "c_utils", ...)  # 手動順序
get_classes()  # PropertyGroup 依存を解決
```

### `force_order` の扱い

- **デバッグ専用**：循環依存で詰んだときの逃げ道
- `pme2-dev` にマージする前に必ず **空にする**
- `force_order` が空でない = 設計負債

## 4. 現状のフラット構造からの移行

### Phase 1: 安全なファイルから移動 ✅ 完了

| 対象 | 移動先 | 状態 |
|------|--------|------|
| `constants.py` | `core/constants.py` | ✅ 完了 |
| `debug_utils.py` | `infra/debug.py` | ✅ 完了 |
| `layout_helper.py` | `ui/layout.py` | ✅ 完了 |
| `ui.py` (一部) | `ui/lists.py`, `ui/panels.py` | ✅ 完了 |
| `ed_*.py` | `editors/` | ✅ 完了 |

### Phase 2: UI & Editor 基盤の整理（次フェーズ）

| 対象 | 作業内容 | リスク |
|------|----------|--------|
| `WM_UL_pm_list`, `PME_UL_pm_tree` | 責務分離 | 中 |
| `EditorBase` | ui 層依存の削減 | 中 |
| `pme.props` / `ParsedData` | core 寄せ検討 | 中 |

### Phase 3: Runtime Lifecycle（将来）

| 対象 | 作業内容 | リスク |
|------|----------|--------|
| `operators/` (runtime 系) | Reload 対応 | 高 |
| `preferences.py` | 依存削減 | 高 |

詳細は `.claude/rules/milestones.md` を参照。

### 移動手順

1. 新ディレクトリに `__init__.py` を作成
2. 対象クラス/関数を新ファイルにコピー
3. 旧ファイルから `from .new_location import SomeClass` で再エクスポート
4. テスト通過後、旧ファイルの実装を削除

## 5. prefs / pme / addon の役割と依存関係

### prefs の役割

`prefs` レイヤ（`PMEPreferences`）は「Blender UI にぶら下がる設定保存場所」です。

- Blender の `AddonPreferences` を継承
- PM/PMI データ、ユーザー設定、UI 状態を保持
- **下位レイヤから直接触るべき対象ではない**

### pme / addon によるファサード

`operators` や `editors` は、`PMEPreferences` を直に import するのではなく、**ファサード経由で設定を読む** 方針とします。

```python
# 推奨: ファサード経由
from . import pme
prefs = pme.get_prefs()  # 将来の候補

from . import addon
prefs = addon.get_prefs()  # 現状はこちら

# 非推奨: 直接 import
from .preferences import PMEPreferences
prefs = PMEPreferences.get()  # 直接参照は避ける
```

### ファサードを使う理由

1. **テスト容易性**: ファサードをモック可能にすることで、`prefs` なしで下位レイヤをテストできる
2. **依存の局所化**: `prefs` の内部構造が変わっても、ファサードのインターフェースを維持すれば影響範囲を限定できる
3. **レイヤ違反の防止**: 下位レイヤ → `prefs` の直接依存を禁止し、循環依存を防ぐ

### レイヤルールとの整合

| 依存パターン | 可否 | 備考 |
|-------------|------|------|
| `operators → prefs` 直接 | ❌ 禁止 | レイヤ違反 |
| `operators → pme` / `operators → addon` | ✅ 許可 | ファサード経由 |
| `pme` / `addon` → `prefs` | ✅ 許可 | ファサード実装のため |
| `editors → prefs` 直接 | ⚠️ 段階的に禁止 | Phase 2-B で移行 |
| `editors → pme` / `editors → addon` | ✅ 許可 | 推奨パターン |

### 現状と移行計画

現状、多くのモジュールが `preferences.py` を直接 import しています。
これを段階的に `pme` / `addon` ファサード経由に移行します。

| フェーズ | 作業 |
|----------|------|
| Phase 2-A (alpha.1) | 現状の依存パターンを観測・文書化 |
| Phase 2-B (alpha.2) | ファサード API を設計、1-2 箇所で実験 |
| Phase 3 (beta) | `editors` / `operators` を順次移行 |
| RC | 直接依存を削除 or 許容範囲として文書化 |

詳細は `rules/pme_api_plan.md` を参照。

## 6. pme モジュールの位置づけ

### 現状

`pme` モジュールは以下を提供:

- `PMEContext` / `context`: 実行コンテキスト
- `PMEProps` / `props`: プロパティ管理
- `ParsedData`: パース済みプロパティ

レイヤ的には `infra` に近いが、`core` に近い責務（データモデル）も混在している。

### 将来の方向性

1. **ファサードとしての pme**
   - 外部スクリプト・他アドオンから `pme` 経由でアクセス
   - 内部構造（`preferences`, `pme_types` など）を隠蔽

2. **責務の分離**
   - 実行コンテキスト（`context`）: `infra` 寄り
   - プロパティ定義（`props`, `ParsedData`）: `core` 寄り
   - 将来的に `core/props.py` などに分離する可能性

3. **API の安定化**
   - Stable / Experimental / Internal のラベリング
   - 詳細は `rules/pme_api_plan.md` を参照
