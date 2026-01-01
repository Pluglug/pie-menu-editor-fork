# pme API (現状インベントリ)

## 目的

このドキュメントは、現状の `pme` モジュールが外部・内部からどう使われているかを記録する **観測ドキュメント** です。

Phase 2-B (alpha.2) で、各シンボルに **Stability level** を付与しました。
詳細な設計は `rules/api/pme_api_plan.md` を参照してください。

---

## Stability Levels

| レベル | 意味 |
|--------|------|
| **Stable** | v2.x 系で互換性維持。外部からの依存を想定 |
| **Experimental** | 変更の可能性あり。フィードバック次第で Stable 昇格 or 削除 |
| **Internal** | 外部からの利用は非推奨。予告なく変更される |

---

## Public symbols

`pme` モジュール直下に存在するシンボルの一覧:

### クラス

| シンボル | 説明 | 用途 | Stability |
|----------|------|------|-----------|
| `UserData` | 汎用データコンテナ | `pme_context.U` として使用。ユーザースクリプトからのデータ保存用 | **Experimental** |
| `PMEContext` | 実行コンテキスト管理 | PM/PMI 実行時のグローバル変数・状態を管理 | **Internal** |
| `PMEProp` | 単一プロパティ定義 | プロパティのメタデータ（型、デフォルト値、items）を保持 | **Internal** |
| `PMEProps` | プロパティ管理 | `prop_map` でプロパティを登録し、テキストのパース・エンコードを担当 | **Internal** |
| `ParsedData` | パース済みプロパティ | テキスト形式 (`TYPE?key=value&...`) をパースした結果 | **Internal** |

### インスタンス

| シンボル | 型 | 説明 | Stability |
|----------|-----|------|-----------|
| `context` | `PMEContext` | グローバルな実行コンテキストインスタンス | **Internal** |
| `props` | `PMEProps` | グローバルなプロパティ管理インスタンス | **Internal** |

### 関数

| シンボル | 説明 | Stability |
|----------|------|-----------|
| `register()` | `context` に `UserData` インスタンスを追加 | **Internal** |

### 再エクスポート（`addon` から）

`pme.py` 自体は以下を `addon` からインポートしているが、現状 `pme` から直接公開はしていない:

| シンボル | 説明 | Stability |
|----------|------|-----------|
| `get_prefs()` | `PMEPreferences` インスタンスを取得 | **Internal** — 外部からの直接アクセスは非推奨 |
| `temp_prefs()` | 一時的な設定オブジェクトを取得 | **Internal** |
| `print_exc()` | 例外出力ヘルパー | **Internal** |

---

## PMEContext の主要 API

`pme.context` インスタンスが提供するメソッドと属性:

> **注意**: `PMEContext` 自体は **Internal** ですが、一部のメソッドは将来的に `pme.execute()` / `pme.evaluate()` のラッパーとして公開される予定です。

### メソッド

| メソッド | シグネチャ | 説明 | Stability |
|----------|-----------|------|-----------|
| `add_global` | `(key, value)` | グローバル名前空間に変数を追加 | **Experimental** → `pme.add_global()` として公開予定 |
| `gen_globals` | `(**kwargs) → dict` | 実行用のグローバル辞書を生成 | **Internal** |
| `eval` | `(expression, globals=None, menu=None, slot=None) → Any` | 式を評価 | **Internal** → `pme.evaluate()` の内部実装 |
| `exe` | `(data, globals=None, menu=None, slot=None, use_try=True) → bool` | コードを実行 | **Internal** → `pme.execute()` の内部実装 |
| `reset` | `()` | 状態をリセット | **Internal** |
| `item_id` | `() → str` | 現在のアイテムの ID を生成 | **Internal** |

### 属性

