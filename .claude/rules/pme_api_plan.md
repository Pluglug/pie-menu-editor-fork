# pme API 設計案 (Stable / Experimental / Internal)

## 目的

このドキュメントは、**外部スクリプトや他アドオンから使ってよい API** をどう定義するかの設計ドキュメントです。

`rules/pme_api_current.md` の観測結果をベースに、各シンボルに Stability level を付与し、v2.0.0 以降の公開 API を設計します。

> **注意**: このドキュメントは Phase 2-B (alpha.2) で検討・確定予定です。

---

## Phase 2-B: External pme API Scope

このセクションでは、**Gizmo Creator 開発者視点のレビュー** を踏まえ、外部ツールが PME を「コマンド実行エンジン」として使うための **最小限の** API スコープを定義します。

> **重要**: Phase 2-B の目的は「Gizmo Creator 一人を満足させられる最小 API を叩き台として出すこと」であり、「エコシステム全体の万能バックエンド API を定義すること」ではない。

### 設計の前提

1. **PME は「コマンド実行エンジン」として機能を提供する**
   - 任意 Python 実行
   - 条件式評価
   - 標準名前空間のセットアップ

2. **外部から触らせない領域を明確化する**
   - `pme.props` / `ParsedData` — ライフサイクル問題があり不安定
   - `context.exec_*` 系 — 内部状態
   - `context.pm` / `context.pmi` の生オブジェクト — 副作用リスク

3. **v2.0.0 では全て Experimental**
   - Stable ラベルは v2.1.0 以降で、利用実績を見て付与する
   - 今の段階で Stable を付けると、将来のリファクタの自由度を失う

### Phase 2-B で本気で守る対象（最小セット）

| API 名 | バンドル | Stability (v2.0) | 備考 |
|--------|---------|------------------|------|
| `pme.execute(code, extra_globals)` | Executor | **Experimental** | `PMEContext.exe` の薄いラッパー |
| `pme.evaluate(expr, extra_globals)` | Executor | **Experimental** | エラーハンドリング方針は後述 |
| `pme.find_pm(name)` | Menu Integration | **Experimental** | 最小限の `PMHandle` を返す |
| `pme.invoke_pm(pm_or_name, event)` | Menu Integration | **Experimental** | `WM_OT_pme_user_pie_menu_call` をラップ |

**これ以外は全て Phase 3 以降に送る。**

### `evaluate()` のエラーハンドリング方針（要決定）

現状、2つの選択肢がある：

#### Option A: 例外を投げる（推奨）

```python
def evaluate(expr: str, extra_globals: dict | None = None) -> Any:
    """
    式を評価して結果を返す。
    評価に失敗した場合は例外を投げる（SyntaxError, NameError など）。
    """
```

**メリット**:
- バグのサイレント抹殺を防ぐ
- ユーザーが typo したら即座に気づける

**デメリット**:
- poll 的な用途で毎回 try-except が必要

#### Option B: エラーはログ出力 + False 返却

```python
def evaluate(expr: str, extra_globals: dict | None = None) -> bool:
    """
    式を評価して bool を返す。
    評価に失敗した場合はログ出力して False を返す。
    """
```

**メリット**:
- poll 条件での使い勝手がいい

**デメリット**:
- typo が見つかりにくい（「なんか gizmo が出たり出なかったりする…」）
- デバッグが困難

#### 現時点の推奨

**Option A（例外を投げる）を推奨。**

poll 用のシュガーが欲しければ、`pme.polls.*` 定数群を使う側の責任にする。

```python
# poll 的な使い方をしたい場合は呼び出し側で処理
try:
    visible = pme.evaluate(self.visibility_condition)
except Exception:
    visible = True  # フォールバック
```

### Phase 3 以降に送るもの

| API | 理由 |
|-----|------|
| `pme.evaluate_ex()` | 使い手が現れてから設計 |
| `pme.ExecuteResult` / `EvaluateResult` のフィールド詳細 | 最初は `success` + `error_message` で十分 |
| `pme.list_pms()` | フィルタ条件の設計が必要 |
| `pme.add_global()` | 本当に必要か要検証 |
| `pme.user_data.get/set` | 永続化の設計が必要 |
| `PMHandle` のフィールド拡張 (`hotkey`, `tag` など) | PM モデル整理後 |

### やらないもの

| API | 理由 |
|-----|------|
| `pme.check_context(...)` | 巨大なシュガー API は避ける |
| `pme.safe_mode` | Python の `exec()` を安全にするのは幻想 |
| `pme.invoke_operator(...)` | コンテキストオーバーライドのエッジケースが多すぎる |

---

## Stability levels

### Stable

- v2.x 系で可能な限り互換性維持を約束する
- 外部スクリプト・他アドオンからの利用を想定
- 変更時は deprecation warning → 1 マイナーバージョン後に削除、のパターン
- ドキュメント化必須

### Experimental

- 将来変更・削除の可能性がある
- 試験的に公開するが、API が安定していない
- フィードバックを受けて Stable に昇格 or 削除
- 変更時の事前通知は必須だが、deprecation 期間は保証しない

