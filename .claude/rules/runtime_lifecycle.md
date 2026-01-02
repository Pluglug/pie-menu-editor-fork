# Runtime Lifecycle Design (Phase 3)

PME2 のライフサイクル問題の分析と解決計画。

---

## ⚠️ 現在のステータス (2026-01-02)

**`use_reload` パターンは一時的に無効化されています。**

### 試行結果

Sprint 0/0.1 で以下を達成：
- ✅ `pme_types.py` の古いインスタンス参照問題を修正
- ✅ `_FALLBACK_DEFAULTS` に不足プロパティを追加
- ✅ PROPERTY モードの描画クラッシュガードを追加

しかし、複雑なユーザー設定環境では **C レベルクラッシュ** が発生：
- CUSTOM スクリプトが無効な Blender 状態にアクセス
- UserProperties の動的プロパティ再登録の失敗
- Python の try-except では捕捉不可能

### 決定事項

`use_reload` パターンを **Phase 3 完了まで無効化**：
- `__init__.py` で `use_reload = False` に設定
- 根本的なライフサイクル設計が必要
- **Issue #67** で追跡: https://github.com/Pluglug/pie-menu-editor-fork/issues/67

### 残存する問題

| 問題 | 影響 | 対策 |
|------|------|------|
| CUSTOM スクリプトの C レベルクラッシュ | Reload Scripts 後にクラッシュ | Phase 3 で対処 |
| UserProperties 動的プロパティ | 再登録タイミング | Phase 3 で対処 |
| `_FALLBACK_DEFAULTS` の保守 | 新プロパティ追加時に更新が必要 | 根本解決が必要 |

---

## 目的

Blender アドオンには 3 つのライフサイクルシナリオがある：

| シナリオ | 発生条件 | 期待される動作 |
|----------|---------|---------------|
| **Reload Scripts** | F3 → Reload Scripts | 全機能が動作継続 |
| **ON/OFF 切り替え** | Preferences でアドオン有効化/無効化 | クリーンな再登録 |
| **Blender 再起動** | Blender を閉じて再起動 | 設定が永続化されている |

**Phase 3 のゴール**: 上記 3 シナリオすべてでエラーなく動作すること。

---

## 現状の問題（Reload Scripts 後の失敗）

### 失敗ログの要約

```
Reload Scripts 後の再 Register:
  - 186 classes registered（初回 178 → 8 増加）
  - 67 modules 中 66 は初期化成功
  - preferences モジュールだけが init 失敗

失敗の直接原因:
  preferences.register()
    → pr.init_menus()
      → editors.property.init_pm(pm)
        → register_user_property(pm)
          → pm.get_data("vector")
            → pp.parse(self.data)
              → ParsedData.__getattr__("vector")
                → AttributeError: 'ParsedData' object has no attribute 'vector'
```

### 問題の構造

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔴 問題 0: pme_types.py の古いインスタンス参照（根本原因）     │
├─────────────────────────────────────────────────────────────────┤
│ - pme_types.py:19 で `from .pme import props as pp` と定義     │
│ - Reload 時、pme.py がリロードされ新しい props インスタンス作成│
│ - しかし pme_types.py の pp は古いインスタンスを参照し続ける   │
│ - editors/property.py は新しい pme.props に vector を登録      │
│ - pm.get_data() → pp.parse() → 古い prop_map → AttributeError  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 問題 1: props 登録タイミング                                    │
├─────────────────────────────────────────────────────────────────┤
│ - pme.props.*Property() がモジュールレベルで呼ばれる            │
│ - Reload 後、prop_map の状態が不整合                           │
│ - "vector" が prop_map に登録される前に参照される              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 問題 2: 初期化順序                                              │
├─────────────────────────────────────────────────────────────────┤
│ - preferences.init_menus() が先に走る                          │
│ - editors/property.py の props 登録が後                        │
│ - → "vector" が見つからない                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 問題 3: クラス重複登録 (178 → 186)                             │
├─────────────────────────────────────────────────────────────────┤
│ - 一部クラスが unregister で完全にクリアされていない           │
│ - "has been registered before" 警告                            │
│ - 対象: WM_OT_pme_user_pie_menu_call, PME_OT_exec, etc.        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 問題 4: 循環依存                                                │
├─────────────────────────────────────────────────────────────────┤
│ - preferences → operators.io → preferences                     │
│ - topological sort 失敗 → alternative sort                     │
│ - ロード順序が不安定になる可能性                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 根本原因の詳細分析

