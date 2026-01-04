# PME2 Schema v2 分析: 可能性と限界

> **目的**: 新スキーマで何ができるか、何ができないか、どこに設計判断が必要かを整理
> **読者**: 1時間くらい悩む材料として

---

## 1. Action.context が開く可能性

### 1.1 現状の問題

PME1 では、コマンド実行時のコンテキストは暗黙的に決まる：

```python
# PME1: コンテキストは WM_OT_pme_user_pie_menu_call の invoke 時点のもの
bpy.ops.mesh.primitive_cube_add()  # 現在のコンテキストで実行
```

これが Issue #69 の根本原因：

```
Panel Group で「VIEW_3D」パネルを拡張しようとしても、
エディタの name が Blender の bl_idname と一致しないと動かない
```

### 1.2 Action.context で解決できること

```json
{
  "type": "command",
  "value": "bpy.ops.mesh.primitive_cube_add()",
  "context": "{'area': view3d_area, 'region': region}"
}
```

**可能になること**:

1. **エリアをまたぐ操作**
   - 3Dビュー以外から 3Dビューのオペレーターを実行
   - UV エディタとの連携操作

2. **動的コンテキスト構築**
   - `context` を Python 式として評価
   - 実行時に適切なエリア/リージョンを取得

3. **Issue #69 の解決パス**
   - Panel Group の name と Blender の bl_idname を分離
   - `context` でターゲットエリアを明示指定

### 1.3 まだ解決できないこと / 要検討

| 課題 | 状態 | 検討事項 |
|------|------|---------|
| `context` の評価タイミング | 未定 | invoke 時？ execute 時？ |
| エラーハンドリング | 未定 | 無効なコンテキストの場合は？ |
| セキュリティ | 要検討 | 任意の Python 式を許可するリスク |
| UI での編集 | 未定 | ユーザーがどうやって context を指定する？ |

### 1.4 考えるべき質問

```
Q1: context フィールドは Python 式として評価するのか、
    それとも構造化された設定（area_type, region_type 等）にするのか？

    Python 式:
    + 柔軟性が高い
    - セキュリティリスク
    - ユーザーが書くのは難しい

    構造化設定:
    + 安全
    + UI で編集しやすい
    - 表現力に限界

Q2: Extend Panel/Header の問題は context だけで解決できるのか、
    それとも別のメカニズムが必要か？
```

---

## 2. PME1 からの移行: 何が保持され、何が失われるか

### 2.1 完全に保持されるもの

| 機能 | PME1 | PME2 | 備考 |
|------|------|------|------|
| メニュー名 | ✅ | ✅ | そのまま |
| ホットキー | ✅ | ✅ | より構造化 |
| コマンド | ✅ | ✅ | Action.command |
| カスタムスクリプト | ✅ | ✅ | Action.custom |
| アイコン | ✅ | ✅ | フラグ分離 |
| タグ | ✅ | ✅ | 配列化 |
| Poll 条件 | ✅ | ✅ | そのまま |

### 2.2 情報が失われる可能性があるもの

| 機能 | PME1 | PME2 | リスク |
|------|------|------|--------|
| `data` 文字列の未知プロパティ | ✅ | ❓ | パース時に無視される |
| カスタム flags ビット | ✅ | ❓ | ビット1以降は未定義 |
| 古い形式の特殊設定 | ✅ | ❓ | 1.18.x 以前の独自形式 |

### 2.3 変換時の検討事項

```
Q3: 変換できなかった情報をどう扱うか？

    A) 静かに無視（データロス）
    B) 警告を出力（ユーザーに通知）
    C) 未知フィールドとして保持（_unknown: {} みたいな）
    D) 変換失敗として拒否

Q4: 1.18.x 以前のサポートはどこまで必要か？
    - 1.19.x のみサポート → シンプル
    - 1.18.x までサポート → 変換ロジックが複雑化
    - 1.13.6 までサポート → さらに複雑
```

---

## 3. 内部スキーマ vs 外部スキーマ

### 3.1 二重スキーマ問題

現在の PME には「二重定義」問題がある：

```python
# (A) Blender PropertyGroup として（pme_types.py）
pm_radius: bpy.props.IntProperty(
    get=lambda s: s.get_data("pm_radius"),
    set=lambda s, v: s.set_data("pm_radius", v),
    default=-1,
)

# (B) PMEProps スキーマとして（editors/pie_menu.py）
schema.IntProperty("pm", "pm_radius", -1)
```

### 3.2 PME2 での選択肢

```
選択肢1: dataclass をメインに、PropertyGroup は薄いラッパー

    core/schemas/pie_menu.py:
        @dataclass
        class PieMenuSchema:
            radius: int = -1
            flick: bool = True

    pme_types.py:
        class PMItem(PropertyGroup):
            _schema_cache: PieMenuSchema | None = None

            @property
            def schema(self) -> PieMenuSchema:
                if self._schema_cache is None:
                    self._schema_cache = PieMenuSchema.from_data(self.data)
                return self._schema_cache

    利点: 型安全、テスト容易
    欠点: キャッシュ管理が複雑

選択肢2: PropertyGroup の getter/setter を維持

    現状維持に近い形で、JSON 出力時のみ dataclass に変換

    利点: 既存コードへの影響が小さい
    欠点: 二重定義問題が残る

選択肢3: 完全に dataclass に移行（PropertyGroup 廃止）

    理想的だが、Blender のシリアライズ機構を捨てることになる

    利点: シンプル
    欠点: Blender 標準の設定保存が使えない
```

