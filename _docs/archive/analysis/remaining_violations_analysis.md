---
title: Remaining Layer Violations - Essential Problems Analysis
phase: RC Preparation
status: analysis
created: 2026-01-04
last_updated: 2026-01-04
---

# 残存レイヤ違反の本質的問題分析

Phase 5-B, 7 完了後、12 件のレイヤ違反が残存している。
このドキュメントでは各違反の本質的な問題を分析し、解決アプローチを整理する。

---

## 現在の違反一覧 (12件)

```
core <- infra : props imports debug
core <- infra : constants imports previews_helper
infra <- ui : bl_utils imports screen
infra <- ui : base imports screen
infra <- ui : pme_types imports utils
infra <- ui : base imports utils
infra <- operators : base imports ed
infra <- operators : popup imports operators
infra <- operators : pme_types imports operators
infra <- operators : base imports operators
ui <- operators : utils imports operators
editors <- operators : panel_group imports operators
```

---

## 分析1: props → debug 違反

### 現状
```python
# core/props.py (LAYER = "core")
from ..infra.debug import logw, DBG_RUNTIME
```

### 本質的問題

**debug は core に置くべきか？**

`infra/debug.py` の内容を分析すると:

| 機能 | Blender 依存 | 用途 |
|------|-------------|------|
| `logw`, `logi`, `loge` | なし | 汎用ログ出力 |
| `DBG_*` フラグ | なし | 機能トグル |
| `DependencyGraphLogger` | なし | モジュールロード順序可視化 |
| `detect_layer_violations` | `sys.modules` のみ | レイヤ違反検出 |
| `_LAYER_ORDER` | なし | レイヤ定義 |

**結論: debug.py は pure Python だが「core」ではない**

理由:
1. **責務**: ローダーとモジュールシステムの観測ツール = インフラ関心
2. **`_LAYER_ORDER`**: レイヤ構造はビジネスロジックではなくアーキテクチャ関心
3. **`DependencyGraphLogger`**: モジュール依存解析 = ローダーインフラ

debug.py を core に移動しても本質的に不適切。props.py の debug import は「許容される違反」として文書化が妥当。

### 対応方針

**許容**: props.py の NOTE コメントで既に説明済み

```python
# NOTE: This is a pragmatic layer violation (core → infra) for debug logging.
# infra/debug.py is pure Python and has no heavy dependencies.
```

---

## 分析2: constants → previews_helper 違反

### 現状
```python
# core/constants.py (LAYER = "core")
from ..previews_helper import ph
```

### 本質的問題

**Issue #65 との関連**

`OPEN_MODE_ITEMS` は EnumProperty の `items` に使用されるが:
1. アイコンを `ph.icon()` で動的取得
2. **Reload Scripts 時にアイコンが更新されない**

これは単なる LAYER 問題ではなく、設計問題:
- EnumProperty の `items` はモジュールロード時に評価される
- Reload Scripts 後、`ph` が再初期化されてもタプル内のアイコン ID は古いまま

### 対応方針

**Issue #65 で根本解決が必要** (保留)

- EnumProperty の items を静的タプル → 動的コールバックに変更
- constants.py から previews_helper 依存を削除
- RC 以降で対応

---

## 分析3: _draw_item メソッド参照 - 設計問題

### 現状
```python
# editors/panel_group.py (LAYER = "editors")
from ..operators import WM_OT_pme_user_pie_menu_call
# ...
WM_OT_pme_user_pie_menu_call._draw_item(pr, pm, pmi, idx)
```

同様の参照:
- `ui/utils.py`: `WM_OT_pme_user_pie_menu_call._draw_item`
- `pme_types.py`: `WM_OT_pme_user_pie_menu_call` import

### 本質的問題

**`_draw_item` は本当にオペレーターの責務か？**

`_draw_item` メソッドの機能:
1. PMI (Pie Menu Item) を UI に描画
2. アイコン、ラベル、オペレーター呼び出しの処理
3. 複数の場所から共有利用される

**これは設計上の問題**:
- `_draw_item` は「オペレーター」ではなく「UI 描画ロジック」
- オペレータークラスに置かれているのは歴史的経緯
- 理想的には `ui/` レイヤに分離すべき

### 解決アプローチ

**Phase 7-B (将来): _draw_item の分離**

```
現状:
  operators/user_call.py::WM_OT_pme_user_pie_menu_call._draw_item

理想:
  ui/item_drawing.py::draw_pmi_item()
```

分離のメリット:
- `editors → operators` 違反が解消
- `ui → operators` 違反が解消
- 責務の明確化

