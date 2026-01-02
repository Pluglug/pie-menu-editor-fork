# Core Layer Design (Phase 3)

Core 層の設計文書。Issue #64 の根本解決を目指す。

---

## ステータス

**Phase 3 (Core Layer Sprint) の設計準備段階**

- `pme.py` の LAYER を "core" に変更済み
- 本格的な設計作業は次のステップで実施

---

## 背景

### Issue #64 の本質

`ParsedData` / `props` 登録問題の根本原因:

1. **スキーマの所有権が不明確**: props 登録が 8 ファイルに散在
2. **ライフサイクルが暗黙的**: モジュールレベルで副作用が発生
3. **レイヤ割り当ての誤り**: `pme.py` は `LAYER="infra"` だったが実質 core の責務

### 現状の回避策とその問題

| 回避策 | 問題点 |
|--------|--------|
| `_FALLBACK_DEFAULTS` | 39 プロパティの重複定義、手動メンテナンス必要 |
| Sprint 0 の `pp` → `pme.props` 修正 | ロード順序問題は残存 |
| キャッシュクリア案 | 症状への対処、原因への対処ではない |

---

## 現在の pme.py の責務

`pme.py` が現在持っている責務:

| クラス/関数 | 責務 | 本来のレイヤ |
|------------|------|-------------|
| `PMEContext` | 実行コンテキスト管理 | core |
| `PMEProps` | プロパティスキーマ管理 | core |
| `ParsedData` | シリアライズデータのパース | core |
| `props` | グローバルスキーマレジストリ | core |
| `context` | グローバル実行コンテキスト | core |

---

## 検討事項

### 1. `core/schema.py` の導入

**目的**: スキーマ定義の一元化

**現行（命令的登録）**:
```python
# editors/pie_menu.py (モジュールレベル)
pme.props.IntProperty("pm", "pm_radius", -1)
pme.props.BoolProperty("pm", "pm_flick", True)
```

**案（宣言的定義）**:
```python
# core/schema.py
PM_SCHEMA = {
    'pm_radius': {'type': 'INT', 'default': -1},
    'pm_flick': {'type': 'BOOL', 'default': True},
}
```

**検討ポイント**:
- 既存コードとの互換性
- Editor との連携方法
- マイグレーションパス

### 2. `core/registry.py` の導入

**目的**: ライフサイクル管理の明示化

**検討ポイント**:
- `register()` / `unregister()` での明示的管理
- キャッシュのクリアポイント
- 遅延初期化の可能性

### 3. `_FALLBACK_DEFAULTS` の扱い

**選択肢**:
1. **削除**: スキーマ一元化により不要になる
2. **縮小**: 最小限のセーフティネットとして維持
3. **自動生成**: スキーマから自動生成

---

## 依存関係の整理

### pme.py → core への変更による影響

ユーザー提供のログより（LAYER="core" に変更後）:

```
[deps], Layer violations: 21
  core <- infra : pme imports debug         # debug は infra 層
  core <- infra : constants imports previews_helper
  core <- operators : pme_types imports operators
  core <- infra : pme_types imports ui
  ...
```

**対処方針**:
- `pme.py` から `infra/debug.py` への依存は許容（ログ出力のみ）
- または `DBG_RUNTIME` を core 層に移動

---

## 次のステップ

1. **詳細設計**: スキーマ構造、レジストリ API の決定
2. **プロトタイプ**: `pm` スキーマで検証
3. **移行計画**: 既存コードからの段階的移行

---

## 参照

- Issue #64: https://github.com/Pluglug/pie-menu-editor-fork/issues/64
- Issue #67: https://github.com/Pluglug/pie-menu-editor-fork/issues/67
- `rules/milestones.md` — Phase 3 計画
- `rules/api/pme_api_current.md` — 現状の pme API インベントリ