### 問題 0: `pme_types.py` の古いインスタンス参照

**発見箇所**: `pme_types.py:19`

```python
from .pme import props as pp  # ← ここで古いインスタンスをキャッシュ
```

**Reload 時のシーケンス**:

```
1. pme.py がリロード
   └── props = PMEProps() ← 新しいインスタンス作成
   └── prop_map = {} ← 空の辞書

2. pme_types.py はリロードされない（または古い参照を保持）
   └── pp は古い pme.props を参照

3. editors/property.py がリロード
   └── pme.props.IntProperty("prop", "vector", 1)
   └── 新しい pme.props.prop_map に登録

4. preferences.register() が呼ばれる
   └── pr.init_menus()
   └── pm.ed.init_pm(pm) [editors/property.py の Editor]
   └── register_user_property(pm)
   └── pm.get_data("vector")
   └── pp.parse(self.data) ← pp は古いインスタンス！
   └── 古い prop_map には vector がない
   └── AttributeError
```

**図解**:

```
初回ロード後:
  pme.props ─────────────┐
                         ├──→ prop_map: {vector: PMEProp(...), ...}
  pme_types.pp ──────────┘

Reload 後:
  pme.props (新) ────────────→ prop_map: {vector: PMEProp(...), ...}

  pme_types.pp (古) ─────────→ prop_map: {} ← 空！

  pm.get_data("vector")
    └── pp.parse() ← 古い pp を使用
    └── vector が見つからない → AttributeError
```

---

## props 登録箇所一覧

### モジュールレベルで登録されているプロパティ

| ファイル | type | プロパティ |
|---------|------|-----------|
| `editors/pie_menu.py:15-18` | `pm` | `pm_radius`, `pm_confirm`, `pm_threshold`, `pm_flick` |
| `editors/menu.py:600` | `rm` | `rm_title` |
| `editors/popup.py:1649-1706` | `row`, `pd` | `layout`, `width`, `poll`, `fixed_col`, `fixed_but`, `align`, `column`, `pd_row`, `pd_box`, `pd_panel`, `pd_expand` |
| `editors/panel_group.py:683-687` | `pg` | `pg_wicons`, `pg_context`, `pg_category`, `pg_space`, `pg_region` |
| `ed_modal.py:25-27` | `mo` | `confirm`, `block_ui`, `lock` |
| `ed_stack_key.py:5-6` | `s` | `s_undo`, `s_state` |
| `ed_sticky_key.py:48` | `sk` | `sk_block_ui` |
| **`editors/property.py`** | `prop` | **`vector`, etc.** ← 要調査 |

### 問題のメカニズム

```python
# 現状: モジュールレベルで登録
# editors/pie_menu.py
pme.props.IntProperty("pm", "pm_radius", -1)  # import 時に実行

class Editor(EditorBase):
    ...

# Reload 後の問題:
# 1. pme.props.prop_map がクリアされる（または不完全）
# 2. editors/property.py が import される前に
# 3. preferences.init_menus() が pm.get_data("vector") を呼ぶ
# 4. → AttributeError
```

---

## 解決アプローチ

### アプローチ D: pp 参照を動的にする（🔴 最優先・最小変更）

**根本原因である問題 0 を直接解決する。**

