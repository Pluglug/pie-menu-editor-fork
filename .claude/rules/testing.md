# Testing Procedures (PME2)

## 基本テスト（毎回実施）

### 有効化テスト
- [ ] Blender 5.0+ で PME2 を有効化 → エラーなし
- [ ] Preferences パネルが表示される

### 基本操作
- [ ] Pie Menu を呼び出し → 動作する
- [ ] 新規作成 → ホットキー設定 → 呼び出し

### 永続化
- [ ] Blender 再起動後も設定が残る

## 特定の変更時

| 変更内容 | 追加テスト |
|----------|-----------|
| JSON/設定 | エクスポート→インポート往復 |
| ローダー | `DBG_DEPS=True` で違反チェック |
| Reload Scripts | F3 → Reload → クラッシュなし |

## デバッグフラグ

```python
# Blender コンソールで
from pie_menu_editor.debug_utils import set_debug_flag
set_debug_flag("deps", True)      # レイヤ違反検出
set_debug_flag("profile", True)   # 起動時間計測
```