| 属性 | 型 | 説明 | Stability |
|------|-----|------|-----------|
| `pm` | `PMItem` or `None` | 現在実行中の Pie Menu | **Internal** — 生オブジェクト。外部からの参照は非推奨 |
| `pmi` | `PMIItem` or `None` | 現在実行中の Pie Menu Item | **Internal** — 生オブジェクト。外部からの参照は非推奨 |
| `index` | `int` or `None` | 現在のアイテムインデックス | **Internal** |
| `icon` | `str` or `None` | 現在のアイコン名 | **Internal** |
| `icon_value` | `int` or `None` | 現在のアイコン値 | **Internal** |
| `text` | `str` or `None` | 現在のテキスト | **Internal** |
| `layout` | `UILayout` or `None` | 現在のレイアウト（プロパティ setter で `L` にも設定） | **Internal** |
| `event` | `Event` or `None` | 現在のイベント（プロパティ setter で `E`, `delta` にも設定） | **Internal** |
| `region` | `Region` or `None` | 現在のリージョン | **Internal** |
| `is_first_draw` | `bool` | 初回描画かどうか | **Internal** |
| `exec_globals` | `dict` or `None` | exec 用グローバル | **Internal** — 絶対に外部から触らせない |
| `exec_locals` | `dict` or `None` | exec 用ローカル | **Internal** — 絶対に外部から触らせない |
| `exec_user_locals` | `dict` | ユーザー定義ローカル変数 | **Internal** — 絶対に外部から触らせない |

### グローバル名前空間のデフォルト変数

`gen_globals()` によって生成される辞書には以下が含まれる。
詳細は `rules/api/pme_standard_namespace.md` を参照。

> **注意**: v2.0.0 では全て Experimental。Stable は v2.1.0 以降で検討。

| 変数名 | 値 | Stability (v2.0) |
|--------|-----|------------------|
| `bpy` | `bpy` モジュール | **Experimental** |
| `C` | `bpy.context` | **Experimental** |
| `D` | `bpy.data` | **Experimental** |
| `E` | 現在の `event` | **Experimental** |
| `L` | 現在の `layout` | **Experimental** |
| `U` | `UserData` インスタンス | **Experimental** |
| `drag_x`, `drag_y` | ドラッグ座標 | **Experimental** |
| `delta` | マウスホイールのデルタ値 | **Experimental** |
| `text`, `icon`, `icon_value` | 現在のコンテキスト値 | **Experimental** |
| `pme_context` | `context` インスタンス自身 | **Internal** |
| `PME` | `temp_prefs()` | **Internal** |
| `PREFS` | `get_prefs()` | **Internal** |

---

## PMEProps の主要 API

> **⚠️ このセクション全体が Internal です**
>
> `pme.props` / `ParsedData` は **Reload Scripts の既知問題** があり、外部からの利用は非推奨です。
> ライフサイクルの問題が解決されるまで、外部ツールはこれらに依存しないでください。

`pme.props` インスタンスが提供するメソッド:

| メソッド | シグネチャ | 説明 | Stability |
|----------|-----------|------|-----------|
| `IntProperty` | `(type, name, default=0)` | 整数プロパティを登録 | **Internal** |
| `BoolProperty` | `(type, name, default=False)` | ブールプロパティを登録 | **Internal** |
| `StringProperty` | `(type, name, default="")` | 文字列プロパティを登録 | **Internal** |
| `EnumProperty` | `(type, name, default, items)` | 列挙型プロパティを登録 | **Internal** |
| `get` | `(name) → PMEProp or None` | プロパティ定義を取得 | **Internal** |
| `parse` | `(text) → ParsedData` | テキストをパースして `ParsedData` を返す（キャッシュあり） | **Internal** |
| `encode` | `(text, prop, value) → str` | プロパティ値をテキストにエンコード | **Internal** |
| `clear` | `(text, *args) → str` | 指定プロパティをクリア | **Internal** |

### プロパティ登録タイミングの問題（既知の問題）

- プロパティは各エディタモジュール（`ed_*.py`）の `register()` で登録される
- `ParsedData` は `parse()` 時点で `prop_map` を参照する
- **Reload Scripts 後に `prop_map` が空になり、属性エラーが発生する**（Issue #64）

**これが Internal としてマークされている主な理由です。** Phase 3 でライフサイクルを再設計するまで、外部からの依存は避けてください。

---

## Usage map

「どのシンボルが、どのモジュールから呼ばれているか」のラフなマップ:

### `pme.context` の使用箇所

| 呼び出し元カテゴリ | 主な使用方法 |
|-------------------|-------------|
| `operators/` (runtime 系) | `context.pm`, `context.pmi`, `context.exe()`, `context.eval()` で PM/PMI を実行 |
| `ui/` | `context.layout` を設定して描画 |
| `editors/` | `context.add_global()` でエディタ固有の変数を追加 |

### `pme.props` の使用箇所

| 呼び出し元カテゴリ | 主な使用方法 |
|-------------------|-------------|
| `editors/` | `props.IntProperty()` などでプロパティ定義を登録 |
| `operators/` | `props.parse()`, `props.encode()` で PM/PMI のデータを読み書き |
| `ui/` | `props.parse()` で表示用データを取得 |