```python
# Before: pme_types.py:19
from .pme import props as pp  # ← 古いインスタンスをキャッシュ

# After: pme_types.py
from . import pme  # pme モジュールを import

# 使用箇所で pme.props を直接参照
def get_data(self, key):
    value = getattr(pme.props.parse(self.data), key)  # pp → pme.props
    return value
```

**メリット**:
- 根本原因を直接解決
- 変更箇所が最小限（pme_types.py のみ）
- 常に最新の pme.props インスタンスを参照

**デメリット**:
- pme_types.py 内の pp 使用箇所を全て修正する必要
- パフォーマンスへの影響は軽微（属性アクセスのオーバーヘッド）

**変更対象**: `pme_types.py` の `pp` 使用箇所（約 3-4 箇所）

---

### アプローチ A: props 登録を register() に移動（推奨）

```python
# Before: モジュールレベル
pme.props.IntProperty("pm", "pm_radius", -1)

class Editor(EditorBase):
    ...

# After: register() 内で登録
class Editor(EditorBase):
    ...

def register():
    pme.props.IntProperty("pm", "pm_radius", -1)
    # ...
```

**メリット**:
- 登録タイミングが明確
- unregister() で対応するクリア処理が書ける
- Blender のライフサイクルに沿った設計

**デメリット**:
- 全 Editor ファイルの修正が必要
- 既存コードへの影響範囲が大きい

### アプローチ B: props 登録順序の保証（暫定）

```python
# addon.py の register_modules() で
# props 登録を含むモジュールを最初に初期化

def register_modules():
    # Phase 1: props 登録（Editor モジュール）
    for mod in EDITOR_MODULES:
        mod.register()

    # Phase 2: preferences 初期化
    preferences.register()
```

**メリット**:
- コード変更が最小限
- 既存構造を維持

**デメリット**:
- 順序依存が暗黙的
- 将来の変更で壊れやすい

### アプローチ C: ParsedData の遅延評価（フォールバック強化）

```python
# pme.py の ParsedData.__getattr__ を強化
def __getattr__(self, name):
    # prop_map から動的に解決を試みる
    prop = props.get(name)
    if prop and prop.type == self.type:
        return prop.default

    # 見つからない場合は警告 + デフォルト値
    logh("WARN", f"Unknown prop: {name}")
    return None  # または型推測
```

**メリット**:
- 既存コードへの影響なし
- 即座に適用可能

**デメリット**:
- 根本解決ではない
- デバッグが困難になる可能性

---

## 実装計画

### Sprint 0: 根本原因の修正（🔴 最優先）✅ 完了

| # | タスク | リスク | 状態 |
|---|--------|--------|------|
| 0.1 | `pme_types.py` の `pp` 使用箇所を特定 | Low | ✅ 完了 |
| 0.2 | `from .pme import props as pp` を削除 | Low | ✅ 完了 |
| 0.3 | `pp.xxx` を `pme.props.xxx` に置換（15 箇所） | Low | ✅ 完了 |
| 0.4 | `_FALLBACK_DEFAULTS` に `vector` 等を追加 | Low | ✅ 完了 |
| 0.5 | Reload Scripts テスト | - | ✅ 完了 |

**コミット**: `2b0704d` - Fix Reload Scripts failure: use pme.props instead of cached pp

---

### Sprint 0.1: ユーザープロパティ防御策 ✅ 完了

Reload Scripts テスト中に発見された新規問題への対応。

**問題**: `graph view prop` という user property の EnumProperty 定義が破損
- `ENUM_FLAG` が無効なのに `default` が `set` 型
- `TypeError: default option must be a 'str' or 'int' type when ENUM_FLAG is disabled`

| # | タスク | リスク | 状態 |
|---|--------|--------|------|
| 0.1.1 | `register_user_property()` に EnumProperty default サニタイズ追加 | Low | ✅ 完了 |
| 0.1.2 | プロパティ登録を try/except でガード | Low | ✅ 完了 |
| 0.1.3 | `late-bound prop` 警告を `DBG_RUNTIME` のみに制限 | Low | ✅ 完了 |