分離のリスク:
- `_draw_item` は `self.invoke_mode` など operator 状態を参照する可能性
- WM_OT_pme_user_pie_menu_call との結合度を調査必要

### 対応方針

**RC では許容、v2.1.0 以降で分離検討**

---

## 分析4: infra → ui 違反 (screen/utils)

### 現状
```python
# bl_utils.py (LAYER = "infra")
from .ui.screen import get_override_args

# pme_types.py (LAYER = "infra")
from .ui import utils as UU
```

### 本質的問題

**screen.py/utils.py の責務が混在している**

`ui/screen.py` の内容:

| 関数 | 実際のレイヤ | 依存 |
|------|-------------|------|
| `find_area`, `find_region` | infra | bpy のみ |
| `get_override_args` | infra | bpy のみ |
| `ContextOverride` | infra | bpy のみ |
| `focus_area` | ui | `pme.context` |
| `override_context` | ui | `bl_context` |
| `exec_with_override` | ui | `pme.context` |

`ui/utils.py` の内容:

| 関数/クラス | 実際のレイヤ | 依存 |
|------------|-------------|------|
| `WM_MT_pme` | ui | `WM_OT_pme_user_pie_menu_call._draw_item` |
| `execute_script` | ui | `pme.context.gen_globals()` |
| `draw_menu`, `open_menu` | ui | `WM_OT_pme_user_pie_menu_call`, `pme.context` |

**問題の本質: モジュールが正しいレイヤに分割されていない**

screen.py は「infra 関数」と「ui 関数」が混在しており、
bl_utils.py が infra 関数だけを使いたくても ui レイヤ全体を import することになる。

### 解決アプローチ

**Phase 8 (将来): screen.py の分割**

```
現状:
  ui/screen.py (LAYER = "ui")

理想:
  infra/context_override.py (LAYER = "infra")
    - find_area, find_region, find_window, find_screen
    - ContextOverride, get_override_args

  ui/screen.py (LAYER = "ui")
    - focus_area, override_context
    - exec_with_override
```

### 対応方針

**RC では許容、v2.1.0 以降で分割検討**

---

## 分析5: infra → operators 違反

### 現状
```python
# infra/base.py (LAYER = "infra") - 存在しない模様
# popup.py (LAYER = ?)
from ..operators import ...

# pme_types.py (LAYER = "infra")
from .operators import WM_OT_pme_user_pie_menu_call
```

### 本質的問題

これらは **ランタイム依存** であり、分離困難:
- popup がオペレーターを呼び出す必要がある
- pme_types が描画にオペレーターメソッドを使用

### 対応方針

**許容**: ランタイム依存として文書化

---

## 許容リスト (RC 時点)

| 違反 | 理由 | 対応時期 |
|------|------|---------|
| `props → debug` | デバッグ用、NOTE 済み | 許容 |
| `constants → previews_helper` | Issue #65 で根本解決 | v2.1.0+ |
| `bl_utils → screen` | screen.py 分割で解決可能 | v2.1.0+ |
| `base → screen` | 同上 | v2.1.0+ |
| `pme_types → utils` | utils.py 分割で解決可能 | v2.1.0+ |
| `base → utils` | 同上 | v2.1.0+ |
| `base → ed` | ランタイム依存 | 許容 |
| `popup → operators` | ランタイム依存 | 許容 |
| `pme_types → operators` | _draw_item 分離で解決可能 | v2.1.0+ |
| `base → operators` | ランタイム依存 | 許容 |
| `utils → operators` | _draw_item 分離で解決可能 | v2.1.0+ |
| `panel_group → operators` | _draw_item 分離で解決可能 | v2.1.0+ |

---

## まとめ: 3 つの本質的問題

### 1. `_draw_item` の配置問題
- オペレーターに置かれた UI 描画ロジック
- 分離すれば 3〜4 件の違反が解消

### 2. `screen.py`/`utils.py` の責務混在
- infra 関数と ui 関数が同一モジュールに存在
- 分割すれば 4 件程度の違反が解消

### 3. ランタイム依存
- popup/base がオペレーターを呼び出す必要
- これは許容するしかない

### RC 目標

- 現在 12 件 < 30 件 ✅
- 全件を「許容」または「将来対応」として文書化
- 旧ローダー削除後、安定版リリース可能

---

## 参照

- `@_docs/guides/rc_roadmap.md` — RC ロードマップ
- `@.claude/rules/milestones.md` — マイルストーン
- `@_docs/design/core-layer/ideal-architecture.md` — 理想アーキテクチャ