### `ParsedData` の使用箇所

| 呼び出し元カテゴリ | 主な使用方法 |
|-------------------|-------------|
| 全般 | `pd = props.parse(text)` で取得し、`pd.some_prop` で値を参照 |

---

## 現状の問題点メモ

### 1. `ParsedData` と props 登録タイミングの依存

- `ParsedData.__init__()` は `props.prop_map` を参照する
- プロパティは `ed_*.py` の `register()` で登録される
- **Reload Scripts 後、`register()` が呼ばれる前に `parse()` されると属性エラー**

```python
# ParsedData.__init__ より
for k, prop in props.prop_map.items():  # ← prop_map が空だと何も設定されない
    if prop.type == self.type:
        setattr(self, k, prop.default)
```

### 2. `context` に UI 依存が混ざっている

- `context.layout` は `UILayout` を保持
- `context.region` は `Region` を保持
- これらは「実行コンテキスト」というより「描画コンテキスト」

### 3. `props.parsed_data` のキャッシュがライフサイクルを跨ぐ

- `props.parsed_data` は辞書でキャッシュ
- Reload Scripts 後もキャッシュが残り、古い `ParsedData` が再利用される可能性

### 4. `prefs` への直接依存

- `context.gen_globals()` 内で `get_prefs()`, `temp_prefs()` を呼び出し
- `pme` が `addon` に依存している（レイヤ的には許容範囲内だが、ファサードとしては要検討）

---

## Phase 2-B での決定事項

Phase 2-A の観測結果を踏まえ、以下が決定されました：

### 重要な前提

**v2.0.0 では全て Experimental。** Stable ラベルは v2.1.0 以降で、利用実績を見て付与する。

### Phase 2-B で公開する最小セット（全て Experimental）

**Executor:**
- `pme.execute()` — `PMEContext.exe()` の薄いラッパー
- `pme.evaluate()` — `PMEContext.eval()` の薄いラッパー（例外を投げる）

**Menu Integration:**
- `pme.find_pm()` — PM 検索 API
- `pme.invoke_pm()` — PM 呼び出し API

**標準名前空間:**
- `C`, `D`, `bpy`, `E`, `L`, `U`, `delta`, etc. — 全て Experimental

### Phase 3 以降に送るもの

- `pme.evaluate_ex()` / 詳細な Result クラス
- `pme.add_global()` — 本当に必要か要検証
- `pme.list_pms()` — フィルタ条件の設計が必要
- `PMHandle` のフィールド拡張

### Internal として隠蔽するもの

- `pme.props` / `ParsedData` 全体 — ライフサイクル問題
- `pme.context.exec_*` 系 — 内部状態
- `pme.context.pm` / `pme.context.pmi` の生オブジェクト — 副作用リスク
- `PME`, `PREFS` 変数 — 内部設定への直接アクセス

詳細は `rules/api/pme_api_plan.md` を参照。

---

## Phase 2-A 観測結果（追加）

以下は Phase 2-A で調査した結果。元々「残りの調査項目」として挙げられていた内容。

### `props.prop_map` への登録順序

**問題**: プロパティ登録がモジュールのロード時（import 時）に発生する

各エディタモジュールでは、**モジュールレベル**（`class Editor` 定義の前）で `pme.props.*Property()` が呼び出される:

```python
# editors/pie_menu.py:15-18 (モジュールレベル)
pme.props.IntProperty("pm", "pm_radius", -1)
pme.props.IntProperty("pm", "pm_confirm", -1)
pme.props.IntProperty("pm", "pm_threshold", -1)
pme.props.BoolProperty("pm", "pm_flick", True)

class Editor(EditorBase):
    ...
```

**登録タイミング**:
1. モジュールが import される → `pme.props.*Property()` が実行
2. `pme.props.prop_map[name] = PMEProp(...)` で登録
3. `register()` が呼ばれる → `Editor()` インスタンスが作成される

**Reload Scripts での問題**:
1. Reload 前: `prop_map` には全プロパティが登録済み
2. Reload 開始: `unregister()` が呼ばれるが、`prop_map` はクリアされない
3. モジュール再ロード: 同じプロパティが再登録される（問題なし）
4. しかし、`ParsedData` のキャッシュ（`props.parsed_data`）は古い状態のまま
5. 古い `ParsedData` が新しい `prop_map` と整合しない可能性

### `ParsedData` の属性一覧

