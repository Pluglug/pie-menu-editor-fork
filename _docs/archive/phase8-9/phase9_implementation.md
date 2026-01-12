# Phase 9: JSON Schema v2 実装ガイド

> **目的**: 2.0.0 の中核機能である JSON Schema v2 の実装手順
> **期間**: 2026-01-05 〜 今月中
> **方針**: 「いま動いているものを壊さずに、土台とスキーマを固める」
> **GitHub Milestone**: [2.0.0 - JSON Schema v2](https://github.com/Pluglug/pie-menu-editor-fork/milestone/1)
> **Tracking Issue**: [#78](https://github.com/Pluglug/pie-menu-editor-fork/issues/78)

---

## 関連 Issue

| Issue | タイトル | フェーズ |
|-------|---------|---------|
| #78 | PME2: JSON Schema v2 for 2.0.0 | トラッキング |
| #79 | PME2: Menu name/uid separation and reference redesign | 9-B, 9-C |
| #80 | PME2: Style system - Color bar visualization | 9-B |
| #81 | PME2: description / description_expr implementation | 9-B |
| #82 | PME2: Action.context implementation | 9-B |
| #83 | Schema v2: PME1 to PME2 converter | 9-C |
| #84 | Schema v2: Implement dataclass schemas | 9-B |

---

## 0. 前提条件の確認

### 決定済み事項

| 項目 | 決定 | 根拠 |
|------|------|------|
| JSON v2 形式 | `json_schema_v2.md` で確定 | pme_mini で検証済み |
| 後方互換範囲 | 1.19.x（1.18.x は可能なら） | メンター相談結果 |
| 内部スキーマ | エクスポート用のみ（2.0.0） | 安定性優先 |

### 未決定事項（検討中）

| 項目 | 選択肢 | 検討文書 |
|------|--------|---------|
| Action.context 仕様 | Python 式 / 構造化 / 両方 | `schema_v2_analysis.md` Q1 |
| dataclass 設計 | シングルクラス / Union 型 | `schema_v2_analysis.md` Q7 |
| Settings 型付け | dict / 型付き | `schema_v2_analysis.md` Q8 |

---

## 1. ディレクトリ構造（目標）

```
pie_menu_editor/
├── core/
│   ├── schema.py          # 既存（PMEProps, ParsedData）
│   └── schemas/           # 新規（Phase 9）
│       ├── __init__.py
│       ├── base.py        # Action, MenuItemSchema, HotkeySchema
│       ├── menu.py        # MenuSchema, PME2File
│       ├── pie_menu.py    # PieMenuSchema（convenience wrapper）
│       ├── popup.py       # PopupSchema
│       └── ...
│
├── infra/
│   ├── converter.py       # 新規: PME1 → PME2 変換
│   ├── serializer.py      # 新規: v2 エクスポート/インポート
│   └── io.py              # 既存（ファイル I/O）
```

---

## 2. 実装フェーズ

### Phase 9-A: dataclass スキーマ定義

**ソース**: `pme_mini/core/schemas.py` をベースに

```python
# core/schemas/base.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal

ActionType = Literal["command", "custom", "prop", "menu", "hotkey", "operator", "empty"]

@dataclass
class Action:
    type: ActionType = "empty"
    value: str = ""

    # command 用
    undo: bool | None = None
    context: str | None = None

    # custom 用
    use_try: bool | None = None

    # prop 用
    expand: bool | None = None
    slider: bool | None = None
    toggle: bool | None = None

    # menu 用
    mode: str | None = None

    # operator 用
    properties: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """タイプに応じた必要なフィールドのみ出力"""
        result = {"type": self.type, "value": self.value}

        if self.type == "command":
            result["undo"] = self.undo if self.undo is not None else True
            result["context"] = self.context
        elif self.type == "custom":
            result["undo"] = self.undo if self.undo is not None else False
            result["use_try"] = self.use_try if self.use_try is not None else True
        # ... 他のタイプ

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Action:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    # ファクトリメソッド
    @classmethod
    def empty(cls) -> Action:
        return cls(type="empty", value="")

    @classmethod
    def command(cls, value: str, undo: bool = True, context: str | None = None) -> Action:
        return cls(type="command", value=value, undo=undo, context=context)
```

**チェックリスト**:
- [ ] `Action` クラス
- [ ] `MenuItemSchema` クラス
- [ ] `HotkeySchema` クラス
- [ ] `MenuSchema` クラス
- [ ] `PME2File` クラス
- [ ] 各タイプの `to_dict()` / `from_dict()`
- [ ] ファクトリメソッド

---

### Phase 9-B: コンバーター実装

**ソース**: `pme_mini/infra/converter.py` をベースに

```python
# infra/converter.py

MODE_MAP = {
    "COMMAND": "command",
    "CUSTOM": "custom",
    "PROP": "prop",
    "MENU": "menu",
    "HOTKEY": "hotkey",
    "OPERATOR": "operator",
    "EMPTY": "empty",
}

def detect_pme_version(data: dict | list) -> str:
    """PME データのバージョンを検出"""
    if isinstance(data, dict) and data.get("$schema") == "PME2":
        return "PME2"
    if isinstance(data, dict) and "menus" in data:
        menus = data.get("menus", [])
        if menus and isinstance(menus[0], list):
            if len(menus[0]) >= 11:
                return "PME1.19"
            return "PME1.13"
    if isinstance(data, list):
        return "PME1.old"
    return "unknown"

def convert_pme1_file(data: dict | list) -> PME2File:
    """PME1 ファイルを PME2File に変換"""
    ...

def parse_icon_flags(icon_str: str) -> tuple[str, bool, bool]:
    """アイコン文字列からフラグを分離"""
    ...

def parse_data_string(data: str) -> dict[str, Any]:
    """data 文字列を settings dict に変換"""
    ...
```

**チェックリスト**:
- [ ] `detect_pme_version()`
- [ ] `convert_pme1_file()`
- [ ] `convert_pme1_menu()`
- [ ] `convert_pme1_item()`
- [ ] `parse_icon_flags()`
- [ ] `parse_hotkey_string()`
- [ ] `parse_data_string()`
- [ ] `build_action()`

---

### Phase 9-C: シリアライザー実装

```python
# infra/serializer.py

import json
from datetime import datetime
from typing import Any

from ..core.schemas import PME2File, MenuSchema
from .converter import detect_pme_version, convert_pme1_file


def export_v2(menus: list, tags: list[str] | None = None) -> dict[str, Any]:
    """現在のメニューを PME2 JSON 形式でエクスポート"""
    pme2_file = PME2File(
        schema="PME2",
        version="2.0.0",
        exported_at=datetime.utcnow().isoformat() + "Z",
        menus=[menu_to_schema(m) for m in menus],
        tags=tags or [],
    )
    return pme2_file.to_dict()


def import_json(data: dict | list) -> PME2File:
    """JSON データをインポート（v1/v2 自動判別）"""
    version = detect_pme_version(data)

    if version == "PME2":
        return PME2File.from_dict(data)

    # PME1 形式は変換
    return convert_pme1_file(data)


def menu_to_schema(pm) -> MenuSchema:
    """PMItem PropertyGroup を MenuSchema に変換"""
    # 既存の PMItem から MenuSchema を生成
    ...


def schema_to_menu(schema: MenuSchema, pm) -> None:
    """MenuSchema を PMItem PropertyGroup に適用"""
    # MenuSchema の内容を既存の PMItem に書き戻す
    ...
```

**チェックリスト**:
- [ ] `export_v2()` — 新形式エクスポート
- [ ] `import_json()` — v1/v2 デュアルインポート
- [ ] `menu_to_schema()` — PMItem → MenuSchema
- [ ] `schema_to_menu()` — MenuSchema → PMItem
- [ ] エラーハンドリング

---

### Phase 9-D: 既存 I/O との統合

```python
# infra/io.py の修正

def import_from_file(filepath: str) -> dict:
    """ファイルからインポート（v1/v2 自動判別）"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    from .serializer import import_json
    pme2_file = import_json(data)

    # 既存の処理に渡す
    return pme2_file_to_legacy_format(pme2_file)


def export_to_file(filepath: str, menus: list, format: str = "v2") -> None:
    """ファイルにエクスポート"""
    if format == "v2":
        from .serializer import export_v2
        data = export_v2(menus)
    else:
        # 既存の v1 形式
        data = legacy_export(menus)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
```

**チェックリスト**:
- [ ] `WM_OT_pm_import` の修正
- [ ] `WM_OT_pm_export` の修正
- [ ] エクスポート形式の選択 UI
- [ ] エラーメッセージの日本語/英語対応

---

## 3. テスト計画

### 3.1 ユニットテスト（Blender 外）

```python
# tests/test_schemas.py

def test_action_command():
    action = Action.command("bpy.ops.mesh.primitive_cube_add()")
    d = action.to_dict()
    assert d["type"] == "command"
    assert d["undo"] == True

def test_roundtrip():
    original = PieMenuSchema(name="Test", radius=100)
    d = original.to_dict()
    restored = PieMenuSchema.from_dict(d)
    assert original.name == restored.name
    assert original.radius == restored.radius
```

### 3.2 統合テスト（Blender 内）

1. **往復変換テスト**
   - 既存メニューを v2 エクスポート
   - 新規 Blender でインポート
   - 動作確認

2. **PME1 インポートテスト**
   - 1.19.x の JSON をインポート
   - 変換後のメニューが動作するか

3. **エッジケース**
   - 空のメニュー
   - 全スロット空の Pie Menu
   - 特殊文字を含むメニュー名
   - 非常に長いスクリプト

---

## 4. 移行のリスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| 変換ロス | ユーザーデータ破損 | v1 インポートは常に可能に |
| パフォーマンス | 起動時間増加 | 変換は必要時のみ |
| UI 混乱 | ユーザーが迷う | 形式選択のデフォルトを明確に |

---

## 5. スケジュール案

| 週 | タスク | 成果物 |
|----|--------|--------|
| Week 1 | 9-A: dataclass 定義 | `core/schemas/` |
| Week 1 | 9-B: コンバーター | `infra/converter.py` |
| Week 2 | 9-C: シリアライザー | `infra/serializer.py` |
| Week 2 | 9-D: I/O 統合 | `infra/io.py` 修正 |
| Week 3 | テスト & 修正 | テスト結果 |
| Week 3 | ドキュメント | マイグレーションガイド |

---

## 6. 参照実装

| ファイル | 内容 |
|---------|------|
| `pme_mini/core/schemas.py` | dataclass 定義の参照実装 |
| `pme_mini/infra/converter.py` | コンバーターの参照実装 |
| `pme_mini/core/protocols.py` | Protocol 定義（将来用） |

---

## 7. 完了条件

- [ ] `core/schemas/` が実装されている
- [ ] `infra/converter.py` が実装されている
- [ ] `infra/serializer.py` が実装されている
- [ ] v2 形式でエクスポートできる
- [ ] v1/v2 両方の形式をインポートできる
- [ ] 既存メニューの往復変換テストが通る
- [ ] Blender 5.0+ で動作確認

---

*このガイドは実装の進行に応じて更新されます。*
