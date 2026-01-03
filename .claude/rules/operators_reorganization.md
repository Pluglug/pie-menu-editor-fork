---
title: Operators Reorganization Plan
phase: 2-C
status: completed
completed_phases: 7/7
last_updated: 2026-01-02
---

# Operators Reorganization Plan

operators/ ディレクトリの整理計画。Phase 2-C の一環として実施。

---

## 目的

巨大な `operators/__init__.py` (3400+ 行) を機能別サブモジュールに分割し、保守性と可読性を向上させる。

---

## 現状分析

### operators/__init__.py の内容 (3400+ 行)

| カテゴリ | クラス数 | 行数 (概算) | リスク |
|----------|---------|-------------|--------|
| Runtime/Modal | 10+ | ~1500 | **HIGH** - 触らない |
| Search | 7+ | ~300 | Low |
| Panel | 2 | ~200 | Low |
| Utility | 10+ | ~500 | Low-Medium |
| Misc | 10+ | ~900 | Medium |

### オペレーターの分布 (ファイル別) - 更新済み

```
operators/__init__.py    : ~20 classes (2588 lines) ← 分割進行中
operators/search.py      : 8 classes (~350 lines) ✅ Phase 1
operators/io.py          : 3 classes (~400 lines) ✅ Phase 2
operators/panel.py       : 2 classes (~200 lines) ✅ Phase 3
operators/utils.py       : 4 classes (~100 lines) ✅ Phase 4
operators/script.py      : 1 class (~90 lines) ✅ Phase 6
operators/hotkey.py      : 3 classes (~75 lines) ✅ Phase 6
operators/extras/        : 16 classes (4 files) ✅ Phase 5
  ├── sidearea.py        : 3 classes
  ├── popup.py           : 6 classes
  ├── area.py            : 2 classes
  └── utils.py           : 5 classes

preferences.py           : 14 classes (IO 移動後)
extra_operators.py       : 薄いラッパー (66 lines)
editors/base.py          : 20 classes (PMI編集)
editors/popup.py         : 16 classes (PDR/PDI操作)
editors/panel_group.py   : 7 classes (パネル操作)
editors/menu.py          : 8 classes (メニュー操作)
keymap_helper.py         : 7 classes (入力状態)
bl_utils.py              : 4 classes (ダイアログ)
```

---

## 分類と移動計画

### Phase 1: Search オペレーター (Low Risk) ✅ 完了

**対象クラス** (移動元: `operators/__init__.py` → 移動先: `operators/search.py`):

| クラス名 | 行番号 | 継承 | 用途 |
|----------|--------|------|------|
| `SearchOperator` | 3072 | - | 基底 mixin |
| `PME_OT_pmi_menu_search` | 3103 | `SearchOperator` | メニュー検索 |
| `PME_OT_pm_search_and_select` | 151 | - | PM 検索・選択 |
| `PME_OT_addonpref_search` | 2404 | - | アドオン設定検索 |
| `PME_OT_pmi_pm_search` | 2618 | - | PMI 内 PM 検索 |
| `PME_OT_pmi_operator_search` | 2669 | - | オペレーター検索 |
| `PME_OT_pmi_panel_search` | 2733 | - | パネル検索 |
| `PME_OT_pmi_area_search` | 2802 | - | エリア検索 |

**移動先**: `operators/search.py`

**依存関係**:
- `SearchOperator` は他の search クラスから継承される
- `get_prefs()`, `lh`, `tag_redraw()` への依存（標準的）
- modal/timer 依存なし

**リスク**: Low

---

### Phase 2: IO オペレーター (Low Risk) ✅ 完了

**対象クラス** (移動元: `preferences.py` → 移動先: `operators/io.py`):

| クラス名 | 行番号 | 継承 | 用途 |
|----------|--------|------|------|
| `WM_OT_pm_import` | 183 | `ImportHelper` | JSON インポート |
| `WM_OT_pm_export` | 472 | `ExportHelper` | JSON エクスポート |
| `PME_OT_backup` | 598 | - | バックアップ |

**依存関係**:
- `infra/io.py` の `read_import_file`, `write_export_file`, `get_user_exports_dir` を使用
- `get_prefs().get_export_data()` への依存
- `fix_json()` (compatibility 関数) への依存
- グローバル変数 (`import_filepath`, `export_filepath`) も `operators/io.py` に移動

**結果**: `preferences.py` が約 400 行削減（3900+ → 3488 行）

---

