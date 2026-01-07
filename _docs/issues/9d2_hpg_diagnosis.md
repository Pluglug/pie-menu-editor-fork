# 9-D-2: type=hpg の謎 - 診断結果

> **調査日**: 2026-01-07 (初版), 2026-01-08 (改訂)
> **ブランチ**: `investigate/9d2-hpg-mystery`
> **関連 Issue**: #88, #89

---

## 診断結果 (改訂版)

### 真の原因: serializer の設計ミス

**初期診断** では `hpg?` プレフィックスの問題と考えていましたが、深い調査により**真の原因は serializer が HPANEL に不適切に `extend_target` を要求したこと**と判明しました。

```python
# work/phase9d-io:infra/serializer.py:109-114 (問題箇所)
if pm.mode in ('PANEL', 'HPANEL'):  # ← HPANEL を含めるべきではない！
    extend_target = getattr(pm, 'extend_target', None)
```

**HPANEL は「パネルを隠す」機能であり、「拡張する」機能ではありません。**

### 修正案

```python
# 正しい実装
if pm.mode in ('PANEL', 'DIALOG', 'RMENU'):  # extend 系モードのみ
    extend_target = getattr(pm, 'extend_target', None)
```

---

## HPANEL の特殊性

### 発見: HPANEL は pm.data を使用しない

詳細な調査により、以下が判明:

| 確認項目 | 結果 |
|----------|------|
| HPANEL Editor が `schema.parse()` を呼ぶか | ❌ 呼ばない |
| HPANEL Editor が `get_data()`/`set_data()` を呼ぶか | ❌ 呼ばない |
| 他コードが HPANEL の pm.data をパースするか | ❌ しない |
| `has_extra_settings` フラグ | `False` |

**結論**: `default_pmi_data = "hpg?"` は**事実上デッドコード**です。

### HPANEL のデータ構造

```python
# HPANEL が実際に使用するデータ
pm.name      # ユーザー定義の「隠すパネルグループ」名
pm.pmis[]    # 隠すパネルのリスト
  .text      # Blender パネル ID (例: "VIEW3D_PT_tools")
  .name      # 表示名

# HPANEL が使用しないデータ
pm.data      # 設定されるが読まれない ("hpg?")
```

---

## プレフィックス問題の再評価

### 正式実装の確認

`hpg?` は **PME v1 の正式実装** です（Initial commit から存在）。

| モード | 正式実装 (PME v1) | converter.py |
|--------|-------------------|--------------|
| PANEL | `pg?` | `pg` ✅ |
| HPANEL | **`hpg?`** ✅ | `hp` ❌ **誤り** |

### 修正が必要な箇所

converter.py の `hp` が誤った推測であり、正式実装 `hpg` に修正すべきです：

| 場所 | 現状 (誤り) | 修正後 |
|------|-------------|--------|
| `infra/converter.py` UID_PREFIX | `'HPANEL': 'hp'` | `'HPANEL': 'hpg'` |
| `infra/converter.py` prefix_map | `'HPANEL': 'hp_'` | `'HPANEL': 'hpg_'` |

### 推奨対応

| 優先度 | アクション | 理由 |
|--------|-----------|------|
| **P0** | serializer から HPANEL を除外 | 設計ミスの修正 |
| **P0** | converter の `hp` → `hpg` | PME v1 正式実装との整合 |

---

## #89 との関係

Issue #89 は「pm.data が settings キャリア」と定義していますが、**HPANEL は例外**です。

### 追記すべき内容

```markdown
### HPANEL Mode Exception

HPANEL does NOT use `pm.data` for settings. It stores:
- `pm.name`: User-defined group name
- `pm.pmis[].text`: Blender panel IDs to hide

**Serializer must NOT:**
- Include HPANEL in `extend_target` handling
- Register schema properties for "hpg" or "hp" types

**JSON v2 for HPANEL:**
{
  "uid": "hpg_abc123",   // 正式プレフィックス: hpg
  "name": "My Hidden Panels",
  "mode": "HPANEL",
  "settings": {},  // Always empty
  "items": [{"text": "VIEW3D_PT_tools"}]
}
```

---

## 初期診断の振り返り

### 初期診断 (2026-01-07)

> `type=hpg` が出る原因は `default_pmi_data = "hpg?"` と `extend_target` の `pg` 専用登録の組み合わせ

### 改訂診断 (2026-01-08)

> 真の原因は **serializer が HPANEL に `extend_target` を不適切に要求したこと**。
> プレフィックス問題は表面的な症状であり、根本原因ではない。

**"Amicus Plato, sed magis amica veritas"** - 初期診断を修正し、真の原因を特定。

---

## 調査詳細

### 確認したファイル

| ファイル | 確認内容 |
|----------|----------|
| `editors/hpanel_group.py` | Editor 実装、`has_extra_settings=False` |
| `editors/base.py:262-264` | `init_pm()` で `pm.data` を設定 |
| `work/phase9d-io:infra/serializer.py:109-114` | **HPANEL 含む extend_target 処理 (バグ)** |
| `work/phase9d-io:infra/converter.py` | UID_PREFIX['HPANEL'] = 'hp' |
| `operators/__init__.py` | モードチェック後にプロパティアクセス (正しいパターン) |

### キーファインディング

1. **HPANEL Editor は pm.data を一切読み書きしない**
2. **既存コードはモードチェック後にモード固有プロパティにアクセスする**
3. **serializer のみが全モードに一律で extend_target を要求していた**

---

## 結論

`type=hpg` 警告の謎は完全に解明されました。

| 問題 | 対応 |
|------|------|
| serializer の HPANEL 含有 | **修正必須** (1行変更) |
| converter の `hp` (誤り) | **修正必須** → `hpg` に変更 |

### 修正アクション

1. **serializer.py**: HPANEL を extend_target 対象から除外
2. **converter.py**: `UID_PREFIX['HPANEL']` = `'hpg'`, `prefix_map['HPANEL']` = `'hpg_'`

**`hpg?` は PME v1 の正式実装であり、維持すべきです。**
