# 9-D-2: type=hpg の謎

> **ブランチ**: `investigate/9d2-hpg-mystery`
> **関連 Issue**: #88
> **目的**: 診断のみ。修正は行わない。

---

## 背景

Phase 9-D の v2 エクスポート時に以下の警告が発生：

```
PME: late-bound prop via __getattr__, type=hpg, prop=extend_target
```

## 疑問点

- `hpg` は HPANEL **アイテム** のデータプレフィックスのはず
- HPANEL **メニュー** のプレフィックスは `hp` のはず
- なぜメニューレベルで `type=hpg` が出るのか？

## データプレフィックスの想定

| モード | メニュー (pm.data) | アイテム (pmi.text prefix) |
|--------|-------------------|---------------------------|
| PMENU | `pm?` | `pm?` |
| PANEL | `pg?` | `pg?` |
| HPANEL | `hp?` | `hpg?` |

## 調査タスク

### 1. HPANEL メニューの pm.data を確認

**確認コマンド** (Blender Python Console):
```python
from pie_menu_editor.addon import get_prefs
pr = get_prefs()
for pm in pr.pie_menus:
    if pm.mode == 'HPANEL':
        print(f"{pm.name}: data='{pm.data}'")
        for pmi in pm.pmis:
            print(f"  - {pmi.name}: text='{pmi.text[:50]}...'")
```

**調査項目**:
- [ ] HPANEL メニューの `pm.data` が `hp?` か `hpg?` か
- [ ] 複数の HPANEL メニューで一貫しているか
- [ ] いつ `hpg?` が設定されるのか（バグ？仕様？）

### 2. late-bound prop 警告の発生箇所を特定

**主戦場**: `core/schema.py` (旧 `core/props.py`)

```python
def __getattr__(self, name):
    # この警告が出ている
    print(f"PME: late-bound prop via __getattr__, type={self.type}, prop={name}")
```

**調査項目**:
- [ ] `ParsedData.__getattr__()` の実装を確認
- [ ] どのオブジェクトの `__getattr__` が呼ばれているか
- [ ] `type=hpg` がどこから来ているか

### 3. extend_target の登録状況を確認

**調査項目**:
- [ ] `extend_target` プロパティがどのタイプに登録されているか
- [ ] `pg` (PANEL) にのみ登録されている？
- [ ] `hp` や `hpg` には登録されていない？

**確認コード**:
```python
from pie_menu_editor.core.schema import schema
print(schema._props)  # 登録されているプロパティ一覧
```

### 4. HPANEL Editor の実装を確認

**主戦場**: `editors/hpanel_group.py`

**調査項目**:
- [ ] HPANEL メニュー作成時に `pm.data` がどう設定されるか
- [ ] HPANEL アイテムと混同している箇所がないか
- [ ] `hpg` プレフィックスの使用箇所

### 5. converter の HPANEL 処理を確認

**主戦場**: `infra/converter.py`

**調査項目**:
- [ ] `parse_data_string()` で `hp` と `hpg` がどう扱われるか
- [ ] PME1 → PME2 変換時に問題がないか

## やらないこと

- 修正コードの実装
- extend_target の再設計
- 他のモードの調査

## 成果物

調査結果を以下の形式でまとめる：

```markdown
## 診断結果

### 原因
[type=hpg が出る原因]

### 正しい状態
[HPANEL メニュー/アイテムの pm.data/pmi.text はどうあるべきか]

### データ不整合の有無
[既存データに問題があるか、コードの問題か]

### 推奨対策（参考）
[調査に基づく対策案。実装は別タスク]
```
