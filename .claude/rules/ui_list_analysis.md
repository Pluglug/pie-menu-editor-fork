# UI List / TreeView 分析

Phase 2-A の観測結果。UIList / TreeView 系クラスの責務と依存関係を整理する。

---

## 対象クラス一覧

| クラス名 | 所在 | 継承元 | 用途 |
|---------|------|--------|------|
| `WM_UL_panel_list` | `preferences.py:1129` | `bpy.types.UIList` | HPANEL モードでのパネル一覧表示 |
| `WM_UL_pm_list` | `preferences.py:1155` | `bpy.types.UIList` | PM リスト表示（リストビュー） |
| `PME_UL_pm_tree` | `preferences.py:1264` | `bpy.types.UIList` | PM ツリー表示（グループ化対応） |
| `TreeView` | `preferences.py:2130` | なし | `PME_UL_pm_tree` のヘルパークラス |

---

## 各クラスの責務と依存

### 1. `WM_UL_panel_list`

**責務**: パネル一覧の描画

**依存先**:
```
WM_UL_panel_list
  ├── get_prefs()          → prefs (addon.py)
  ├── hidden_panel()       → bl_utils.py (infra)
  └── ic()                 → addon.py (prefs)
```

**レイヤ違反**: なし（ui → prefs は許容）

**責務分離の可能性**:
- `hidden_panel()` は Blender API ラッパーであり、`infra` 層に属する
- `get_prefs()` への依存は避けられない（表示設定の読み取り）

---

### 2. `WM_UL_pm_list`

**責務**: PM リストの描画、フィルタリング、ソート

**依存先**:
```
WM_UL_pm_list
  ├── get_prefs()          → prefs (addon.py)
  ├── lh (LayoutHelper)    → ui/layout.py (ui)
  ├── to_ui_hotkey()       → ? (utils)
  ├── ic_cb()              → addon.py (prefs)
  └── CC (constants)       → core/constants.py (core)
```

**メソッド別責務**:

| メソッド | 責務 | データアクセス |
|---------|------|---------------|
| `draw_filter()` | フィルタ UI の描画 | `pr.list_size`, `pr.num_list_rows` |
| `draw_item()` | 各 PM アイテムの描画 | `pm.enabled`, `pm.label`, `pm.tag`, `pm.km_name` |
| `filter_items()` | フィルタリングロジック | `pm.filter_list(pr)` |

**問題点**:
- `draw_item()` 内で `pm.ed.icon` にアクセス（Editor オブジェクトへの参照）
- `filter_items()` で `pm.filter_list(pr)` を呼び出し（Model にロジックが混在）
- `lh` (LayoutHelper) を直接使用（グローバルインスタンス）

**レイヤ違反**:
- `WM_UL_pm_list → PMItem.ed → EditorBase` (ui → editors)

---

### 3. `PME_UL_pm_tree`

**責務**: PM ツリーの描画、グループ化、状態管理、永続化

**依存先**:
```
PME_UL_pm_tree
  ├── get_prefs()          → prefs (addon.py)
  ├── temp_prefs()         → prefs (addon.py)
  ├── CC (constants)       → core/constants.py (core)
  ├── os, json             → stdlib
  ├── ADDON_PATH           → constants (core)
  └── logh() (DBG_TREE)    → infra/debug.py (infra)
```

**クラス変数（状態）**:
```python
locked = False                 # ツリー更新のロック
groups = []                    # グループ名のリスト
collapsed_groups = set()       # 折りたたまれたグループ
expanded_folders = set()       # 展開されたフォルダ
has_folders = False            # フォルダを持つか
```

**メソッド別責務**:

| メソッド | 責務 | データアクセス | 問題 |
|---------|------|---------------|------|
| `save_state()` | ツリー状態の永続化 | ファイル I/O | **高リスク**: ファイル書き込み |
| `load_state()` | ツリー状態の復元 | ファイル I/O, `pr.group_by` | **高リスク**: ファイル読み込み |
| `link_is_collapsed()` | フォルダ展開状態チェック | `expanded_folders` | 純粋なロジック |
| `update_tree()` | ツリー構造の更新 | `tpr.links`, 多数のフィールド | **超高リスク**: 複雑なロジック |

**問題点**:
1. **状態管理がクラス変数**: `collapsed_groups`, `expanded_folders` がクラス変数
   - テストが困難
   - Reload 時に状態が残る/消えるの制御が難しい

2. **永続化ロジックが混在**: `save_state()` / `load_state()` が UIList 内にある
   - ファイル I/O と UI 描画が密結合
   - 本来は別のサービスクラスに分離すべき

3. **`update_tree()` の複雑さ**: 250 行以上の巨大メソッド（推定）
   - グループ化、リンク構築、フィルタリングが一体化
   - 分割・テストが非常に困難