### Phase 3: Panel オペレーター (Low Risk) ✅ 完了

**対象クラス** (移動元: `operators/__init__.py` → 移動先: `operators/panel.py`):

| クラス名 | 行番号 | 継承 | 用途 |
|----------|--------|------|------|
| `PME_OT_panel_hide` | 223 | - | パネル非表示 |
| `PME_OT_panel_hide_by` | 309 | - | 条件指定でパネル非表示 |

**依存関係**:
- `panel_utils.py` (`hide_panel`, `hidden_panel`, `is_panel_hidden`, `bl_panel_types`, `bl_panel_enum_items`)
- `get_prefs()`, `lh`, `tag_redraw`
- `SPACE_ITEMS`, `REGION_ITEMS` from constants

**結果**: `operators/__init__.py` が約 250 行削減（2996 → 2749 行）

---

### Phase 4: Utility オペレーター (Low-Medium Risk) ✅ 部分完了

**移動済みクラス** (移動元: `operators/__init__.py` → 移動先: `operators/utils.py`):

| クラス名 | 用途 | リスク |
|----------|------|--------|
| `WM_OT_pme_none` | 空オペレーター | Low |
| `PME_OT_preview` | プレビュー | Low |
| `PME_OT_docs` | ドキュメント | Low |
| `PME_OT_debug_mode_toggle` | デバッグモード | Low |

**結果**: `operators/__init__.py` が約 39 行削減（2749 → 2710 行）

---

### Phase 6: Script/Hotkey オペレーター (Low Risk) ✅ 完了

**移動済みクラス** (移動元: `operators/__init__.py`):

#### Step 6-A: Script オペレーター ✅ 完了

**移動先**: `operators/script.py` (~90 lines)

| クラス名 | 用途 | リスク |
|----------|------|--------|
| `PME_OT_script_open` | スクリプト開く | Low |

#### Step 6-B: Hotkey オペレーター ✅ 完了

**移動先**: `operators/hotkey.py` (~75 lines)

| クラス名 | 用途 | リスク |
|----------|------|--------|
| `WM_OT_pme_hotkey_call` | ホットキー呼び出し | Low |
| `PME_OT_pm_chord_add` | コード追加 | Low |
| `PME_OT_pm_hotkey_remove` | ホットキー削除 | Low |

**結果**: `operators/__init__.py` が約 122 行削減（2710 → 2588 行）

---

### 残りの未移動クラス (今後検討)

| クラス名 | 用途 | リスク |
|----------|------|--------|
| `WM_OT_pm_select` | PM 選択 | Low |
| `WM_OT_pme_user_command_exec` | コマンド実行 | Medium |
| `PME_OT_exec` | Python 実行 | Medium |
| `PME_OT_button_add` | ボタン追加 | Medium |

---

### Phase 5: extra_operators.py 完全解体 (Low Risk) ✅ 完了

`extra_operators.py` を完全に解体し、`operators/extras/` サブパッケージに分割した。

**結果**: 1462 行 → 66 行（薄いラッパー）、16 クラスすべて移動完了

#### Step 5-A: Sidebar 系 ✅ 完了

**移動先**: `operators/extras/sidearea.py` (~760 lines)

| クラス名 | 用途 | 状態 |
|----------|------|------|
| `WM_OT_pme_sidebar_toggle` | Sidebar トグル (simple) | ✅ 完了 |
| `PME_OT_sidebar_toggle` | Sidebar トグル (options) | ✅ 完了 |
| `PME_OT_sidearea_toggle` | Side Area トグル (complex) | ✅ 完了 |

#### Step 5-B: Popup 系 ✅ 完了

**移動先**: `operators/extras/popup.py` (~470 lines)

| クラス名 | 用途 | 状態 |
|----------|------|------|
| `PME_OT_popup_property` | プロパティポップアップ | ✅ 完了 |
| `PME_OT_popup_user_preferences` | ユーザー設定ポップアップ | ✅ 完了 |
| `PME_OT_popup_addon_preferences` | アドオン設定ポップアップ | ✅ 完了 |
| `PME_OT_popup_panel` | パネルポップアップ | ✅ 完了 |
| `PME_OT_select_popup_panel` | パネル選択ポップアップ | ✅ 完了 |
| `PME_OT_popup_area` | エリアポップアップ | ✅ 完了 |

**依存**: `PopupOperator` (from `bl_utils`)

#### Step 5-C: Window/Area 系 ✅ 完了

**移動先**: `operators/extras/area.py` (~160 lines)

