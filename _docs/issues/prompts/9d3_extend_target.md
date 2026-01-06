# 9-D-3: extend_target 再設計調査

> **ブランチ**: `investigate/9d3-extend-target`
> **関連 Issue**: #88, #69
> **目的**: 診断のみ。設計変更は行わない。

---

## ワークツリー

**作業前に必ずワークツリーに移動してください。**

```
ワークツリー: E:/0339_Blender version archive/blender-5.0.1-C/portable/scripts/addons/pie_menu_editor
Blender起動: E:/0187_Pie-Menu-Editor/common_scripts_dir/blender_C.cmd
```

```bash
cd "E:/0339_Blender version archive/blender-5.0.1-C/portable/scripts/addons/pie_menu_editor"
git status  # investigate/9d3-extend-target であることを確認
```

---

## 背景

Phase 9-D で `extend_target` を MenuSchema のトップレベルフィールドにしたが、これが適切かどうか疑問が生じた。

### 現在の設計 (json_schema_v2.md)

```json
{
  "uid": "pg_abc123",
  "name": "My Panel Extension",
  "mode": "PANEL",
  "extend_target": "VIEW3D_PT_tools_active",  // ← トップレベル
  ...
}
```

### 問題点

1. `extend_target` は PANEL/HPANEL 専用？それとも他モードも使う？
2. `settings` に入れるべきだった？
3. `Menu.name` との関係性が不明確

## 調査タスク

### 1. extend_target の使用箇所を確認

**主戦場**: 全コードベース

```bash
rg "extend_target" --type py
```

**調査項目**:
- [ ] どのファイルで `extend_target` が参照されているか
- [ ] どのモードで使用されているか
- [ ] PME1 での元々の用途

### 2. PANEL/HPANEL の extend 機能を理解

**主戦場**:
- `editors/panel_group.py`
- `editors/hpanel_group.py`

**調査項目**:
- [ ] Panel Group が Blender パネルを「拡張」する仕組み
- [ ] `extend_target` が指すのは Blender の `bl_idname`？
- [ ] HPANEL でも同じ仕組みか

### 3. 他モードでの extend 可能性を確認

**調査対象**:
- RMENU: 既存 Blender メニューを拡張できる？
- DIALOG: 特定のダイアログに追加できる？

**調査項目**:
- [ ] PME1 で RMENU/DIALOG に extend 機能があったか
- [ ] 今後追加する可能性があるか

### 4. Menu.name との関係を整理

**問題**:
- Panel Group では `pm.name` が実質的に `bl_idname` の一部になる
- `extend_target` と `name` の役割分担が不明確

**調査項目**:
- [ ] `pm.name` がどう使われるか（表示名？ID？）
- [ ] `extend_target` との重複・衝突の可能性
- [ ] PME2 スキーマでどう整理すべきか

### 5. settings vs トップレベルの判断基準

**確認事項**:
- [ ] 他のモード固有フィールドはどこに配置されているか
- [ ] `settings` に入れる基準は何か
- [ ] トップレベルに残すメリット/デメリット

## やらないこと

- スキーマの変更
- コードの修正
- 新しい設計の実装

## 成果物

調査結果を以下の形式でまとめる：

```markdown
## 診断結果

### extend_target の現状
[どのモードで使われ、何を指しているか]

### 使用モード一覧
| モード | 使用 | 用途 |
|--------|------|------|
| PANEL | ✓/✗ | ... |
| HPANEL | ✓/✗ | ... |
| RMENU | ✓/✗ | ... |
| ... | | |

### 推奨配置
[トップレベル or settings、その理由]

### Menu.name との関係
[整理案]
```
