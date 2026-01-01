# pme API (現状インベントリ)

## 目的

このドキュメントは、現状の `pme` モジュールが外部・内部からどう使われているかを記録する **観測ドキュメント** です。
まだ「設計」として確定した仕様ではなく、Phase 2-A (alpha.1) の「観測」フェーズでの調査結果をまとめたものです。

Phase 2-B (alpha.2) では、このインベントリをベースに `rules/pme_api_plan.md` で Stable / Experimental / Internal のラベリングを行います。

---

## Public symbols

`pme` モジュール直下に存在するシンボルの一覧:

### クラス

| シンボル | 説明 | 用途 |
|----------|------|------|
| `UserData` | 汎用データコンテナ | `pme_context.U` として使用。ユーザースクリプトからのデータ保存用 |
| `PMEContext` | 実行コンテキスト管理 | PM/PMI 実行時のグローバル変数・状態を管理 |
| `PMEProp` | 単一プロパティ定義 | プロパティのメタデータ（型、デフォルト値、items）を保持 |
| `PMEProps` | プロパティ管理 | `prop_map` でプロパティを登録し、テキストのパース・エンコードを担当 |
| `ParsedData` | パース済みプロパティ | テキスト形式 (`TYPE?key=value&...`) をパースした結果 |

### インスタンス

| シンボル | 型 | 説明 |
|----------|-----|------|
| `context` | `PMEContext` | グローバルな実行コンテキストインスタンス |
| `props` | `PMEProps` | グローバルなプロパティ管理インスタンス |

### 関数

| シンボル | 説明 |
|----------|------|
| `register()` | `context` に `UserData` インスタンスを追加 |

### 再エクスポート（`addon` から）

`pme.py` 自体は以下を `addon` からインポートしているが、現状 `pme` から直接公開はしていない:

- `get_prefs()` — `PMEPreferences` インスタンスを取得
- `temp_prefs()` — 一時的な設定オブジェクトを取得
- `print_exc()` — 例外出力ヘルパー

---

## PMEContext の主要 API

`pme.context` インスタンスが提供するメソッドと属性:

### メソッド

| メソッド | シグネチャ | 説明 |
|----------|-----------|------|
| `add_global` | `(key, value)` | グローバル名前空間に変数を追加 |
| `gen_globals` | `(**kwargs) → dict` | 実行用のグローバル辞書を生成 |
| `eval` | `(expression, globals=None, menu=None, slot=None) → Any` | 式を評価 |
| `exe` | `(data, globals=None, menu=None, slot=None, use_try=True) → bool` | コードを実行 |
| `reset` | `()` | 状態をリセット |
| `item_id` | `() → str` | 現在のアイテムの ID を生成 |

### 属性

| 属性 | 型 | 説明 |
|------|-----|------|
| `pm` | `PM` or `None` | 現在実行中の Pie Menu |
| `pmi` | `PMI` or `None` | 現在実行中の Pie Menu Item |
| `index` | `int` or `None` | 現在のアイテムインデックス |
| `icon` | `str` or `None` | 現在のアイコン名 |
| `icon_value` | `int` or `None` | 現在のアイコン値 |
| `text` | `str` or `None` | 現在のテキスト |
| `layout` | `UILayout` or `None` | 現在のレイアウト（プロパティ setter で `L` にも設定） |
| `event` | `Event` or `None` | 現在のイベント（プロパティ setter で `E`, `delta` にも設定） |
| `region` | `Region` or `None` | 現在のリージョン |
| `is_first_draw` | `bool` | 初回描画かどうか |
| `exec_globals` | `dict` or `None` | exec 用グローバル |
| `exec_locals` | `dict` or `None` | exec 用ローカル |
| `exec_user_locals` | `dict` | ユーザー定義ローカル変数 |

### グローバル名前空間のデフォルト変数

`gen_globals()` によって生成される辞書には以下が含まれる:

| 変数名 | 値 |
|--------|-----|
| `bpy` | `bpy` モジュール |
| `pme_context` | `context` インスタンス自身 |
| `C` | `bpy.context` |
| `D` | `bpy.data` |
| `L` | 現在の `layout` |
| `E` | 現在の `event` |
| `U` | `UserData` インスタンス |
| `drag_x`, `drag_y` | ドラッグ座標 |
| `delta` | マウスホイールのデルタ値 |
| `text`, `icon`, `icon_value` | 現在のコンテキスト値 |
| `PME` | `temp_prefs()` |
| `PREFS` | `get_prefs()` |

---

## PMEProps の主要 API

`pme.props` インスタンスが提供するメソッド:

| メソッド | シグネチャ | 説明 |
|----------|-----------|------|
| `IntProperty` | `(type, name, default=0)` | 整数プロパティを登録 |
| `BoolProperty` | `(type, name, default=False)` | ブールプロパティを登録 |
| `StringProperty` | `(type, name, default="")` | 文字列プロパティを登録 |
| `EnumProperty` | `(type, name, default, items)` | 列挙型プロパティを登録 |
| `get` | `(name) → PMEProp or None` | プロパティ定義を取得 |
| `parse` | `(text) → ParsedData` | テキストをパースして `ParsedData` を返す（キャッシュあり） |
| `encode` | `(text, prop, value) → str` | プロパティ値をテキストにエンコード |
| `clear` | `(text, *args) → str` | 指定プロパティをクリア |

### プロパティ登録タイミングの問題（既知の問題）

- プロパティは各エディタモジュール（`ed_*.py`）の `register()` で登録される
- `ParsedData` は `parse()` 時点で `prop_map` を参照する
- **Reload Scripts 後に `prop_map` が空になり、属性エラーが発生する**（Issue #64）

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

## TODO: Phase 2-A で追加調査が必要な項目

- [ ] `props.prop_map` への登録順序と、各エディタの `register()` 呼び出し順序の関係
- [ ] `ParsedData` の属性一覧（どのエディタがどのプロパティを登録しているか）
- [ ] `context` の `exec_globals` / `exec_locals` の使い分けパターン
- [ ] 外部スクリプトから `pme.context` がどう呼ばれているかの実例収集

---

## 参照

- `pme.py`: `E:\0187_Pie-Menu-Editor\MyScriptDir\addons\pie_menu_editor\pme.py`
- `addon.py`: `get_prefs()`, `temp_prefs()`, `print_exc()` の実装
- `docs/api_pme.md`: API ドラフト（Phase 2+ で整備予定）
