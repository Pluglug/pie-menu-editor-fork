# PME2 Milestones (Summary)

> 詳細な履歴: `@_docs/archive/milestones_full.md`

## 現在のステータス

| フェーズ | 状態 | 主要成果 |
|----------|------|---------|
| Phase 1 (alpha.0) | ✅ | 新ローダー、レイヤ分離 |
| Phase 2-A/B/C (alpha.1-2) | ✅ | モジュール分割、違反 49→21件 |
| Phase 4-A (alpha.3) | ✅ | `core/props.py` 分離、#64 解消 |
| Phase 4-B | ✅ | 標準名前空間、外部 API ファサード |
| Phase 5-A | ✅ | オペレーター分離（#74）、base.py 71%削減 |
| Phase 8-A | ✅ | Thin wrapper 削除 (PR#75)、違反 12→7 件 |
| Phase 8-C | ✅ | Schema リネーム（props → schema） |
| **Phase 9** | 🔄 | **JSON Schema v2 + dataclass 移行** |

---

## Phase 9: JSON Schema v2（2.0.0 の中核）

> メンターアドバイス: 「いま動いているものを壊さずに、土台とスキーマを固める版」
> トラッキング Issue: #78

### 9-A: JSON v2 スキーマ確定 🔄 (レビュー中)

- [x] `json_schema_v2.md` 初版作成
- [x] `design_decisions.md` 作成（D1-D18 確定）
- [x] メンターレビュー反映
- [x] 保守的レビュー反映（Modal ActionType, Hotkey fields, icon flags 等）
- [ ] 最終レビュー・承認待ち

**確定した設計判断 (18件)**:
| カテゴリ | 決定事項 |
|---------|---------|
| 基本構造 | D1: $schema/version 分離, D2: uid 導入, D5: extensions 2階層 |
| MenuItem | D3: description/description_expr 分離, D4: Style オブジェクト化 |
| Hotkey | D6: keymaps 配列化, D15: any/key_mod/chord 追加 |
| Action | D8-D10: operator 削除/undo 削除/menu uid のみ, D14: Modal モード追加, D18: custom 修正 |
| Settings | D7: キー名ルール, D17: 接頭辞変換方針 |
| その他 | D11-D13: poll/DragDirection/accent_usage, D16: icon flags |

### 9-B: dataclass スキーマ実装 ⏳

- [ ] `core/schemas/` ディレクトリ作成
- [ ] `Action`, `MenuItemSchema`, `HotkeySchema`, `MenuSchema` dataclass
- [ ] `PME2File` ルートオブジェクト

### 9-C: コンバーター実装 ⏳

- [ ] `infra/converter.py` 作成
- [ ] PME1 → PME2 変換（インポート時）
- [ ] バージョン検出ロジック

### 9-D: シリアライザー実装 ⏳

- [ ] `infra/serializer.py` 作成
- [ ] v2 エクスポート（新形式）
- [ ] v1/v2 デュアルインポート

### 9-E: テストと検証 ⏳

- [ ] 既存メニューの往復変換テスト
- [ ] Blender 5.0+ での動作確認

### やらないこと（2.0.1 へ）

- WM_OT ステートマシン再設計
- 動的オペレーター生成
- 内部の完全 dataclass 化

### 参照ドキュメント

- `@_docs/design/json_schema_v2.md` — JSON 形式仕様
- `@_docs/design/design_decisions.md` — 設計判断の記録（D1-D18）
- `@_docs/design/schema_v2_analysis.md` — 可能性と限界の分析
- `@_docs/design/schema_v2_future_extensibility.md` — 将来拡張性の検討
- `@_docs/design/PME2_FEATURE_REQUESTS.md` — ユーザー要望
- `@_docs/guides/phase9_implementation.md` — 実装ガイド

---

## 基本方針

- **Core 層の設計・実装**を最優先
- `use_reload` パターンは保留（Issue #67）
- `DBG_DEPS=True` でレイヤ違反を可視化

## 現在の構造

```
core/namespace.py → Stability, NAMESPACE_*, PUBLIC_NAMES, is_public()
core/schema.py    → SchemaProp, SchemaRegistry, ParsedData, schema
                  → (後方互換: PMEProp, PMEProps, props)
core/props.py     → 後方互換エイリアス（deprecated, v3.0で削除予定）
pme.py            → PMEContext, UserData, context
                  → execute(), evaluate() (Experimental)
                  → find_pm(), list_pms(), invoke_pm() (Experimental)
```

## 解決済み Issue

| Issue | 内容 | 解決方法 |
|-------|------|---------|
| #64 | ParsedData の cross-type property binding | `is_empty` で `__dict__` 直接参照 |

## 関連 Issue

| Issue | 内容 | 状態 |
|-------|------|------|
| #70 | Phase 4-B 外部 API 実装 | ✅ 完了 |
| #69 | Extend Panel の name 設計問題 | PME2 スキーマで対応予定 |
| #65 | icon previews の Reload 問題 | 解消済み、モジュール移動待ち |
| #67 | use_reload パターン | 保留 |
| #73 | モジュール読み込み順序問題 | ✅ workaround 適用、設計問題は #74 へ |
| #74 | Phase 5-A オペレーター分離 | ✅ 完了 |

## Phase 4-B 完了サマリー

- [x] `core/namespace.py` に標準名前空間を定義
- [x] `pme.execute()` / `pme.evaluate()` ファサード実装
- [x] `pme.find_pm()` / `list_pms()` / `invoke_pm()` 実装
- [x] ドキュメント同期（PR #72）

## Phase 5-A: オペレーター分離

**目標**: `editors/base.py` から 33 個のオペレーターを `operators/` に移動

**背景** (Issue #73 から):
- `editors/base.py` に EditorBase と 33 個のオペレーターが同居
- `preferences.py` が 8 個のオペレーターをインポート → `editors` レイヤへの依存
- これが循環的な読み込み順序問題を引き起こした

**成果**:
- [x] 33 個のオペレーターを `operators/ed/` に移動（8 ファイル）
- [x] `editors/base.py` を 2662 → 768 行に削減（71%）
- [x] `preferences` → `editors` 依存を解消
- [x] `pm.ed` null safety guards 追加

**Phase 5-B（将来検討）**:
- EditorBase の責務整理（Behavior / View 分離）
- 理想アーキテクチャに向けた段階的移行

## 完了したフェーズ

| フェーズ | 内容 | 結果 |
|---------|------|------|
| Phase 5-B | pme_types LAYER 変更 | 17 → 13 件 (-4) ✅ |
| Phase 7 | bl_idname リテラル化 | 13 → 12 件 (-1) ✅ |
| Phase 8-C | Schema リネーム | props → schema ✅ |

## 保留中のフェーズ

| フェーズ | 内容 | 理由 |
|---------|------|------|
| Phase 6 | constants → previews_helper 分離 | Issue #65 関連 |

## 残存違反の本質分析

12 件の違反は 3 つの本質的問題に分類される:

1. **`_draw_item` 配置問題**: オペレーターに置かれた UI 描画ロジック (3件)
2. **`screen.py`/`utils.py` 責務混在**: infra と ui 関数の同居 (4件)
3. **ランタイム依存**: popup/base のオペレーター呼び出し (3件)

**詳細**: `@_docs/analysis/remaining_violations_analysis.md`

## Phase 8: 薄いラッパー削除

**目標**: プロジェクトルートを `addon.py`, `pme.py` のみにする

### 8-A: 低リスク移動 ✅ (PR#75)

| ファイル | 移動先 | 状態 |
|----------|--------|------|
| `macro_utils.py` | `infra/macro.py` | ✅ |
| `utils.py` | `infra/utils.py` | ✅ |
| `property_utils.py` | `infra/property.py` | ✅ |
| `modal_utils.py` | `infra/modal.py` | ✅ |
| `selection_state.py` | `infra/selection.py` | ✅ |
| `compatibility_fixes.py` | `infra/compat.py` | ✅ |
| `previews_helper.py` | `infra/previews.py` | ✅ |

**残存（高リスク）**:
| `keymap_helper.py` | `infra/keymap.py` | 未着手 |
| `operator_utils.py` | `operators/utils.py` | 未着手 |

### 8-B: 高リスク分離

| タスク | 注意点 | 状態 |
|--------|--------|------|
| `WM_OT_pme_user_pie_menu_call` 切り出し | `_draw_item` が 3 箇所から参照 | 未着手 |
| `prefs` UI 分離 | draw 系メソッドの依存が複雑 | 未着手 |

### 8-C: Schema リネーム ✅

| タスク | 内容 | 状態 |
|--------|------|------|
| `pme.props` → `pme.schema` | 混乱防止のためリネーム | ✅ 完了 |

**完了内容**:
- [x] `core/props.py` → `core/schema.py` リネーム
- [x] `PMEProps` → `SchemaRegistry`, `PMEProp` → `SchemaProp`
- [x] `props` → `schema` インスタンス
- [x] 全 editors/ モジュールの import 更新
- [x] pme.py, pme_types.py, operators/, ui/ の更新
- [x] 後方互換エイリアスの維持

**詳細**: `@_docs/design/schema-rename-plan.md`

## 次のステップ候補

- **Phase 8-A**: 薄いラッパー移動（Codex タスク候補）
- **RC 準備**: 許容リスト文書化、旧ローダー削除
- **Issue #65**: OPEN_MODE_ITEMS アイコン問題
- **理想アーキテクチャ**: v2.1.0 以降で Schema/Behavior/View 分離

詳細は `@_docs/guides/rc_roadmap.md` を参照。

## RC への条件

- レイヤ違反 < 30 件 ✅ (現在 12 件)
- Reload Scripts が安定動作
- 旧ローダー削除
- マイグレーションガイド作成
- **JSON Schema v2 エクスポート/インポート** ← Phase 9

---

## WM-1: _draw_item 分離（2.0.0 で許容される WM_OT 変更）

> メンターアドバイス: 「責務の切り出しだけやる。挙動は 100%据え置き」

### 目的

- レイヤ違反を消す（operators → ui の依存を解消）
- `_draw_item` を単体テストしやすくする
- 将来の WM_OT 再設計（2.0.1）への準備

### やること

1. `ui/item_drawing.py` 新規作成
2. `WM_OT_pme_user_pie_menu_call._draw_item` の中身を移動
3. WM_OT 側は薄いラッパーに変更
4. `editors/panel_group`, `ui/utils` の参照を直接呼び出しに変更

### やらないこと

- ステートマシン（invoke/modal/execute_menu）への変更
- 動的オペレーター生成
- `InvocationState` 導入

---

## 2.0.0 → 2.0.1 の境界

| 2.0.0 でやる | 2.0.1 でやる |
|-------------|-------------|
| JSON Schema v2 | WM_OT ステートマシン再設計 |
| dataclass スキーマ（エクスポート用） | 内部 dataclass 化 |
| コンバーター実装 | 動的オペレーター生成 |
| _draw_item 分離（WM-1） | InvocationState 導入 |
| 許容リスト文書化 | テスター募集 |

---

## 参照

| ドキュメント | 用途 |
|-------------|------|
| `@_docs/archive/milestones_full.md` | 完了フェーズの詳細 |
| `@_docs/guides/cleanup_workflow.md` | 違反整理手順 |
| `@_docs/guides/rc_roadmap.md` | RC ロードマップ |
| `@_docs/design/api/pme_api_plan.md` | API 設計 |
| `@_docs/design/json_schema_v2.md` | JSON 形式仕様 |
| `@_docs/design/schema_v2_analysis.md` | スキーマ分析 |
| `@_docs/design/PME2_FEATURE_REQUESTS.md` | ユーザー要望 |
