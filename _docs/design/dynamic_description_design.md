# Dynamic Description System Design

> **Status**: Planning
> **Related Issue**: #102
> **Created**: 2026-01-15

## 1. Background

### 発見

Blender は `description(cls, context, properties)` クラスメソッドをサポートしており、
オペレーターのプロパティに基づいて動的に tooltip を生成できる。

```python
@classmethod
def description(cls, context, properties):
    # properties.xxx でオペレーターのプロパティにアクセス
    # context で現在の Blender 状態にアクセス
    return "Dynamic tooltip"
```

### 実験結果

- `PME_OT_invoke_macro` に実装 → 成功
- `WM_OT_pme_user_pie_menu_call` に実装 → 成功
- 複数ボタン同時表示でもそれぞれ正しい tooltip が表示される

---

## 2. 調査対象: PME ラッパーオペレーター

### 主要なラッパー（要調査）

| オペレーター | 用途 | プロパティ | description() 効果 |
|-------------|------|-----------|-------------------|
| `WM_OT_pme_user_pie_menu_call` | PM 呼び出し | `pie_menu_name`, `slot` | 全 PM タイプに効く |
| `PME_OT_exec` | コマンド実行 | `cmd` | 困難（任意のコード） |
| `WM_OT_pme_hotkey_call` | ホットキー呼び出し | ? | 要調査 |
| `PME_OT_invoke_macro` | マクロ呼び出し | `pm_name` | 実験で確認済み |

### 調査項目

- [ ] PME の全オペレーター一覧を作成
- [ ] 各オペレーターの properties を確認
- [ ] description() 追加の効果範囲を分析
- [ ] 最小実装（最大効果）のオペレーターを特定

---

## 3. ユーザーニーズ

### 主要なユースケース

1. **UI ウィジェットへのメニュー登録**
   - ツールバーにボタンを追加
   - サイドバーにボタンを追加
   - カスタムパネルにボタンを追加
   - → tooltip でメニューの説明を表示したい

2. **F3 検索**
   - `INTERNAL` オプションのオペレーターは検索対象外
   - → 影響なし（または意図的に対象にするか？）

3. **コンテキストメニュー**
   - 右クリックメニューにアイテム追加
   - → tooltip が表示されるか要確認

### 必要な description レベル

| レベル | 対象 | 用途 |
|--------|------|------|
| PM (Menu) | `PMItem` | メニュー全体の説明 |
| PMI (Item) | `PMIItem` | 個々のアイテムの説明 |

**疑問**: PMI レベルの description は必要か？
- slot を直接呼び出すケースがどれくらいあるか
- PMI には既に `name` があるが、より詳細な説明が必要か

---

## 4. 設計選択肢

### Option A: WM_OT_pme_user_pie_menu_call のみ

**変更**: 1 オペレーターに description() 追加

**効果**:
- 全 PM タイプに description 機能
- PMItem.description フィールドを使用

**メリット**:
- 最小の変更
- 最大の効果

**デメリット**:
- PMI レベルの description は非対応

### Option B: Option A + PMI 対応

**追加変更**:
- `PMIItem.description` フィールド追加
- `slot >= 0` の場合に PMI の description を返す

**メリット**:
- より細かい制御

**デメリット**:
- PMIItem の変更が必要
- UI で description を設定する手段が必要

### Option C: Option A + PME_OT_invoke_macro

**追加変更**:
- マクロ専用のラッパーを維持

**疑問**:
- `WM_OT_pme_user_pie_menu_call` でマクロも呼べるのに、
  別のラッパーが必要か？

---

## 5. 次のステップ

### Phase 1: 調査

- [ ] PME の全オペレーター一覧
- [ ] 各オペレーターの用途と properties
- [ ] どのオペレーターが UI 登録で使われるか

### Phase 2: 設計決定

- [ ] 最小実装を決定
- [ ] PMI レベル対応の要否を決定
- [ ] `PME_OT_invoke_macro` の要否を決定

### Phase 3: 実装

- [ ] 設計に基づいて実装
- [ ] テスト
- [ ] ドキュメント更新

---

## 6. 参考資料

### Blender API

- [Operator.description()](https://docs.blender.org/api/current/bpy.types.Operator.html)
- [Dynamic operator description - Interplanety](https://b3d.interplanety.org/en/dynamic-operator-description/)

### PME 関連ファイル

- `operators/__init__.py` - メインのオペレーター定義
- `operators/macro.py` - マクロラッパー（実験で作成）
- `pme_types.py` - PMItem, PMIItem 定義

---

## 7. 実験コードの記録

### 実験 1: PME_OT_invoke_macro

```python
# operators/macro.py (新規作成)
class PME_OT_invoke_macro(Operator):
    bl_idname = "pme.invoke_macro"
    pm_name: StringProperty()

    @classmethod
    def description(cls, context, properties):
        pr = get_prefs()
        pm = pr.pie_menus.get(properties.pm_name)
        if pm and pm.description:
            return pm.description
        return f"Execute {properties.pm_name} macro"

    def execute(self, context):
        execute_macro(pm)
        return {'FINISHED'}
```

### 実験 2: WM_OT_pme_user_pie_menu_call

```python
# operators/__init__.py に追加
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

両方とも動作確認済み。
