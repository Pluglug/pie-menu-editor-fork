# Dynamic Description Expansion

> **Issue**: #102 (拡張)
> **Branch**: `feature/macro-improvements`
> **Status**: In Progress

## Overview

Phase B で発見した `description()` クラスメソッドを、既存のラッパーオペレーターに適用し、
PME のほぼすべての PM/PMI に動的 description 機能を提供する。

## Background

### Phase B での発見

Blender は `description(cls, context, properties)` クラスメソッドをサポートしており、
オペレーターのプロパティに基づいて動的に tooltip を生成できる。

```python
@classmethod
def description(cls, context, properties):
    return f"Dynamic tooltip based on {properties.some_prop}"
```

### 既存のラッパーオペレーター

| オペレーター | 用途 | プロパティ |
|-------------|------|-----------|
| `WM_OT_pme_user_pie_menu_call` | PM 呼び出し | `pie_menu_name`, `slot` |
| `PME_OT_exec` | コマンド実行 | `cmd` |

---

## TODO

### Phase D-1: WM_OT_pme_user_pie_menu_call に description() 追加

**ファイル**: `operators/__init__.py`

**実装**:
```python
class WM_OT_pme_user_pie_menu_call(Operator):
    # ... 既存コード ...

    @classmethod
    def description(cls, context, properties):
        pr = get_prefs()
        pm = pr.pie_menus.get(properties.pie_menu_name)
        if not pm:
            return "Call PME menu"

        if pm.description:
            return pm.description
        return f"Call {pm.name}"
```

**状態**: [x] 完了

### Phase D-2: テスト

**テスト項目**:
- [ ] Pie Menu を UI に登録 → カスタム tooltip 表示
- [ ] Regular Menu を UI に登録 → カスタム tooltip 表示
- [ ] Popup Dialog を UI に登録 → カスタム tooltip 表示
- [ ] description 未設定時 → デフォルト "Call {name}" 表示
- [ ] 存在しないメニュー名 → "Call PME menu" 表示

**状態**: [ ] 未着手

### Phase D-3: PMI レベルの description（将来検討）

**課題**:
- `slot` プロパティで特定の PMI を呼び出す場合
- PMI にも description フィールドを追加すべきか？

**現状**: PM レベルの description のみ対応

**状態**: [ ] 保留

---

## 効果範囲

### 影響を受けるメニュータイプ

| タイプ | 効果 |
|--------|------|
| Pie Menu | ✅ |
| Regular Menu | ✅ |
| Popup Dialog | ✅ |
| Panel Group | ✅ |
| Sticky Key | ✅ |
| Modal | ✅ |
| Macro | ✅ (Phase B で対応済み) |
| Stack Key | ✅ |
| Property | ✅ |

### 影響を受けないもの

- `PME_OT_exec` - cmd は任意の Python コードなので description 推測困難
- F3 検索 - `bl_options = {'INTERNAL'}` なので検索対象外

---

## 関連ファイル

| ファイル | 変更内容 |
|----------|---------|
| `operators/__init__.py` | `WM_OT_pme_user_pie_menu_call` に description() 追加 |
| `pme_types.py` | `PMItem.description` (Phase A で追加済み) |

## 関連 Issue

- #102: Macro operator improvements（元 Issue）

---

## 進捗ログ

| 日付 | 内容 |
|------|------|
| 2026-01-15 | TODO ドキュメント作成、Phase D 計画開始 |
