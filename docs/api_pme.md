# pme API Reference (Draft)

> **Status**: DRAFT - Phase 2+ で整備予定
>
> このドキュメントは `pie_menu_editor.pme` モジュールの公開 API を定義します。
> 現時点では「現状の整理」であり、API 仕様として確定したものではありません。

---

## Overview

`pie_menu_editor.pme` は PME の「外部ファサード」として位置づけられるモジュールです。

**設計目標**:
- ユーザースクリプトから PME の機能に安全にアクセスできる
- 内部実装の詳細を隠蔽し、安定したインターフェースを提供
- Reload Scripts に対して堅牢

**現状**:
- 外から安定して使えるのは `pme.context.add_global()` くらい
- 他の API (`props` / `ParsedData` / `exec` 系) は「中の実装がそのまま漏れてる」状態

---

## Namespaces

### `pme.context` (Execution Context)

実行時コンテキストの管理。

| Member | Stability | Description |
|--------|-----------|-------------|
| `pme.context.add_global(key, value)` | **Stable** | グローバル変数の追加 |
| `pme.context.globals` | Experimental | 現在のグローバル辞書 |
| `pme.context.pm` | Internal | 現在の Pie Menu オブジェクト |
| `pme.context.pmi` | Internal | 現在の Pie Menu Item |
| `pme.context.layout` | Internal | 現在の UILayout |
| `pme.context.event` | Internal | 現在の Event |
| `pme.context.eval(expression)` | Experimental | 式の評価 |
| `pme.context.exe(code)` | Experimental | コードの実行 |

### `pme.props` / `PMEProps` (Property System)

PM/PMI のカスタムプロパティ管理。

| Member | Stability | Description |
|--------|-----------|-------------|
| `pme.props.parse(text)` | Internal | データ文字列をパースして `ParsedData` を返す |
| `pme.props.encode(text, prop, value)` | Internal | プロパティ値をエンコード |
| `pme.props.BoolProperty(type, name, default)` | Internal | Bool プロパティ登録 |
| `pme.props.IntProperty(type, name, default)` | Internal | Int プロパティ登録 |
| `pme.props.StringProperty(type, name, default)` | Internal | String プロパティ登録 |
| `pme.props.EnumProperty(type, name, default, items)` | Internal | Enum プロパティ登録 |

**Known Issues**:
- `prop_map` の登録タイミングが Reload Scripts で問題を起こす (Issue #64)
- `ParsedData` のキャッシュが stale になる可能性

### `ParsedData` (Data Model)

パースされた PM/PMI データのコンテナ。

| Attribute | Stability | Description |
|-----------|-----------|-------------|
| `.type` | Internal | データタイプ ("pm", "pmi", etc.) |
| `.pm_flick` | Internal | Pie Menu: Confirm on Release |
| `.pm_radius` | Internal | Pie Menu: Custom radius |
| `.is_empty` | Internal | すべてのプロパティがデフォルトか |

---

## Stability Levels

| Level | Meaning | Commitment |
|-------|---------|------------|
| **Stable** | 安定 API | 破壊的変更時は deprecation warning |
| **Experimental** | 実験的 API | 警告なく変更される可能性あり |
| **Internal** | 内部用 | 外部からの使用は非推奨 |

---

## Future Directions

### Phase 2: Data Model Refactoring

- `pme.props` / `PMEProps` / `ParsedData` を `core` 層に寄せる
- `pme.context` の責務を分離（実行コンテキスト vs UI 依存）

### Phase 3: Stable API Design

- Reload-safe な props lifecycle の実現
- operators/editors から pme への依存方向を一方向に
- ユーザースクリプト向けの安定 API 公開

### Long Term

- `pme.data` 名前空間の追加（メニュー構造への高レベルアクセス）
- プロパティアクセスの型安全化
- イベントシステムの整備

---

## Usage Examples (Experimental)

### Adding a Global Variable

```python
# ユーザースクリプトから
from pie_menu_editor import pme

pme.context.add_global("my_helper", my_helper_function)
```

### Accessing PM Data (Internal - Not Recommended)

```python
# 内部用 - 将来変更される可能性あり
from pie_menu_editor import pme

parsed = pme.props.parse(pm.data)
if hasattr(parsed, "pm_flick"):  # 属性存在チェック推奨
    flick = parsed.pm_flick
```

---

## Changelog

- **v2.0.0-alpha.0**: Initial draft of API documentation
