# pme API 設計案 (Stable / Experimental / Internal)

## 目的

このドキュメントは、**外部スクリプトや他アドオンから使ってよい API** をどう定義するかの設計ドキュメントです。

`rules/pme_api_current.md` の観測結果をベースに、各シンボルに Stability level を付与し、v2.0.0 以降の公開 API を設計します。

> **注意**: このドキュメントは **draft** です。Phase 2-B (alpha.2) で検討・確定します。

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

## 参照

- `rules/pme_api_current.md` — 現状のインベントリ
- `docs/api_pme.md` — API ドキュメント（Phase 2+ で整備予定）
- `rules/architecture.md` — レイヤ構造と依存方向のルール