各エディタが登録するプロパティと、`ParsedData` の属性の対応:

| type | プロパティ名 | ptype | デフォルト値 | 登録元 |
|------|-------------|-------|-------------|--------|
| `pm` | `pm_radius` | INT | -1 | `editors/pie_menu.py:15` |
| `pm` | `pm_confirm` | INT | -1 | `editors/pie_menu.py:16` |
| `pm` | `pm_threshold` | INT | -1 | `editors/pie_menu.py:17` |
| `pm` | `pm_flick` | BOOL | True | `editors/pie_menu.py:18` |
| `rm` | `rm_title` | BOOL | True | `editors/menu.py:600` |
| `row` | `layout` | STR (ENUM) | 'COLUMN' | `editors/popup.py:1649` |
| `row` | `width` | STR (ENUM) | 'NORMAL' | `editors/popup.py:1659` |
| `row` | `poll` | STR (ENUM) | 'NORMAL' | `editors/popup.py:1669` |
| `row` | `fixed_col` | BOOL | False | `editors/popup.py:1680` |
| `row` | `fixed_but` | BOOL | False | `editors/popup.py:1681` |
| `pd` | `align` | BOOL | True | `editors/popup.py:1682` (推定) |
| `pg` | `pg_wicons` | BOOL | - | `editors/panel_group.py:683` |
| `pg` | `pg_context` | STR | "ANY" | `editors/panel_group.py:684` |
| `pg` | `pg_category` | STR | "My Category" | `editors/panel_group.py:685` |
| `pg` | `pg_space` | STR | "VIEW_3D" | `editors/panel_group.py:686` |
| `pg` | `pg_region` | STR | "TOOLS" | `editors/panel_group.py:687` |
| `mo` | `confirm` | BOOL | False | `ed_modal.py:25` |
| `mo` | `block_ui` | BOOL | True | `ed_modal.py:26` |
| `mo` | `lock` | BOOL | True | `ed_modal.py:27` |
| `s` | `s_undo` | BOOL | - | `ed_stack_key.py:5` |
| `s` | `s_state` | BOOL | - | `ed_stack_key.py:6` |
| `sk` | `sk_block_ui` | BOOL | False | `ed_sticky_key.py:48` |

**`type` の意味**:
- `pm`: Pie Menu
- `rm`: Regular Menu
- `row` / `pd`: Pop-up Dialog
- `pg`: Panel Group
- `mo`: Modal Operator
- `s`: Stack Key
- `sk`: Sticky Key

`ParsedData.__init__()` は、`text` の先頭から `type` を抽出し、その `type` に対応するプロパティのみを属性として設定する。

### `exec_globals` / `exec_locals` の使い分けパターン

`PMEContext` には 3 種類の辞書がある:

| 属性 | 用途 | ライフサイクル |
|------|------|--------------|
| `_globals` | 基本的なグローバル変数 (`bpy`, `pme_context`, `drag_x/y`) | インスタンス生成時に初期化 |
| `exec_globals` | `exec()` 呼び出し時のグローバル辞書 | 各 exec 呼び出しで設定、`reset()` でクリア |
| `exec_locals` | `exec()` 呼び出し時のローカル辞書 | 各 exec 呼び出しで設定、`reset()` でクリア |
| `exec_user_locals` | ユーザースクリプトから設定されたローカル変数 | 永続、`reset()` ではクリアされない |

**典型的な使用パターン**:

```python
# 1. gen_globals() で統合辞書を生成
globals_dict = context.gen_globals()
# → _globals + exec_user_locals + 動的値 (text, icon, PME, PREFS) を統合

# 2. exe() でコードを実行
context.exe(code, globals=globals_dict)
# → exec(code, globals_dict) を呼び出し

# 3. eval() で式を評価
result = context.eval(expression, globals=globals_dict)
# → eval(expression, globals_dict) を呼び出し
```

**外部から触らせない理由**:
- `exec_globals` / `exec_locals` は `exec()` の実行中のみ有効
- 外部から設定すると、次の実行で上書きされる
- 意図しない副作用の原因になる

---

## 参照

- `pme.py`: 実装ファイル
- `addon.py`: `get_prefs()`, `temp_prefs()`, `print_exc()` の実装
- `rules/api/pme_api_plan.md`: API 設計案（Phase 2-B で更新）
- `rules/api/pme_standard_namespace.md`: 標準名前空間の定義
- `docs/api_pme.md`: API ドキュメント（Phase 2+ で整備予定）
