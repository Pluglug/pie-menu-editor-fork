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

## 3. モジュールローダー移行

### 現状（PME1 方式）

```python
# __init__.py
MODULES = ("addon", "pme", "c_utils", ...)  # 手動順序
get_classes()  # PropertyGroup 依存を解決
```

### 目標（PME2 方式）

```python
# __init__.py
from . import addon

def register():
    addon.init_addon(
        module_patterns=["core.*", "infra.*", "ui.*", "editors.*", "operators.*", "prefs.*"],
        use_reload="pie_menu_editor" in sys.modules,
    )
    addon.register_modules()
```

### `init_addon()` の処理フロー

1. `module_patterns` に基づいてモジュールを収集
2. 各モジュールをロード（必要に応じてリロード）
3. import 文と PropertyGroup 依存を解析
4. トポロジカルソートでロード順序を決定
5. `MODULE_NAMES` に格納

### `force_order` の扱い

- **デバッグ専用**：循環依存で詰んだときの逃げ道
- `pme2-dev` にマージする前に必ず **空にする**
- `force_order` が空でない = 設計負債

## 4. 現状のフラット構造からの移行

### Phase 1: 安全なファイルから移動

| 対象 | 移動先 | リスク |
|------|--------|--------|
| `overlay.py` | `infra/overlay.py` | 低（描画のみ、依存少） |
| `layout_helper.py` | `ui/layout.py` | 低（レイアウトヘルパー） |
| `ed_*.py` | `editors/` | 中（EditorBase との依存） |

### Phase 2: 依存の多いファイル

| 対象 | 移動先 | リスク |
|------|--------|--------|
| `operators.py` | `operators/` | 高（巨大、依存多） |
| `preferences.py` | `prefs/` | 高（全体のハブ） |

### 移動手順

1. 新ディレクトリに `__init__.py` を作成
2. 対象クラス/関数を新ファイルにコピー
3. 旧ファイルから `from .new_location import SomeClass` で再エクスポート
4. テスト通過後、旧ファイルの実装を削除