| クラス名 | 用途 | 状態 |
|----------|------|------|
| `PME_OT_window_auto_close` | ウィンドウ自動クローズ | ✅ 完了 |
| `PME_OT_area_move` | エリア移動 | ✅ 完了 |

#### Step 5-D: Dummy/Utility 系 ✅ 完了

**移動先**: `operators/extras/utils.py` (~125 lines)

| クラス名 | 用途 | 状態 |
|----------|------|------|
| `PME_OT_dummy` | ダミーオペレーター | ✅ 完了 |
| `PME_OT_modal_dummy` | モーダルダミー | ✅ 完了 |
| `PME_OT_none` | 空オペレーター | ✅ 完了 |
| `PME_OT_screen_set` | スクリーン設定 | ✅ 完了 |
| `PME_OT_clipboard_copy` | クリップボードコピー | ✅ 完了 |

**注**: `save_pre_handler`, `register()`, `unregister()` も移動

#### Step 5-E: extra_operators.py 薄いラッパー化 ✅ 完了

`extra_operators.py` は削除せず、後方互換性のための薄いラッパーとして維持。
すべてのクラスを `operators.extras` パッケージから再エクスポート。

**extras/ パッケージ構成**:
```
operators/extras/
├── __init__.py      # パッケージ初期化、全クラスをエクスポート
├── sidearea.py      # Sidebar/SideArea トグル
├── popup.py         # ポップアップ操作
├── area.py          # Window/Area 管理
└── utils.py         # ユーティリティ + ハンドラー
```

---

### 触らない領域 (HIGH RISK)

以下は Phase 3 以降まで変更禁止:

| クラス名 | 行番号 | 理由 |
|----------|--------|------|
| `PME_OT_sticky_key_base` | 507 | modal + timer |
| `PME_OT_sticky_key` | 677 | modal + timer |
| `PME_OT_timeout` | 681 | modal + timer |
| `PME_OT_restore_mouse_pos` | 751 | modal + timer |
| `PME_OT_modal_base` | 825 | modal core |
| `PME_OT_modal_grab` | 1349 | modal |
| `PME_OT_modal` | 1353 | modal |
| `PME_OT_restore_pie_prefs` | 1357 | modal |
| `PME_OT_restore_pie_radius` | 1366 | pie radius |
| `WM_OT_pme_user_pie_menu_call` | 1392 | **runtime core** |
| `WM_OT_pme_user_dialog_call` | 2313 | popup |
| `WM_OT_pme_keyconfig_wait` | 2341 | keyconfig |
| `WM_OT_pmi_submenu_select` | 2373 | submenu |
| `PME_OT_pmi_custom_set` | 2457 | custom PMI |
| `WM_OT_pmidata_hints_show` | 2844 | hints |
| `PME_OT_pmidata_specials_call` | 2894 | specials |

**理由**:
- modal/timer ハンドラーとの密結合
- Blender ライフサイクルへの依存
- Issue #64, #65 の影響範囲

---

## CRUD Base Classes について

**現状**: `infra/collections.py` に配置済み

| クラス名 | 継承元 | 使用箇所 |
|----------|--------|---------|
| `AddItemOperator` | - | `editors/base.py` |
| `MoveItemOperator` | - | `editors/base.py`, `popup.py`, `panel_group.py`, `property.py` |
| `RemoveItemOperator` | `ConfirmBoxHandler` | `editors/base.py` |

**判断**: **移動不要**。既に適切な位置にある。

**理由**:
- `infra/` 層は「Blender API との橋渡し」を担う
- オペレーター mixin は `bpy.props` に依存しており、`infra/` が適切
- 提案された `operators/crud/` への移動はレイヤ違反を招く可能性

---

## 実施手順 (Phase 1: Search オペレーター)

### Step 1: 新ファイル作成

```python
# operators/search.py
"""Search operators for PME."""

LAYER = "operators"

import bpy
from inspect import isclass
from ..addon import get_prefs
from ..ui.layout import lh
from ..ui import tag_redraw, utitle
from ..keymap_helper import to_ui_hotkey


class SearchOperator:
    """Base mixin for search popup operators."""
    use_cache = False
    ...
```

### Step 2: クラス移動

1. `SearchOperator` (基底 mixin)
2. `PME_OT_pmi_menu_search`
3. その他の search オペレーター

### Step 3: 後方互換インポート

