# PME2 Milestones (Summary)

> 詳細な履歴: `@_docs/archive/milestones_full.md`
> 最終更新: 2026-01-13

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
| **Phase 9** | 🔄 | **JSON Schema v2 I/O** |

---

## Phase 9: JSON Schema v2（2.0.0 の中核）

> GitHub Milestone: [2.0.0 - JSON Schema v2](https://github.com/Pluglug/pie-menu-editor-fork/milestone/1)
> Tracking Issue: #78

### 完了した Issue ✅

| Issue | タイトル | 完了 |
|-------|---------|------|
| #92 | Prefix standardization (MODAL/PROPERTY) | PR マージ |
| #93 | uid field for PMItem | コミット完了 |
| #89 | pm.data strategy | 戦略確定、実装完了 |
| #88 | Post-mortem (9-D ブロック解消) | 全サブタスク解決 |
| #79 | name/uid separation | uid コア実装完了 |
| #69 | Extend Panel name issue | PR #98 |
| #94 | PROPERTY mode fix (prop_type) | PR マージ |
| #97 | ExtendManager | PR #98 マージ |

### 残り OPEN

| Issue | タイトル | 状態 |
|-------|---------|------|
| **#87** | I/O integration | **次ステップ** - メイン作業 |
| #83 | PME1→PME2 converter | 一部 `infra/compat.py` に実装済み |
| #78 | Tracking | 全完了時にクローズ |

### 2.0.0 スコープ外に移動

| Issue | タイトル | 理由 |
|-------|---------|------|
| #84 | dataclass schemas | #89 でやらないことに |
| #82 | Action.context | 新機能、設計未定 |
| #81 | description/expr | 新機能 (部分的に 2.0.0 に入れる可能性) |
| #80 | Style system | 新機能 (UI/UX) |
| #77 | Git-backed JSON | RFC |

### 2.0.0 で追加検討

- **description の GPU 描画ヒント**: Pie Menu のみでヒントを付けられるようにする

---

## 9-D サブタスク解決済み

| ID | タスク | 解決 |
|----|--------|------|
| 9-D-1 | PROPERTY mode クラッシュ | ✅ PR #94 (`prop_type` 分離) |
| 9-D-2 | type=hpg の謎 | ✅ 勘違い (HPANEL menu=`hp?`, item=`hpg?`) |
| 9-D-3 | extend_target 再設計 | ✅ PR #98 (ExtendManager, pm.data へ移動) |
| 9-D-4 | Editor I/O methods | ✅ 不要 (pm.data + schema で十分) |

---

## 基本方針

- **JSON v2 I/O 実装**を最優先
- dataclass スキーマは不要（pm.data + ParsedData で十分）
- `DBG_DEPS=True` でレイヤ違反を可視化

## 現在の構造

```
core/namespace.py → Stability, NAMESPACE_*, PUBLIC_NAMES, is_public()
core/schema.py    → SchemaProp, SchemaRegistry, ParsedData, schema
core/uid.py       → generate_uid(), validate_uid(), get_mode_from_uid()
pme.py            → PMEContext, UserData, context
                  → execute(), evaluate() (Experimental)
                  → find_pm(), list_pms(), invoke_pm() (Experimental)
infra/extend.py   → ExtendManager, ExtendEntry (PR #98)
```

---

## 解決済み Issue

| Issue | 内容 | 解決方法 |
|-------|------|---------|
| #64 | ParsedData の cross-type property binding | `is_empty` で `__dict__` 直接参照 |
| #69 | Extend Panel の name 設計問題 | PR #98 (ExtendManager) |
| #88 | Phase 9-D ブロック | 全サブタスク解決 |

## 関連 Issue

| Issue | 内容 | 状態 |
|-------|------|------|
| #70 | Phase 4-B 外部 API 実装 | ✅ 完了 |
| #65 | icon previews の Reload 問題 | 解消済み、モジュール移動待ち |
| #67 | use_reload パターン | 保留 |
| #74 | Phase 5-A オペレーター分離 | ✅ 完了 |

---

## 2.0.0 → 2.0.1 の境界

| 2.0.0 でやる | 2.0.1 でやる |
|-------------|-------------|
| JSON Schema v2 I/O | WM_OT ステートマシン再設計 |
| PME1 migration (fix_2_0_0, fix_json_2_0_0) | 内部 dataclass 化 |
| uid field | 動的オペレーター生成 |
| ExtendManager | Action.context |
| (検討) description GPU ヒント | Style system |

---

## 参照

| ドキュメント | 用途 |
|-------------|------|
| `@_docs/archive/milestones_full.md` | 完了フェーズの詳細 |
| `@_docs/guides/cleanup_workflow.md` | 違反整理手順 |
| `@_docs/design/json_schema_v2.md` | JSON 形式仕様 |
| `@_docs/design/design_decisions.md` | 設計判断の記録 |
| `@_docs/design/PME2_FEATURE_REQUESTS.md` | ユーザー要望 |
