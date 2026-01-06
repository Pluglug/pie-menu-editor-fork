# 9-D-1: PROPERTY mode クラッシュ調査

> **ブランチ**: `investigate/9d1-property-crash`
> **関連 Issue**: #88
> **目的**: 診断のみ。修正は行わない。

---

## 背景

Phase 9-D (JSON Schema v2 I/O 統合) の往復テストで、PROPERTY mode メニューのインポート時にクラッシュが発生した。

```
AttributeError: module 'bpy.props' has no attribute 'Return TrueProperty'

File "editors/property.py", line 372, in prop_by_type
    return getattr(bpy.props, name)
```

## 症状

- PROPERTY mode では `pm.poll_cmd` がプロパティタイプ (`BOOL`, `INT`, `FLOAT`, `STRING`, `ENUM`) を格納する
- インポート後に `pm.poll_cmd` が `"Return True"` になっている
- `prop_by_type()` が `"Return True" + "Property"` → `"Return TrueProperty"` を探してクラッシュ

## 調査タスク

### 1. prop_by_type() の呼び出しフローを追跡

**主戦場**: `editors/property.py`

```
editors/property.py:369  prop_by_type()        ← クラッシュ箇所
editors/property.py:392  register_user_property()  ← 呼び出し元
editors/property.py:400  bpy_prop = prop_by_type(pm.poll_cmd, size > 1)
```

**調査項目**:
- [ ] `register_user_property()` がどこから呼ばれるか
- [ ] import 時の呼び出しタイミングを特定
- [ ] `pm.poll_cmd` がいつ設定されるか

### 2. PME1 の PROPERTY メニューの実データを確認

**やること**:
- [ ] ユーザーの v1 JSON から PROPERTY メニューを抽出
- [ ] `poll_cmd` フィールドの実際の値を確認
- [ ] 複数の PROPERTY メニューで値がどうなっているか

**確認コマンド** (Blender Python Console):
```python
from pie_menu_editor.addon import get_prefs
pr = get_prefs()
for pm in pr.pie_menus:
    if pm.mode == 'PROPERTY':
        print(f"{pm.name}: poll_cmd='{pm.poll_cmd}', data='{pm.data}'")
```

### 3. v2 エクスポート JSON を検証

**やること**:
- [ ] `work/phase9d-io` ブランチで v2 エクスポートした JSON を取得
- [ ] PROPERTY メニューの `settings` に `prop_type` が含まれているか確認
- [ ] `poll` フィールドの値を確認

### 4. serializer の PROPERTY 処理を確認

**主戦場**: `work/phase9d-io:infra/serializer.py`

```python
# Export 時
if pm.mode == 'PROPERTY':
    settings['prop_type'] = pm.poll_cmd if pm.poll_cmd else 'BOOL'
    poll = "return True"

# Import 時
if schema.mode == 'PROPERTY':
    pm.poll_cmd = schema.settings.get('prop_type', 'BOOL')
```

**調査項目**:
- [ ] Export 時に `settings.prop_type` が正しく設定されるか
- [ ] Import 時に `pm.poll_cmd` が正しく復元されるか
- [ ] どこで `"Return True"` が混入するか

## やらないこと

- 修正コードの実装
- 他のモードの調査
- 設計変更の提案

## 成果物

調査結果を以下の形式でまとめる：

```markdown
## 診断結果

### 原因
[poll_cmd が "Return True" になる原因]

### 発生箇所
[コード箇所と呼び出しフロー]

### 影響範囲
[この問題が影響する他の箇所]

### 推奨対策（参考）
[調査に基づく対策案。実装は別タスク]
```