```python
# operators/__init__.py (追加)
from .search import (
    SearchOperator,
    PME_OT_pmi_menu_search,
    PME_OT_pm_search_and_select,
    # ...
)
```

### Step 4: テスト

- [x] アドオン有効化でエラーなし
- [x] 検索ダイアログが動作
- [x] `DBG_DEPS=True` で新たな違反なし

**結果**: `operators/__init__.py` が 3400+ 行 → 2996 行に削減（約400行削減）

---

## 最終目標構造

```
operators/
├── __init__.py          # 後方互換エクスポート + register()
├── search.py            # 検索オペレーター
├── io.py                # インポート/エクスポート
├── panel.py             # パネル操作
├── utils.py             # ユーティリティ
└── runtime/             # (Phase 3+) modal/sticky/pie_call
    ├── __init__.py
    ├── modal.py
    ├── sticky.py
    └── pie_call.py
```

**注意**: `runtime/` は Phase 3 以降で実施。現時点では計画のみ。

---

## リスクマトリクス

| 対象 | リスク | 影響範囲 | 実施時期 | 状態 |
|------|--------|---------|---------|------|
| Search operators | Low | 検索 UI のみ | Phase 2-C | ✅ 完了 |
| IO operators | Low-Medium | インポート/エクスポート | Phase 2-C | ✅ 完了 |
| Panel operators | Low | パネル非表示 | Phase 2-C | ✅ 完了 |
| Utility operators (simple) | Low | ユーティリティ | Phase 2-C | ✅ 完了 |
| Utility operators | Medium | 多岐 | Phase 2-C/3 |
| Runtime operators | **HIGH** | 全 Pie 呼び出し | Phase 3+ |

---

## 成功基準

1. **レイヤ違反なし**: `DBG_DEPS=True` で新規違反が発生しない
2. **後方互換性**: 既存の `from .operators import ...` が動作する
3. **テスト通過**: 有効化・基本操作・永続化テスト
4. **ファイルサイズ削減**: `operators/__init__.py` が 2000 行未満に

---

## コードスタイル規約

このリオーガナイズ作業では、以下のスタイル規約に従う。

### Operator クラスの継承

```python
# ✅ 推奨: bpy.types から直接インポート
from bpy.types import Operator

class PME_OT_example(Operator):
    bl_idname = "pme.example"
    ...

# ❌ 使用しない: bpy.types.Operator を直接参照
class PME_OT_example(bpy.types.Operator):
    bl_idname = "pme.example"
    ...
```

### プロパティの定義

```python
# ✅ 推奨: bpy.props から直接インポート
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty

class PME_OT_example(Operator):
    name: StringProperty(options={'SKIP_SAVE'})
    enabled: BoolProperty(default=True)
    mode: EnumProperty(items=ITEMS)

# ❌ 使用しない: bpy.props.* を直接参照
class PME_OT_example(Operator):
    name: bpy.props.StringProperty(options={'SKIP_SAVE'})
```

### 基本方針

**`bpy` モジュールを直接使わない**:
- `bpy.types.*` → `from bpy.types import ...`
- `bpy.props.*` → `from bpy.props import ...`
- `bpy.ops.*` → 例外的に使用可（オペレーター呼び出しは動的）
- `bpy.context`, `bpy.data` → 例外的に使用可（ランタイムアクセス）

**理由**:
- コードがスッキリして読みやすい
- インポートで依存関係が明確になる
- 他の bpy.types クラス（Menu, Panel 等）にも同様に適用可能

### 新規ファイル作成時のテンプレート

```python
# operators/xxx.py - Description
# LAYER = "operators"
#
# Moved from: operators/__init__.py (Phase 2-C operators reorganization)
#
# Contains:
#   - ClassName1: Description
#   - ClassName2: Description
#
# pyright: reportInvalidTypeForm=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

LAYER = "operators"

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty

from ..addon import get_prefs
...
```

**pyright 抑制の理由**:
- `reportInvalidTypeForm`: Blender のプロパティアノテーションは標準の型ヒントと異なる
- `reportIncompatibleMethodOverride`: オペレーターのメソッドシグネチャが Blender の仕様に従う
- `reportAttributeAccessIssue`: Blender の動的属性アクセス
- `reportOptionalMemberAccess`: `bpy.context` のオプショナルメンバー

---

## 参照

- `rules/architecture.md` — レイヤ構造
- `rules/milestones.md` — フェーズ計画
- `rules/dependency_cleanup_plan.md` — 違反クリーンアップ
- `infra/collections.py` — CRUD base classes