**レイヤ違反**:
- `PME_UL_pm_tree → temp_prefs().links` (ui → prefs の内部データ)
- `PME_UL_pm_tree → pr.pie_menus` (ui → prefs のコレクション)
- `PME_UL_pm_tree → file I/O` (ui 層でのファイル操作)

---

### 4. `TreeView`

**責務**: `PME_UL_pm_tree` の薄いラッパー

**依存先**:
```
TreeView
  └── PME_UL_pm_tree (直接参照)
```

**メソッド**:
```python
def expand_km(self, name)    # グループを展開
def lock(self)               # ロック
def unlock(self)             # アンロック
def update(self)             # ツリー更新
```

**問題点**:
- `PME_UL_pm_tree` のクラス変数を直接操作
- ファサードというより、単なる委譲

---

## 依存関係図

```
┌─────────────────────────────────────────────────────────────┐
│                          prefs 層                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ PMEPreferences                                        │  │
│  │   ├── pie_menus: Collection[PMItem]                   │  │
│  │   ├── tree: TreeView                                  │  │
│  │   └── 各種設定 (list_size, group_by, etc.)            │  │
│  └──────────────────────────────────────────────────────┘  │
│                              ▲                              │
│                              │ get_prefs()                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ WM_UL_pm_list      (UI 描画)                         │  │
│  │ WM_UL_panel_list   (UI 描画)                         │  │
│  │ PME_UL_pm_tree     (UI 描画 + 状態管理 + 永続化)     │  │
│  │ TreeView           (薄いラッパー)                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                          ui 層                              │
│  lh (LayoutHelper)                                          │
│  tag_redraw()                                               │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         infra 層                            │
│  hidden_panel()                                             │
│  logh() (DBG_TREE)                                          │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                          core 層                            │
│  CC (constants)                                             │
│  ADDON_PATH                                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## UI とデータの密結合箇所

### 1. `WM_UL_pm_list.draw_item()` での Editor アクセス

```python
# preferences.py:1183
lh.label("", item.ed.icon)
```

- `item` は `PMItem`
- `item.ed` は `EditorBase` サブクラスのインスタンス
- UI 層から Editor 層への直接アクセス

**改善案**:
- `PMItem` に `icon` プロパティを追加し、`ed.icon` を隠蔽
- または `EditorBase` に `get_icon(pm)` メソッドを追加

### 2. `PME_UL_pm_tree` のクラス変数状態

```python
# preferences.py:1265-1270
class PME_UL_pm_tree(bpy.types.UIList):
    locked = False
    groups = []
    collapsed_groups = set()
    expanded_folders = set()
    has_folders = False
```

- クラス変数として状態を保持
- UIList のライフサイクルと状態のライフサイクルが分離されていない

**改善案**:
- 状態を `PMEPreferences` または別の StateManager クラスに移動
- `PME_UL_pm_tree` は純粋な UI 描画のみを担当

### 3. `PME_UL_pm_tree.save_state()` のファイル I/O

```python
# preferences.py:1272-1290
@staticmethod
def save_state():
    pr = get_prefs()
    path = os.path.join(ADDON_PATH, "data", "tree.json")
    # ... ファイル書き込み
```

- UIList がファイル I/O を直接実行
- 本来は infra 層のサービスに委譲すべき

**改善案**:
- `infra/persistence.py` などに `TreeStatePersistence` クラスを作成
- `PME_UL_pm_tree` はイベントを発火するだけ

---

## Phase 2-B 以降の改善候補

### 優先度: 高

1. **`PME_UL_pm_tree` のクラス変数状態を分離**
   - 状態を `TreeState` クラスに抽出
   - `PMEPreferences.tree_state` として保持
   - リスク: 中（既存動作への影響あり）

### 優先度: 中

2. **ファイル I/O を infra 層に移動**
   - `save_state()` / `load_state()` のロジックを分離
   - リスク: 低（純粋なリファクタリング）

3. **`WM_UL_pm_list` の Editor 依存を解消**
   - `PMItem.icon` プロパティを追加
   - リスク: 低

### 優先度: 低

4. **`lh` グローバルインスタンスの依存注入化**
   - テスト容易性の向上
   - リスク: 低（純粋なリファクタリング）
   - 影響範囲: 広い

---

## 現状維持すべき箇所

- `WM_UL_panel_list`: シンプルで問題なし
- `WM_UL_pm_list` の基本構造: 複雑さは許容範囲
- UIList と `PMEPreferences` の基本的な関係: Blender の設計に沿っている

---

## 参照

- `preferences.py`: UIList の実装
- `pme_types.py`: `PMItem`, `PMIItem` の定義
- `editors/base.py`: `EditorBase` の定義
- `rules/architecture.md`: レイヤ構造の定義
