# 9-D-4: Editor.export/import_settings() 設計調査

> **ブランチ**: `investigate/9d4-editor-io`
> **関連 Issue**: #88
> **目的**: 設計判断のための情報収集。実装は行わない。

---

## ワークツリー

**作業前に必ずワークツリーに移動してください。**

```
ワークツリー: E:/0339_Blender version archive/blender-5.0.1-D/portable/scripts/addons/pie_menu_editor
Blender起動: E:/0187_Pie-Menu-Editor/common_scripts_dir/blender_D.cmd
```

```bash
cd "E:/0339_Blender version archive/blender-5.0.1-D/portable/scripts/addons/pie_menu_editor"
git status  # investigate/9d4-editor-io であることを確認
```

---

## 背景

Phase 9-D で `infra/serializer.py` にすべてのモード固有ロジックが集中した。

```python
# serializer.py の現状
if pm.mode == 'PROPERTY':
    settings['prop_type'] = pm.poll_cmd
    poll = "return True"
if pm.mode in ('PANEL', 'HPANEL'):
    extend_target = getattr(pm, 'extend_target', None)
```

**問題提起**: 各 Editor がモード固有の I/O ロジックを持つべきでは？

```python
# 提案パターン
class EdProperty(EditorBase):
    def export_settings(self, pm) -> dict:
        return {'prop_type': pm.poll_cmd, ...}
```

## 調査タスク

### 1. 現在の Editor 構造を把握

**主戦場**: `editors/` ディレクトリ

| Editor | ファイル | 特殊な I/O 処理が必要か |
|--------|----------|------------------------|
| Pie Menu | `pie_menu.py` | ? |
| Menu | `menu.py` | ? |
| Dialog | `popup.py` | ? |
| Panel Group | `panel_group.py` | ? |
| Hidden Panel | `hpanel_group.py` | ? |
| Stack Key | `stack_key.py` | ? |
| Macro | `macro.py` | ? |
| Modal | `modal.py` | ? |
| Sticky Key | `sticky_key.py` | ? |
| Property | `property.py` | ✓ (poll_cmd 二重利用) |

**調査項目**:
- [ ] 各 Editor で `pm.data` の解釈が異なる箇所
- [ ] `pm.poll_cmd` の使い方が異なる箇所
- [ ] モード固有のフィールドの有無

### 2. EditorBase の責務を確認

**主戦場**: `editors/base.py`

**調査項目**:
- [ ] EditorBase が提供するメソッド一覧
- [ ] 現在の責務（UI 描画、データ検証、etc.）
- [ ] I/O メソッドを追加する余地

### 3. pm.ed のライフサイクルを確認

**問題**: import 時に `pm.ed` が存在するか？

**調査項目**:
- [ ] `pm.ed` がいつ設定されるか
- [ ] import 中に `pm.ed` にアクセスできるか
- [ ] できない場合、どうやって Editor を取得するか

**確認コード**:
```python
# pme_types.py で pm.ed がどう設定されるか確認
class PMItem(PropertyGroup):
    @property
    def ed(self):
        # この実装を確認
```

### 4. 代替設計案の検討

**選択肢**:

1. **Editor にメソッド追加**
   ```python
   class EditorBase:
       def export_settings(self, pm) -> dict:
           return parse_data_string(pm.data, pm.mode)  # デフォルト
   ```

2. **別ファイルに分離**
   ```
   infra/mode_settings/
     __init__.py
     property.py    # PROPERTY 固有
     panel.py       # PANEL/HPANEL 固有
   ```

3. **変換テーブル（データ駆動）**
   ```python
   MODE_SETTINGS = {
       'PROPERTY': {'poll_cmd_as': 'prop_type'},
       'PANEL': {'has_extend_target': True},
   }
   ```

4. **現状維持**
   - serializer 内で if 分岐

**調査項目**:
- [ ] 各選択肢のメリット/デメリット
- [ ] 他の Blender アドオンでの類似パターン
- [ ] PME の将来的な拡張性

### 5. 影響範囲の評価

**調査項目**:
- [ ] Editor にメソッド追加した場合の変更ファイル数
- [ ] テストの容易さ
- [ ] 後方互換性への影響

## やらないこと

- 設計の決定
- コードの実装
- 他の調査タスクとの統合

## 成果物

調査結果を以下の形式でまとめる：

```markdown
## 診断結果

### 現状の責務分布
[serializer vs Editor でどう分かれているか]

### モード固有処理の一覧
| モード | 固有処理 | 現在の場所 |
|--------|---------|-----------|
| PROPERTY | poll_cmd → prop_type | serializer |
| PANEL | extend_target | serializer |
| ... | | |

### pm.ed のタイミング
[import 時にアクセス可能か]

### 設計選択肢の評価
| 選択肢 | メリット | デメリット | 推奨度 |
|--------|---------|-----------|--------|
| Editor メソッド | | | |
| 別ファイル | | | |
| データ駆動 | | | |
| 現状維持 | | | |

### 推奨（参考）
[調査に基づく推奨案]
```
