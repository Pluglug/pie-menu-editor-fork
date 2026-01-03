---
title: Testing Procedures
status: stable
last_updated: 2026-01-01
---

# rules/testing.md

## 1. 手動テスト（毎回やる最低ライン）

変更のたびに実行する「固定コース」。

### 1.1 アドオン有効化テスト

- [ ] 新規 Blender（5.0+）を起動
- [ ] PME2 を有効化してエラーが出ない
- [ ] Preferences パネルが表示される
- [ ] コンソールに Python エラーがない

### 1.2 基本操作テスト

- [ ] 既存の Pie Menu を 1 つ呼び出して動く
- [ ] 新規 Pie Menu を作成
  - 項目を 1 つ追加
  - ホットキーを設定
  - 呼び出しが動作する

### 1.3 永続化テスト

- [ ] Blender を再起動
- [ ] 作成した Pie Menu が残っている
- [ ] ホットキーが機能する

## 2. 追加テスト（特定の変更時）

### JSON / 設定フォーマットを触ったとき

- [ ] JSON エクスポート → インポートで往復できる
- [ ] PME 1.19.x で作成した JSON を PME2 で読み込める

### ローダー / init_addon を触ったとき

- [ ] `DBG_DEPS=True` で起動してレイヤ違反がない
- [ ] `force_order=[]` で正常起動できる
- [ ] アドオン無効化 → 有効化でエラーが出ない

### Reload Scripts テスト（Phase 2-B Hotfix 適用後）

⚠️ **Hotfix 適用済み** (v2.0.0-alpha.2)

Phase 2-B で以下のホットフィックスが適用されました:

| Issue | 問題 | 対策 |
|-------|------|------|
| #64 | `ParsedData.pm_flick` などの属性エラー | `ParsedData.__getattr__` でフォールバックデフォルト値を返す |
| #65 | カスタムアイコンが読み込まれない | `previews_helper` に try-except ガードを追加 |

**テスト手順**:

1. **Reload Scripts の実行**
   - [ ] F3 → 「Reload Scripts」を実行
   - [ ] Python コンソールにクラッシュなし（警告ログは許容）

2. **Preferences 画面の確認**
   - [ ] Edit → Preferences → Add-ons → Pie Menu Editor を開く
   - [ ] パネルが表示される（アイコンが出なくても許容）
   - [ ] PM リストが表示される

3. **基本的な Pie 呼び出し**
   - [ ] 既存の Pie Menu をホットキーで呼び出す
   - [ ] 項目をクリックして動作する

**期待される警告ログ** (正常動作):
```
PME: fallback default used type=PMENU prop=pm_flick default=True
PME: previews refresh failed (icons may not display) ...
```

**クラッシュする場合**:
- コンソールのトレースバックを Issue に報告
- Phase 3 でライフサイクルを再設計予定

### PropertyGroup / クラス構造を触ったとき

- [ ] 既存の設定データが読み込める
- [ ] 新しいプロパティがデフォルト値で初期化される

## 3. デバッグフラグの使い方

### 依存解析・ロード順の確認

```python
# Blender Python コンソールで
from pie_menu_editor.debug_utils import set_debug_flag
set_debug_flag("deps", True)
set_debug_flag("structured", True)  # NDJSON 出力も必要な場合
```

- Mermaid 形式でモジュール順序が出力される
- レイヤ違反があれば警告表示

### パフォーマンス計測

```python
set_debug_flag("profile", True)
```

- `init_addon` の各フェーズの所要時間が出力される

## 4. 自動テスト（将来）

### 導入条件

- `core/` 層が分離され、bpy 非依存のコードが存在するようになったら

### 対象候補

| 対象 | テスト内容 |
|------|-----------|
| `property_utils.to_dict` / `from_dict` | ラウンドトリップ |
| JSON パース / シリアライズ | 形式の整合性 |
| `compatibility_fixes` | マイグレーション関数の単体テスト |

### pytest 構成（予定）

```
tests/
├── test_property_utils.py
├── test_json_compat.py
└── test_compatibility.py
```

## 5. テストを実行すべきタイミング

| 変更内容 | 必須テスト |
|----------|-----------|
| レイヤ間でファイルを移動 | 有効化 + ローダー |
| PropertyGroup のフィールド変更 | 有効化 + 永続化 + JSON |
| `__init__.py` のロード順変更 | 有効化 + ローダー |
| UI レイアウト変更 | 有効化 + 基本操作 |
| runtime / modal 系オペレーター | 有効化 + 基本操作 + 呼び出し |
