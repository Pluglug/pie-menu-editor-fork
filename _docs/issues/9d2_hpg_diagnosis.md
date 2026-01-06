# 9-D-2: type=hpg の謎 - 診断結果

> **調査日**: 2026-01-07
> **ブランチ**: `investigate/9d2-hpg-mystery`
> **関連 Issue**: #88

---

## 診断結果

### 原因

`type=hpg` が出る原因は **2 つの問題の組み合わせ** です:

#### 問題 1: HPANEL メニューの `pm.data` が `hpg?` になっている

```python
# editors/hpanel_group.py:74
self.default_pmi_data = "hpg?"

# editors/base.py:262-264
def init_pm(self, pm):
    if not pm.data:
        pm.data = self.default_pmi_data  # ← ここで pm.data = "hpg?" が設定される
```

`default_pmi_data` は本来「アイテム用のデフォルトデータ」ですが、`EditorBase.init_pm()` がこれを「メニューのデータ」にも使用しています。

#### 問題 2: `extend_target` は `pg` タイプにのみ登録されている

```python
# editors/panel_group.py:688 (work/phase9d-io ブランチ)
schema.StringProperty("pg", "extend_target", "")
# → "hpg" タイプには未登録！
```

#### 発生フロー

1. HPANEL メニューの `pm.extend_target` にアクセス
2. `get_data("extend_target")` が呼ばれる (`pme_types.py:610`)
3. `schema.parse("hpg?...")` で `ParsedData(type="hpg")` が生成される
4. `__init__` では `extend_target` が設定されない（`hpg` タイプに未登録）
5. `getattr(parsed_data, "extend_target")` で `__getattr__` がトリガー
6. `prop_map` に `extend_target` が存在するので警告が出る (`core/schema.py:278`)

---

### 正しい状態

| モード | メニュー (`pm.data`) | アイテム (`pmi.text` prefix) | `extend_target` 必要？ |
|--------|---------------------|------------------------------|----------------------|
| PANEL | `pg?` | `pg?` | ✅ はい |
| HPANEL | `hp?` または `hpg?` | `hpg?` | ❌ いいえ（パネルを隠すだけ） |

**HPANEL は「パネルを隠す」機能であり、「拡張する」機能ではないため、`extend_target` は不要です。**

---

### データ不整合の有無

**コードの問題（データ不整合ではない）:**

1. `default_pmi_data` がメニューとアイテム両方に使われている設計上の混乱
2. `extend_target` が PANEL 専用なのに、HPANEL メニューからもアクセスされる

---

### 推奨対策（参考）

| 対策 | 説明 | リスク |
|------|------|--------|
| **A. HPANEL のプレフィックスを `hp` に変更** | `default_pmi_data = "hp?"` に修正、またはメニュー用の `default_pm_data` を別途定義 | 既存データとの互換性 |
| **B. `extend_target` を PANEL/HPANEL 両方に登録** | `schema.StringProperty("hpg", "extend_target", "")` を追加 | 不要なプロパティが HPANEL に追加される |
| **C. HPANEL から `extend_target` アクセスをガード** | `PMItem.extend_target` の getter で mode チェック | 一時的な回避策 |
| **D. メニューとアイテムのプレフィックスを分離** | `default_pm_data` と `default_pmi_data` を別々に定義 | 大きなリファクタリング |

**推奨**: **対策 A** - HPANEL のメニュープレフィックスを明確に定義し、`extend_target` は PANEL 専用として維持。

---

## 調査詳細

### 確認したファイル

| ファイル | 確認内容 |
|----------|----------|
| `core/schema.py:268-278` | `ParsedData.__getattr__()` - 警告発生箇所 |
| `editors/hpanel_group.py:74` | `default_pmi_data = "hpg?"` |
| `editors/panel_group.py:683-688` | `pg` タイプのプロパティ登録 |
| `editors/base.py:262-264` | `init_pm()` で `pm.data` を設定 |
| `pme_types.py:606-612` | `extend_target` プロパティ定義 |
| `pme_types.py:905-910` | `get_data()` / `set_data()` 実装 |

### Schema 登録状況

**登録されているタイプ**: `pm`, `rm`, `pg`, `mo`, `sk`, `s`, `prop`, `row`, `spacer`, `pd`

**登録されていないタイプ**: `hp`, `hpg`

### プレフィックス対応表

| モード | UID_PREFIX (converter.py) | default_pmi_data | schema 登録 |
|--------|---------------------------|------------------|-------------|
| PMENU | `pm` | - | `pm` ✅ |
| RMENU | `rm` | - | `rm` ✅ |
| DIALOG | `pd` | - | `pd` ✅ |
| PANEL | `pg` | `pg?` | `pg` ✅ |
| HPANEL | `hp` | `hpg?` ⚠️ | なし ❌ |
| MODAL | `md` | - | `mo` ✅ |

**不整合**: HPANEL の UID_PREFIX は `hp` だが、`default_pmi_data` は `hpg?`。

---

## 結論

`type=hpg` の謎は解明されました。これは HPANEL モードの設計上の不整合であり、`default_pmi_data` がメニューとアイテム両方に使われていることが原因です。

修正は Issue #88 の一部として、Phase 9-D の I/O 実装と合わせて行うべきです。