### Internal

- アドオン内部のみで使用
- 外部からの利用は非推奨（動くかもしれないが保証しない）
- 予告なく変更・削除される可能性がある
- ドキュメント化は不要

---

## 候補 API 一覧（ドラフト）

### Stable 候補

実行コンテキストとユーザーデータへの基本アクセス:

| シンボル | 現状の用途 | 備考 |
|----------|-----------|------|
| `pme.context.add_global(key, value)` | ユーザースクリプトから変数追加 | よく使われるパターン |
| `pme.context.exe(data, ...)` | コード実行 | 主要 API |
| `pme.context.eval(expression, ...)` | 式評価 | 主要 API |
| `pme.context.U` (UserData) | ユーザーデータ保存 | ドキュメント化されている |

- [ ] TODO: `context.exe()` / `context.eval()` の引数を整理（`menu`, `slot` は使われているか？）
- [ ] TODO: 戻り値の型を明確化

### Experimental 候補

設定アクセスと高度なコンテキスト操作:

| シンボル | 現状の用途 | 備考 |
|----------|-----------|------|
| `pme.get_prefs()` (新設) | PMEPreferences を取得 | `addon.get_prefs()` の再エクスポート案 |
| `pme.context.pm` / `pme.context.pmi` | 現在の PM/PMI を参照 | 読み取り専用として公開？ |
| `pme.context.layout` / `pme.context.event` | 描画/イベント情報 | UI 依存なので Experimental |
| `pme.context.gen_globals(**kwargs)` | グローバル辞書生成 | 高度な用途向け |

- [ ] TODO: `pm` / `pmi` を読み取り専用として公開するか検討
- [ ] TODO: `layout` / `event` を分離すべきか（描画コンテキスト vs 実行コンテキスト）

### Internal 候補

プロパティ管理と内部状態:

| シンボル | 現状の用途 | 備考 |
|----------|-----------|------|
| `pme.props` | プロパティ登録・パース | 内部向け |
| `pme.props.prop_map` | プロパティ定義マップ | 内部向け |
| `pme.props.parse()` / `pme.props.encode()` | パース・エンコード | 内部向け（外部から触ると壊れる） |
| `pme.ParsedData` | パース結果クラス | 内部向け |
| `pme.context.reset()` | 状態リセット | 内部向け |
| `pme.context.exec_globals` / `exec_locals` | 実行状態 | 内部向け |

---

## 新設 API 候補

Phase 2-B 以降で検討する新規 API:

### PM/PMI 検索・取得 API

現状、PM/PMI を検索するには `PMEPreferences.pm_items` を直接舐める必要がある。ファサード API を提供することで、内部構造の変更に強くなる。

```python
# 候補案
pme.find_pm(name) -> PM or None
pme.find_pmi(pm, name) -> PMI or None
pme.list_pms(mode=None) -> list[PM]
```

- [ ] TODO: 戻り値の型（PM/PMI 自体を返すか、ラッパーを返すか）
- [ ] TODO: 検索条件（mode, tag, hotkey など）

### 設定アクセス API

```python
# 候補案
pme.get_prefs() -> PMEPreferences  # addon.get_prefs() の再エクスポート
pme.temp_prefs() -> TempPrefs      # addon.temp_prefs() の再エクスポート
```

- [ ] TODO: `get_prefs()` を Stable にするか Experimental にするか

---

## Phase 2-B でやること

このドキュメントをベースに、alpha.2 で以下を実施:

1. **Stability level の確定**
   - Stable / Experimental / Internal のラベリングを完了
   - 各シンボルのドキュメント文字列（docstring）を整備

2. **最小限の API 導線実装**
   - `editors/` から `prefs` を直接舐めるパターンを、`pme` API 経由に置き換える（1-2 箇所の実験）
   - 動作確認

3. **外部利用シナリオの文書化**
   - ユーザースクリプトからの典型的な使い方
   - 他アドオンとの連携パターン

---

## 設計方針

### 1. 最小限の公開

- 必要最小限のシンボルのみ Stable にする
- 「あったら便利」程度のものは Experimental に留める
- 迷ったら Internal

### 2. 読み取り優先

- 外部から「読み取る」API は積極的に公開
- 外部から「書き換える」API は慎重に（副作用の管理が難しい）

### 3. 後方互換性

- Stable API は v2.x 系で互換性を維持
- 内部構造が変わっても、Stable API の挙動は維持

### 4. ファサードパターン

- 外部からは `pme` モジュール経由でアクセス
- 内部実装（`preferences.py`, `pme_types.py` など）には直接触らせない

---

## Draft API Signatures（最小セット）

Phase 2-B で実装を検討する **最小限の** API シグネチャ案。

> **注意**: Result クラスのフィールド詳細や `evaluate_ex` などは、使い手が現れてから設計する。今は最小限で始める。