**変更ファイル**:
- `editors/property.py`: サニタイズロジック + try/except ガード
- `pme.py`: 警告を `DBG_RUNTIME and logw(...)` に変更

---

### Sprint 1: Runtime Lifecycle / Reload-safe behavior ⏳ 進行中

Sprint 0/0.1 で「Reload Scripts で落ちない」という最低ラインをクリア。
Sprint 1 では残りの構造問題を調査し、ユーザー体験を完全にするためのタスクに取り組む。

| # | タスク | 成果物 | 状態 |
|---|--------|--------|------|
| 1.1 | `editors/property.py` の props 登録箇所を特定 | 登録一覧 | ✅ 完了 |
| 1.2 | `preferences.init_menus()` の呼び出しフロー追跡 | シーケンス図 | ✅ 完了 |
| 1.3 | 循環依存 `preferences ↔ operators.io` の原因特定 | 依存グラフ | ✅ 完了 |
| 1.4 | クラス重複登録（178 → 186）の原因特定 | 重複クラス一覧 | ⏳ 次のタスク |
| 1.5 | **previews_helper reload-safe 化** | ライフサイクル設計 | ⏳ 次のタスク |

---

#### 1.3 循環依存の原因特定 ✅ 解決済み

**原因**:
```
preferences.py:104     → from .operators.io import (...)  [モジュールレベル]
operators/io.py:316    → from ..preferences import PME_UL_pm_tree  [関数内遅延]
```

**解決策**: `addon.py` の `_analyze_imports()` を改善

関数スコープ内の import（遅延インポート）を依存検出から除外：
- `visit_FunctionDef` / `visit_AsyncFunctionDef` で `function_depth` をトラッキング
- `function_depth > 0` の場合、import を依存としてカウントしない

**設計理由**:
- モジュールレベル import = **ロード時依存**（循環するとエラー）
- 関数内 import = **ランタイム依存**（呼び出し時に解決、循環しても OK）

**結果**:
- `preferences → operators.io`: ✅ 検出される（正常な依存方向）
- `operators.io → preferences`: ❌ 検出されない（関数内遅延インポート）
- 循環警告が消える

---

#### 1.4 クラス重複登録の原因特定

**目的**: どのクラスが「二度目の register_class(..., unregistering previous)」を引き起こしているかを特定。

**対象クラス（ログから）**:
- `WM_OT_pme_user_pie_menu_call`
- `WM_OT_pm_select`
- `PME_OT_exec`
- `PME_OT_input_box`
- `PME_OT_message_box`

**ゴール**:
- 原因が以下のどれかを明確化:
  - a) 旧 PME1 時代の register/unregister の設計ミス
  - b) PME2 Loader の import 戦略
  - c) 双方のミスマッチ
- 「必ず直す」までやらなくても、「どこの責任レイヤか」を明確にする

---

#### 1.5 previews_helper reload-safe 化（カスタムアイコンの根本解決）

