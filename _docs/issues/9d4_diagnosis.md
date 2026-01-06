# 9-D-4 診断結果: Editor.export/import_settings() 設計調査

> **調査日**: 2026-01-07
> **調査者**: Claude (AI)
> **関連 Issue**: #88
> **ブランチ**: `investigate/9d4-editor-io`

---

## 診断結果

### 現状の責務分布

| 場所 | 責務 |
|------|------|
| **EditorBase** (`editors/base.py:181-749`) | UI 描画、イベントハンドリング、プロパティ登録、PMI 検証 |
| **各 Editor** | EditorBase を継承、モード固有の初期化・描画・イベント処理 |
| **serializer** (未実装/Phase 9-D) | すべてのモード固有 I/O ロジック集中（問題点） |
| **schema** (`core/schema.py`) | `pm.data` のパース・エンコード |

**現状の問題**: I/O ロジックが Editor に存在せず、serializer に全モードのロジックが集中する設計になっている。

---

### モード固有処理の一覧

| モード | データプレフィックス | 固有処理 | 複雑度 |
|--------|---------------------|---------|-------|
| **PROPERTY** | `prop?` | `poll_cmd` を `prop_type` として使用（二重利用） | **高** |
| PMENU | `pm?` | `pm_radius`, `pm_confirm`, `pm_threshold`, `pm_flick` | 低 |
| RMENU | `rm?` | `rm_title` | 低 |
| DIALOG | `pd?` | `pd_*` プロパティ、`row?`/`spacer?` レイアウト | 中 |
| PANEL | `pg?` | `pg_wicons`, `pg_context`, `pg_category`, `pg_space`, `pg_region` | 中 |
| **HPANEL** | `hpg?` | パネル名リスト（`extend_target` 相当） | 中 |
| STACK | `s?` | `s_undo`, `s_state` | 低 |
| STICKY | `sk?` | `sk_block_ui` | 低 |
| MODAL | `mo?` | `confirm`, `block_ui`, `lock` | 低 |
| MACRO | `m?` | なし（スキーマプロパティ未定義） | 低 |

#### PROPERTY モードの特殊性

```python
# editors/property.py:141-152
def ed_type_get(self):
    return get_prefs().selected_pm.poll_cmd  # ← poll_cmd を property type として読み取る

def ed_type_set(self, value):
    pm.poll_cmd = items[value].identifier  # ← poll_cmd に property type を書き込む
```

`poll_cmd` フィールドが「poll コマンド」ではなく「プロパティタイプ」として使用される唯一のモード。

#### PANEL/HPANEL と extend_target

- `extend_target` は PME1 では別フィールドとして存在
- PME2 では `pm.name` がターゲット名を含む（例: `VIEW3D_PT_object_properties$`）
- HPANEL の `hpg?` プレフィックスはメニューデータ用（アイテムでは異なる可能性）

---

### pm.ed のタイミング

```python
# pme_types.py:907-913
@property
def ed(self):
    prefs = get_prefs()
    if not prefs.editors:
        return None  # ← 初期化中は None
    return prefs.editors.get(self.mode)
```

| タイミング | pm.ed アクセス | 備考 |
|------------|---------------|------|
| アドオン初期化中 | ❌ 不可 | `prefs.editors` が空 |
| 初期化完了後 | ✅ 可能 | 全 Editor が登録済み |
| **JSON インポート時** | **⚠️ 要確認** | タイミングによる |

**重要**: `preferences.py:load_post_handler()` でメニューを読み込む際、Editor の登録順序に依存。ほとんどの場合は問題ないが、以下のパターンで問題になる可能性：

1. カスタムアドオンが PME より先に `load_post` を登録
2. PME の Editor 登録より前に `pm.ed` にアクセス

---

### 設計選択肢の評価

| 選択肢 | メリット | デメリット | 推奨度 |
|--------|---------|-----------|--------|
| **1. Editor にメソッド追加** | OOP原則に沿う、拡張性◎、責務が明確 | 10個のEditorに影響、pm.edタイミング問題 | ⭐⭐⭐⭐ |
| **2. 別ファイルに分離** | 関心の分離、いつでも呼べる | ファイル増加、知識が分散 | ⭐⭐⭐ |
| **3. データ駆動（テーブル）** | シンプル、一覧性◎ | 複雑な変換に不向き（PROPERTY） | ⭐⭐ |
| **4. 現状維持** | 変更なし | OCP違反、肥大化、テスト困難 | ⭐ |