### Executor（2 関数のみ）

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class ExecuteResult:
    """コード実行の結果。最小限のフィールドで始める。"""
    success: bool
    error_message: str | None = None
    # Phase 3 以降で必要に応じて追加: error_type, traceback

def execute(code: str, *, extra_globals: dict | None = None) -> ExecuteResult:
    """
    任意の Python コードを実行する。

    標準名前空間（C, D など）は自動的に提供される。
    extra_globals で追加の変数を渡すことができる。

    内部実装: PMEContext.exe() をラップ
    """
    ...

def evaluate(expr: str, *, extra_globals: dict | None = None) -> Any:
    """
    式を評価して結果を返す。

    評価に失敗した場合は例外を投げる（SyntaxError, NameError など）。
    poll 用途で try-except が必要な場合は呼び出し側で処理する。

    内部実装: PMEContext.eval() をラップ
    """
    ...
```

### Menu Integration（2 関数 + 最小限の型）

```python
from dataclasses import dataclass
import bpy

@dataclass
class PMHandle:
    """
    PM の読み取り専用ラッパー。最小限のフィールドで始める。
    """
    name: str
    # Phase 3 以降で必要に応じて追加: mode, enabled, hotkey, tag

def find_pm(name: str) -> PMHandle | None:
    """
    名前で PM を検索する。
    見つからない場合は None を返す。

    内部実装: PMEPreferences.pie_menus.get(name)
    """
    ...

def invoke_pm(
    pm_or_name: PMHandle | str,
    event: bpy.types.Event | None = None
) -> bool:
    """
    PM を呼び出す（表示する）。
    成功したら True、失敗したら False を返す。

    内部実装: WM_OT_pme_user_pie_menu_call をラップ
    """
    ...
```

### 内部実装の対応関係

| 公開 API | 内部実装 | 備考 |
|----------|---------|------|
| `execute()` | `PMEContext.exe()` | `gen_globals()` を内部で呼ぶ |
| `evaluate()` | `PMEContext.eval()` | 例外をそのまま投げる |
| `find_pm()` | `PMEPreferences.pie_menus.get()` | `PMHandle` でラップ |
| `invoke_pm()` | `WM_OT_pme_user_pie_menu_call` | オペレーター呼び出し |

---

## Future API Ideas（PME 側からの追加提案）

Gizmo Creator 視点のレビューに対して、PME 側から提案する追加 API アイデア。
実装は当然後回しで、価値とコストを見極めてから検討する。

### 1. `pme.log` ラッパー

**概要**: `infra/debug.py` の構造化ログ機能を薄くラップ

**提供する API**:
```python
pme.log.debug(msg: str, **context) -> None
pme.log.info(msg: str, **context) -> None
pme.log.warn(msg: str, **context) -> None
pme.log.error(msg: str, **context) -> None
```

**価値**:
- 外部アドオンからも PME と同じログフォーマットで出力可能
- デバッグ体験の統一
- `DBG_STRUCTURED=True` 時に NDJSON で出力され、解析しやすい

**コスト**: 低（既存の `dbg_log` をラップするだけ）

**Stability**: Experimental（ログフォーマットが変わる可能性）

### 2. `pme.profile` 簡易プロファイラ

**概要**: `DBG_PROFILE` をベースにした処理時間計測ユーティリティ

**提供する API**:
```python
with pme.profile("my_operation"):
    # 計測したい処理
    pass
# → ログに所要時間が出力される
```

**価値**:
- 外部ツールが自分の処理のボトルネックを測定可能
- PME の `dbg_scope("profile", ...)` と同じフォーマットで出力

**コスト**: 低（`dbg_scope` をラップするだけ）

**Stability**: Experimental

### 3. `pme.polls` 定数群（条件式プリセット）

**概要**: よくある poll 条件を定数文字列として提供

**提供する API**:
```python
# 定数として提供（関数ではない）
pme.polls.MESH_EDIT = "C.mode == 'EDIT_MESH'"
pme.polls.OBJECT_MODE = "C.mode == 'OBJECT'"
pme.polls.HAS_ACTIVE_OBJECT = "C.active_object is not None"
pme.polls.SCULPT_MODE = "C.mode == 'SCULPT'"
```

**使い方**:
```python
# Gizmo Creator から
if pme.evaluate(pme.polls.MESH_EDIT):
    self.draw_gizmo()
```

**価値**:
- 巨大な `check_context()` API を作る代わりに、薄いヘルパーで済む
- 定数なので壊れにくい（評価は `evaluate()` に任せる）
- ユーザーがコピペして条件をカスタマイズ可能

**コスト**: 非常に低（文字列定数を定義するだけ）

**Stability**: Stable（文字列なので変更しにくい → 慎重に定義）

---

## 参照

- `rules/pme_api_current.md` — 現状のインベントリ
- `rules/pme_standard_namespace.md` — 標準名前空間の定義
- `docs/api_pme.md` — API ドキュメント（Phase 2+ で整備予定）
- `rules/architecture.md` — レイヤ構造と依存方向のルール
- Gizmo Creator 開発者視点の PME API レビュー