### 3.3 考えるべき質問

```
Q5: 2.0.0 でどこまでやるか？

    最小限: JSON v2 エクスポート/インポートのみ
          → 内部は PME1 のまま、出力だけ新形式

    中程度: dataclass スキーマを追加、並行運用
          → 徐々に内部を置き換え

    最大限: 完全に dataclass 化
          → PropertyGroup は薄いアダプターに

Q6: PropertyGroup の data 文字列は維持するか、廃止するか？

    維持:
    + 後方互換
    + 既存の getter/setter がそのまま使える
    - 二重定義問題が残る

    廃止:
    + シンプル
    - 既存コードへの影響が大きい
    - Blender シリアライズとの整合性
```

---

## 4. Feature Requests との関連

### 4.1 新スキーマで実現しやすくなるもの

| 要望 | PME1 | PME2 | 根拠 |
|------|------|------|------|
| **メニュープロファイル切り替え** | 困難 | 可能 | ファイル単位でメニューセットを管理 |
| **コピー&ペースト** | 困難 | 容易 | JSON オブジェクトとしてコピペ |
| **Python エクスポート** | 困難 | 可能 | スキーマから Python コード生成 |
| **Blender キーマップ表示** | 困難 | 検討中 | Issue #4（後述） |
| **動的メニュー** | 困難 | 検討中 | Action.context + poll 条件 |

### 4.2 新スキーマだけでは解決しないもの

| 要望 | 理由 | 必要な追加作業 |
|------|------|--------------|
| **カスタムスタイリング** | スキーマではなく描画の問題 | UI レイヤーの変更 |
| **Modal Operator 強化** | ステートマシンの問題 | WM_OT 再設計（2.0.1） |
| **フォルダ/階層管理** | UI の問題 | Preferences UI 変更 |
| **Blender キーマップ表示** | オペレーター bl_label の問題 | 動的オペレーター生成 |

### 4.3 Blender キーマップ表示問題（Issue #4 相当）

現状:
```
Preferences → Keymap で「Call Menu (PME)」と表示される
ユーザーは「どのメニューを呼ぶのか」分からない
```

解決策の候補:

```
A) 動的オペレーター生成
   - メニューごとに異なる bl_idname を持つオペレーターを生成
   - bl_label = "My Pie Menu (PME)"
   - 問題: オペレーター数の爆発、登録/解除の複雑さ

B) キーマップカスタム表示
   - Blender のキーマップ UI をオーバーライド
   - 問題: Blender 内部 UI への介入が必要

C) 独自キーマップ管理 UI
   - PME Preferences 内で完結
   - 問題: Blender 標準と別管理になる

D) 2.0.1 で対応（WM_OT 再設計時）
   - 2.0.0 では現状維持
```

---

## 5. dataclass 設計の詳細検討

### 5.1 pme_mini の設計（参考）

```python
# pme_mini/core/schemas.py

@dataclass
class Action:
    type: ActionType = "empty"
    value: str = ""
    undo: bool | None = None
    context: str | None = None
    use_try: bool | None = None
    expand: bool | None = None
    slider: bool | None = None
    toggle: bool | None = None
    mode: str | None = None
    properties: dict[str, Any] | None = None
```

**長所**:
- シンプル、全タイプを1クラスで表現
- `to_dict()` でタイプに応じたフィールドのみ出力

**短所**:
- 型安全性が弱い（どのフィールドがどのタイプで使われるか不明確）
- IDE 補完が効きにくい

### 5.2 代替案: Union + タイプ別クラス

```python
@dataclass
class CommandAction:
    type: Literal["command"] = "command"
    value: str = ""
    undo: bool = True
    context: str | None = None

@dataclass
class CustomAction:
    type: Literal["custom"] = "custom"
    value: str = ""
    undo: bool = False
    use_try: bool = True

Action = Union[CommandAction, CustomAction, PropAction, ...]
```

**長所**:
- 型安全
- IDE 補完が効く
- 各タイプの設定が明確

**短所**:
- クラス数が多い
- 変換ロジックが複雑

### 5.3 考えるべき質問

```
Q7: どちらの設計を採用するか？

    シングルクラス:
    - 実装が早い
    - 柔軟
    - 2.0.0 向け

    Union 型:
    - 型安全
    - 長期的に保守しやすい
    - 2.1.0 向け？

Q8: Settings も同様の問題がある

    現在: settings: dict[str, Any]
    理想: settings: PieMenuSettings | PopupSettings | ...

    2.0.0 では dict で進めて、2.1.0 で型付けする？
```

---

## 6. 移行戦略の選択肢