---

### 推奨（参考）

#### 推奨案: ハイブリッドアプローチ

**Option 1 + 2 の組み合わせ**

```python
# editors/base.py
class EditorBase:
    def export_settings(self, pm) -> dict:
        """デフォルト実装: pm.data をパースして返す"""
        return schema.parse(pm.data).to_dict()

    def import_settings(self, pm, settings: dict) -> None:
        """デフォルト実装: settings から pm.data を構築"""
        pm.data = schema.encode_from_dict(self.default_pmi_data, settings)

# editors/property.py
class Editor(EditorBase):
    def export_settings(self, pm) -> dict:
        settings = super().export_settings(pm)
        settings['prop_type'] = pm.poll_cmd  # poll_cmd を prop_type として出力
        return settings

    def import_settings(self, pm, settings: dict) -> None:
        super().import_settings(pm, settings)
        if 'prop_type' in settings:
            pm.poll_cmd = settings['prop_type']  # prop_type を poll_cmd に復元
```

**バックアップ用ファサード** (pm.ed が None の場合):

```python
# infra/mode_io.py
def export_settings(pm) -> dict:
    """pm.ed が利用可能ならそれを使い、そうでなければフォールバック"""
    if pm.ed:
        return pm.ed.export_settings(pm)
    return _fallback_export(pm)

def _fallback_export(pm) -> dict:
    """Editor 登録前のフォールバック（シンプルなパース）"""
    return schema.parse(pm.data).to_dict()
```

#### 理由

1. **拡張性**: 新モード追加時、Editor を追加するだけで対応可能
2. **テスト容易性**: 各 Editor の I/O ロジックを単体テスト可能
3. **後方互換**: デフォルト実装があるため既存 Editor に影響少
4. **安全性**: フォールバック機能でタイミング問題を回避

---

### 影響範囲の評価

#### Editor にメソッド追加した場合の変更ファイル

| ファイル | 変更内容 | 工数 |
|----------|---------|------|
| `editors/base.py` | `export_settings()`, `import_settings()` デフォルト実装追加 | 小 |
| `editors/property.py` | オーバーライド（poll_cmd → prop_type） | 中 |
| `editors/panel_group.py` | オーバーライド（extend_target 相当） | 小 |
| `editors/hpanel_group.py` | オーバーライド（extend_target 相当） | 小 |
| その他 7 Editor | 変更不要（デフォルト実装で対応） | なし |
| `infra/serializer.py` | pm.ed.export_settings() 呼び出し | 小 |
| `infra/converter.py` | pm.ed.import_settings() 呼び出し | 小 |

**合計変更ファイル**: 6-7 ファイル
**影響する Editor**: 3/10（特殊処理が必要なもの）

---

## やらないこと（調査範囲外）

- 設計の最終決定
- コードの実装
- 他の調査タスク（9-D-1, 9-D-2, 9-D-3）との統合

---

## 次のステップ（参考）

1. **9-D-1 との統合**: PROPERTY mode クラッシュ調査の結果を踏まえて `export_settings()` の実装を検討
2. **9-D-2 との統合**: `hpg` プレフィックスの用途確認後、HPANEL の `export_settings()` を設計
3. **プロトタイプ実装**: PROPERTY Editor のみで PoC を実施
4. **テスト**: 往復変換（export → import）テストの追加

---

## 参照ファイル

| ファイル | 行番号 | 内容 |
|----------|--------|------|
| `editors/base.py` | 181-749 | EditorBase クラス |
| `editors/property.py` | 141-152, 369-372, 680-1205 | PROPERTY Editor |
| `editors/panel_group.py` | 683-827 | PANEL Editor |
| `editors/hpanel_group.py` | 63-130 | HPANEL Editor |
| `pme_types.py` | 907-913 | pm.ed プロパティ |
| `core/schema.py` | - | ParsedData, schema |