**関連 Issue**: #65, #62, #57
**関連コミット**: `a0d5aba` (Fix custom icon lifecycle and prefs #57)

**背景**:
- Sprint 0/0.1 で Reload Scripts 自体は通るようになった
- しかし「カスタムアイコンが再登録できない」という UX 的に致命的な傷が残る
- Lifecycle フェーズの完了条件として「カスタムアイコンが普通に使える」を含めるべき

**スコープ**:

1. **現状把握**
   - `previews_helper.py` がどのタイミングで preview コレクションを作成/破棄しているか整理
   - `bpy.utils.previews.new()` / `remove()` の呼び出し箇所
   - 依存違反: `core.constants imports previews_helper` の影響評価

2. **ライフサイクル設計**
   - インバリアントを決定:
     - PME enable / Reload Scripts / PME disable-enable を何度やっても:
       - 「ユーザーが設定した custom icon 定義」は消えない（prefs / data として保持）
       - 「preview キャッシュ」は必要な時に再構築される揮発的なもの
   - PME2 Loader のフックに合わせた管理:
     - `register_modules.init` で preview コレクションを作り直す
     - `unregister_modules.uninit` で確実に `remove()` する

3. **実装**
   - 既存ホットフィックス（`a0d5aba`）の評価と改善
   - `init_previews()` / `clear_previews()` のペアで管理する形にリプレイス
   - Reload Scripts シナリオのテスト:
     - 通常起動 → custom icon 登録 → Reload Scripts → icon が使える
     - PME disable → enable → icon 生存

4. **ドキュメント**
   - 本ドキュメントに previews_helper のライフサイクル図を追加
   - 「Reload Scripts を前提とした custom icon の保証範囲」を明記

**受け入れ条件**:
- [ ] Reload Scripts 実行後も、ユーザー定義 custom icon が再起動なしで機能する
- [ ] custom icon 周りのエラーでアドオン全体が register 失敗しない
- [ ] previews_helper の preview コレクションは register/unregister で必ず作成/破棄される
- [ ] 既存のホットフィックスコードは削除または明確に位置づけられている

---

### Sprint 2: 循環依存の解消（1-2 日）

| # | タスク | リスク |
|---|--------|--------|
| 2.1 | `operators/io.py` から `preferences` への依存を特定 | Low |
| 2.2 | 依存を断ち切る方法を決定（ファサード or 分離） | Medium |
| 2.3 | 実装とテスト | Medium |

### Sprint 3: props 登録の修正（2-3 日）

| # | タスク | リスク |
|---|--------|--------|
| 3.1 | アプローチ決定（A/B/C のいずれか） | - |
| 3.2 | 1 つの Editor で試験実装 | Low |
| 3.3 | 全 Editor に適用 | Medium |
| 3.4 | ParsedData キャッシュのクリア処理追加 | Medium |

### Sprint 4: use_reload パターン導入（1 日）

| # | タスク | リスク |
|---|--------|--------|
| 4.1 | `__init__.py` に `use_reload` パターン実装 | Low |
| 4.2 | 明示的な reload 時クリーンアップ処理追加 | Medium |

### Sprint 5: 検証とドキュメント（1 日）

| # | タスク | 成果物 |
|---|--------|--------|
| 5.1 | 3 シナリオのテスト実施 | テストレポート |
| 5.2 | 本ドキュメントの更新 | 最終版 |
| 5.3 | `milestones.md` の Phase 3 を完了にマーク | - |

---

## ゲート条件（Phase 3 完了判定）

以下のすべてが pass すること：

### Reload Scripts テスト

- [x] F3 → Reload Scripts を実行 ✅ Sprint 0 で達成
- [x] Python コンソールにクラッシュなし（警告は許容）✅ Sprint 0/0.1 で達成
- [x] Preferences パネルが表示される ✅ Sprint 0 で達成
- [ ] 既存の Pie Menu が呼び出せる
- [ ] 新規 Pie Menu を作成できる

### カスタムアイコンテスト（Sprint 1.5）

- [ ] Reload Scripts 実行後もカスタムアイコンが表示される
- [ ] アイコン更新ボタン（refresh）が機能する
- [ ] `wm.read_homefile(app_template=...)` 後もアイコンが機能する

### ON/OFF 切り替えテスト

- [ ] Preferences でアドオンを無効化
- [ ] 再度有効化
- [ ] エラーなし
- [ ] 設定が維持されている

### Blender 再起動テスト

- [ ] Blender を終了
- [ ] 再起動
- [ ] アドオンが自動有効化される
- [ ] 全設定が維持されている

---

## 参照

- `rules/milestones.md` — フェーズ定義
- `rules/editor_dependency_map.md` — Editor の依存関係
- `rules/api/pme_api_current.md` — pme モジュールの現状
- `pme.py` — PMEProps, ParsedData の実装
- `addon.py` — init_addon, register_modules の実装