### 6.1 Option A: エクスポート先行（最小リスク）

```
2.0.0:
  - JSON v2 エクスポーター実装
  - JSON v1 インポーター維持 + v2 対応追加
  - 内部は現状維持（PMEProps + ParsedData）

2.0.1:
  - dataclass スキーマを core/schemas/ に追加
  - 並行運用開始
  - 一部 editor を新スキーマ対応

2.1.0:
  - 内部を完全に dataclass 化
  - PropertyGroup は薄いアダプターに
```

### 6.2 Option B: コア先行（構造改善優先）

```
2.0.0:
  - core/schemas/ に dataclass 定義
  - infra/converter.py で PME1 ↔ PME2 変換
  - JSON v2 エクスポート/インポート
  - 内部は新旧併用

2.0.1:
  - 内部を段階的に dataclass 化
  - WM_OT 再設計開始
```

### 6.3 Option C: 完全移行（最大リスク）

```
2.0.0:
  - 内部を完全に dataclass 化
  - PropertyGroup は getter/setter のみ
  - JSON v2 のみサポート
```

### 6.4 考えるべき質問

```
Q9: 2.0.0 のスコープは？

    A) エクスポート先行 → 安全だが、内部は PME1 のまま
    B) コア先行 → 構造は改善されるが、リスクあり
    C) 完全移行 → 理想的だが、テスター無しでは危険

Q10: 「土台とスキーマを固める」の定義は？

    狭い解釈: JSON 形式を確定し、変換ロジックを実装
    広い解釈: 内部スキーマ（dataclass）も確定
```

---

## 7. 残存する設計課題

### 7.1 Issue #69: Panel Group の name 問題

```python
# 現状: pm.name が Blender の bl_idname と一致する必要がある
# 例: name="VIEW3D_PT_my_panel" でないと動かない

# 理想: name は任意で、settings.target_panel で指定
{
  "name": "My Custom Panel",
  "mode": "PANEL",
  "settings": {
    "target_panel": "VIEW3D_PT_tools_active",  # ← 新フィールド
    "space": "VIEW_3D",
    "region": "UI"
  }
}
```

**検討事項**:
- `target_panel` を追加すれば解決するか？
- それとも Action.context で解決すべきか？
- 両方必要？

### 7.2 PropertyGroup 登録順序

```python
# Blender の PropertyGroup は登録順序に依存する
# PME1 では __init__.py で明示的に管理

# PME2 で dataclass 化すると、
# PropertyGroup はアダプターになるが、登録順序は残る

# 対策案:
# - dataclass は PropertyGroup から独立
# - PropertyGroup は必要最小限のフィールドのみ
# - data 文字列を維持して後方互換
```

### 7.3 Reload Scripts 問題

```python
# Issue #65, #67: Reload Scripts で状態が壊れる
# dataclass 化しても解決しない（別問題）

# ただし、dataclass 化により:
# - キャッシュ管理がシンプルになる可能性
# - prop_map のグローバル状態が減る可能性
```

---

## 8. 決定が必要な項目リスト

### 8.1 今すぐ決める（2.0.0 ブロッカー）

| # | 項目 | 選択肢 | 推奨 |
|---|------|--------|------|
| D1 | JSON v2 形式の確定 | 現ドラフトで進める / 修正 | 現ドラフト |
| D2 | 後方互換の範囲 | 1.19.x のみ / 1.18.x まで | 1.19.x |
| D3 | 内部スキーマの範囲 | エクスポートのみ / 内部も | エクスポートのみ |

### 8.2 今週中に決める

| # | 項目 | 選択肢 |
|---|------|--------|
| D4 | Action.context の仕様 | Python 式 / 構造化 / 両方 |
| D5 | dataclass の設計方針 | シングルクラス / Union 型 |
| D6 | Settings の型付け | dict のまま / 型付き |

### 8.3 2.0.1 で決める

| # | 項目 |
|---|------|
| D7 | 内部 dataclass 化の範囲 |
| D8 | WM_OT 再設計の詳細 |
| D9 | 動的オペレーター生成の是非 |

---

## 9. 参照資料

| ドキュメント | 内容 |
|-------------|------|
| `json_schema_v2.md` | JSON 形式の仕様 |
| `pme_mini/core/schemas.py` | dataclass 実装例 |
| `pme_mini/infra/converter.py` | 変換ロジック例 |
| `PME2_FEATURE_REQUESTS.md` | ユーザー要望一覧 |
| `ideal-architecture.md` | 理想アーキテクチャ |
| `pmeprops-schema-system.md` | 現行スキーマシステム |

---

## 10. Next Steps

1. **D1-D3 を決定**して json_schema_v2.md を最終化
2. **converter.py を PME 本体に移植**（pme_mini から）
3. **core/schemas/ を作成**（エクスポート用）
4. **infra/serializer.py を実装**（v2 エクスポート/インポート）
5. **テスト**: 既存メニューを v2 エクスポート → 再インポート → 動作確認

---

*このドキュメントは「茂らせる」フェーズの材料です。刈り取りは後で行います。*
