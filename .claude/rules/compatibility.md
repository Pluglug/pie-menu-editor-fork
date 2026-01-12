---
title: Compatibility Policy
status: stable
last_updated: 2026-01-13
---

# rules/compatibility.md

## 1. 対応 Blender バージョン

| ブランチ | 対応バージョン | 備考 |
|---------|---------------|------|
| PME2 (pme2-dev) | **Blender 5.0 以降専用** | 4.x 互換コードは段階的に削除 |
| PME1 (main) | Blender 4.2 LTS 〜 4.x 系 | 5.x は「動けばラッキー」 |

## 2. データ互換性ポリシー

### 2.1 Must Keep（絶対維持）

- **PME 1.19.x 系で出力された JSON / backup**
  - PME2 (2.0.0) で読み込めること
  - 読み込み時にマイグレーション処理が走るのは OK
  - 内部表現が変わるのも OK

### 2.2 May Break（破壊許容）

- **1.18.x 以前の JSON / backup**
  - 読めなくなっても「仕様」とする
- **エクスポートする JSON のフォーマット**
  - PME2 で変わってよい（ただし 1.19.x 形式は読み込めること）
- **UI レイアウトやパネル構成**
  - PME1 と一致している必要はない
- **内部クラス名・bl_idname**
  - 必要に応じて変更可（ユーザーのショートカットが壊れる可能性は許容）

## 3. 古いバージョンガードの扱い

### 削除手順

1. `DBG_INIT` を有効化して Blender 5.x で起動
2. `if APP_VERSION < (5, 0, 0):` の分岐が通っていないことをログで確認
3. 通っていないことが確認できたら削除

### 削除優先順位

| 優先度 | 対象 | 備考 |
|--------|------|------|
| 高 | `if APP_VERSION < (5, 0, 0):` | 即削除候補 |
| 中 | `if APP_VERSION < (4, 2, 0):` | 4.2 LTS 未満の互換コード |
| 低 | `if APP_VERSION < (4, 0, 0):` | 3.x 互換コード |

## 4. infra/compat.py の方針

> 旧名: `compatibility_fixes.py`

- **1.19.x → 2.0.0 のマイグレーションパス**のみ維持
- 1.17.x 未満の古い `fix_*` 関数は **2.0.0 リリース時に削除可**
- 新しいマイグレーションが必要な場合は `fix_2_0_0()` のような命名で追加

### 現在のマイグレーション関数

| 関数 | 用途 |
|------|------|
| `fix_2_0_0()` | Blender 起動時の PME1→PME2 マイグレーション |
| `fix_json_2_0_0()` | JSON v1 インポート時のマイグレーション |
| `_migrate_extend_target()` | Extend プロパティの pm.data 移行 |
| `_migrate_json_extend_target()` | JSON v1 の Extend プロパティ移行 |
