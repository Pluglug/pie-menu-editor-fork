---
title: RC Roadmap - Layer Violation Reduction Plan
phase: 5-A+
status: draft
created: 2026-01-04
last_updated: 2026-01-04
---

# RC Roadmap: レイヤ違反削減計画

Phase 5-A 完了後、RC までにレイヤ違反を整理するための計画。

---

## 現状サマリー

| 項目 | 値 |
|------|-----|
| 現在の違反 | 17 件 |
| RC 目標 | < 30 件（達成済み）|
| 理想目標 | 10 件以下 |
| Phase 5-A 完了 | ✅ (operators 分離) |

---

## 違反の分類（17件）

### カテゴリ A: core の上位依存（6件）

| 違反 | ファイル | 原因 | 対応方針 |
|------|----------|------|---------|
| `core ← infra` | `props.py` | debug import | **許容**: NOTE 済み、デバッグ用 |
| `core ← infra` | `constants.py` | previews_helper import | **Phase 6**: 分離検討 |
| `core ← infra` | `pme_types.py` | ui import | **Phase 5-B**: LAYER 変更 |
| `core ← ui` | `pme_types.py` | utils import | **Phase 5-B**: LAYER 変更 |
| `core ← operators` | `pme_types.py` | operators import | **Phase 5-B**: LAYER 変更 |
| `core ← infra` | `pme_types.py` | panels import | **Phase 5-B**: LAYER 変更 |

### カテゴリ B: infra の上位依存（8件）

| 違反 | ファイル | 原因 | 対応方針 |
|------|----------|------|---------|
| `infra ← ui` | `base.py` | screen import | **Phase 7**: 分離検討 |
| `infra ← ui` | `bl_utils.py` | screen import | **Phase 7**: 分離検討 |
| `infra ← ui` | `base.py` | utils import | **Phase 7**: 分離検討 |
| `infra ← operators` | `popup.py` | operators import | **許容**: runtime 依存 |
| `infra ← operators` | `base.py` | operators import | **許容**: runtime 依存 |
| `infra ← operators` | `base.py` | ed import | **許容**: runtime 依存 |
| `infra ← operators` | `property.py` | extra_operators import | **Phase 7**: 分離検討 |

### カテゴリ C: ui/editors の上位依存（3件）

| 違反 | ファイル | 原因 | 対応方針 |
|------|----------|------|---------|
| `ui ← operators` | `utils.py` | operators import | **Phase 7**: 分離検討 |
| `editors ← operators` | `panel_group.py` | operators import | **Phase 7**: TYPE_CHECKING へ |
| `editors ← operators` | `hpanel_group.py` | operators import | **Phase 7**: TYPE_CHECKING へ |
| `editors ← operators` | `panel_group.py` | extra_operators import | **Phase 7**: TYPE_CHECKING へ |

---

## フェーズ計画

### Phase 5-B: pme_types の再配置（優先度: 高）

**目標**: pme_types の LAYER を実態に合わせて修正

**選択肢**:

| オプション | 説明 | 削減数 | リスク |
|----------|------|--------|--------|
| A: LAYER → "infra" | 最も簡単、実態に合致 | 4件 | 低 |
| B: LAYER → "ui" | より正確だが依存が複雑 | 4件 | 低 |
| C: 依存を削除 | 根本解決、大規模変更 | 4件 | 高 |

**推奨**: オプション A（LAYER → "infra"）

**理由**:
- `pme_types.py` は `PropertyGroup` を定義しており、`bpy` に強く依存
- 純粋な `core` レイヤにはなれない
- 実態を反映した LAYER 宣言にすることで、依存グラフが正確になる

**予想結果**: 違反 17 → 13 件（4件削減）

---

### Phase 6: core の infra 依存解消（優先度: 中）⏸️ 保留

**目標**: constants.py の previews_helper 依存を解消

**現状**:
```python
# core/constants.py
from ..previews_helper import ph
```

**保留理由**: Issue #65 に関連
- `OPEN_MODE_ITEMS` のアイコンがリロード時に更新されない問題
- EnumProperty の items を動的コールバックに変更する必要あり
- 単純な LAYER 変更では根本解決にならない

**予想結果**: 違反 13 → 12 件（1件削減）

**関連**: Issue #65 (icon previews の Reload 問題)

---

### Phase 7: infra/editors → operators 依存の解消（優先度: 低）⏸️ 保留

**目標**: TYPE_CHECKING への移動と実行時依存の分離

**対象**:
- `panel_group.py` → operators
- `hpanel_group.py` → operators
- `property.py` → extra_operators

**保留理由**: 実行時に必要な依存
- 使用箇所: `lh.operator(SomeOperator.bl_idname, ...)` など
- `.bl_idname` はクラス属性アクセスであり、実行時にクラスが必要
- TYPE_CHECKING に移動すると実行時エラーになる

**代替案（将来検討）**:
1. オペレーターの bl_idname を定数として定義
2. editors は定数を参照し、operators を直接 import しない
3. しかし大規模変更のため RC 後に検討

---

### RC 準備: 許容リストの文書化

**目標**: 残存する違反を「意図的に許容」として文書化

**許容する違反の候補**:

| 違反 | 理由 |
|------|------|
| `props → debug` | デバッグ用、NOTE 済み |
| `popup/base → operators` | runtime 依存、分離困難 |
| `infra → ui` (screen/utils) | 画面操作に必要 |

**RC タスク**:
- [ ] 許容リストを `_docs/` に文書化
- [ ] 旧ローダー削除
- [ ] マイグレーションガイド作成

---

## 全体スケジュール

```
Phase 5-A 完了時 (17件)
    │
    ├── Phase 5-B: pme_types LAYER 変更 ✅ 完了
    │   └── 結果: 13件 (-4)
    │
    ├── Phase 6: constants → previews_helper 分離 ⏸️ 保留
    │   └── Issue #65 関連のため保留
    │
    ├── Phase 7: TYPE_CHECKING 移動 ⏸️ 保留
    │   └── 実行時依存のため保留
    │
    └── RC 準備
        ├── 許容リスト文書化
        ├── 旧ローダー削除
        └── マイグレーションガイド

現在の違反: 13件 (目標 < 30件 達成済み)
```

---

## 理想アーキテクチャとの関係

Phase 5-B〜7 は「対症療法」であり、理想アーキテクチャ（`_docs/design/core-layer/ideal-architecture.md`）への移行ではない。

理想アーキテクチャへの移行は v2.1.0 以降で検討:
- MenuSchemaBase (dataclass)
- MenuBehaviorBase / MenuViewBase 分離
- MenuRegistry パターン

現フェーズでは「安定リリースのための整理」を優先する。

---

## 参照

- `rules/milestones.md` — フェーズ計画
- `_docs/guides/dependency_cleanup_plan.md` — 違反削減計画
- `_docs/design/core-layer/ideal-architecture.md` — 理想アーキテクチャ
