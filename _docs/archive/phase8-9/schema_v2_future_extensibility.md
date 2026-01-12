# PME2 Schema v2: 将来拡張性の検討

> **目的**: 現在のスキーマが将来の機能拡張に対応できるか検証
> **視点**: ユーザー体験、Blender 進化、AI 活用、VR/AR

---

## 1. 現在のスキーマの限界

### 1.1 Context Sensitive Menu が示す問題

`autorun_context_sensitive_menu_v2.py` は人気の拡張スクリプトだが、**初心者には使いづらい**。

```python
# 現状: Python スクリプトを書く必要がある
CSM.from_context(context, prefix="My ", suffix=" Menu").open_menu()
```

**問題点**:
- Python 知識が必要
- エラーハンドリングが難しい
- 設定の可視化ができない
- 共有/インポートが難しい

### 1.2 現在のスキーマで表現できないこと

| 機能 | 現在 | 理由 |
|------|------|------|
| **コンテキスト依存メニュー選択** | ❌ | 条件分岐がない |
| **動的なアイテム表示/非表示** | 一部 | `poll` のみ、アイテムレベルなし |
| **ツールチップ/説明文** | ❌ | フィールドがない |
| **ボタンカラー** | ❌ | スタイル情報がない |
| **アニメーション/トランジション** | ❌ | 描画情報がない |
| **音声フィードバック** | ❌ | メディア情報がない |
| **VR/空間 UI** | ❌ | 位置/サイズ情報がない |

---

## 2. 拡張性のためのスキーマ改善案

### 2.1 メタデータセクションの追加

```json
{
  "name": "My Pie Menu",
  "mode": "PMENU",

  "meta": {
    "description": "モデリング作業用のメインメニュー",
    "author": "username",
    "version": "1.0.0",
    "tags": ["modeling", "mesh"],
    "icon": "MESH_CUBE",
    "color": "#4A90D9"
  }
}
```

**利点**:
- メニューの説明が可能（UI で表示、AI が理解）
- カラーテーマのカスタマイズ
- 将来的に検索/フィルタリングに活用

### 2.2 アイテムレベルのメタデータ

```json
{
  "name": "Add Cube",
  "action": { ... },

  "meta": {
    "description": "シーンに立方体を追加します",
    "shortcut_hint": "Shift+A → Mesh → Cube",
    "difficulty": "beginner",
    "category": "primitives"
  },

  "style": {
    "color": "#4CAF50",
    "size": "large",
    "emphasis": true
  }
}
```

**利点**:
- ツールチップに description を表示（動的オペレーター不要でも将来対応可能）
- 初心者向け UI フィルタリング
- AI がアクションを理解して提案

### 2.3 条件付きロジック

```json
{
  "name": "Context Menu",
  "mode": "PMENU",

  "conditions": {
    "when": [
      { "context.mode": "EDIT_MESH", "use_menu": "Edit Mesh Menu" },
      { "context.mode": "SCULPT", "use_menu": "Sculpt Menu" },
      { "object.type": "ARMATURE", "use_menu": "Armature Menu" },
      { "default": true, "use_menu": "Default Menu" }
    ]
  }
}
```

**利点**:
- Context Sensitive Menu がスキーマで表現可能
- Python 不要で初心者も使える
- インポート/エクスポートで共有可能

### 2.4 アイテムレベルの条件

```json
{
  "name": "Subdivide",
  "action": { "type": "command", "value": "bpy.ops.mesh.subdivide()" },

  "visibility": {
    "when": "context.mode == 'EDIT_MESH'",
    "fallback": "hidden"
  },

  "enabled": {
    "when": "len(context.selected_objects) > 0"
  }
}
```

**利点**:
- 動的なアイテム表示/非表示
- メニューレベルの `poll` より細かい制御
- UI で条件を可視化できる

---

## 3. 将来技術への対応

### 3.1 VR/AR/空間コンピューティング

```json
{
  "spatial": {
    "position": { "anchor": "hand_right", "offset": [0, 0.1, 0] },
    "orientation": "face_user",
    "scale": 1.5,
    "interaction": {
      "selection": "gaze_dwell",
      "activation": "pinch"
    }
  }
}
```

**将来の Blender VR モードに対応**:
- 手元に追従するメニュー
- 視線選択
- ジェスチャー認識

### 3.2 AI 統合

```json
{
  "ai": {
    "intent": "add_primitive_mesh",
    "parameters": {
      "mesh_type": { "type": "enum", "options": ["cube", "sphere", "cylinder"] }
    },
    "natural_language": [
      "立方体を追加",
      "キューブを作成",
      "add a cube"
    ]
  }
}
```

**利点**:
- AI がメニューの意図を理解
- 音声コマンド対応
- 自然言語検索
- AI によるメニュー提案

### 3.3 マルチモーダル入力

```json
{
  "input": {
    "keyboard": { "key": "A", "modifiers": ["SHIFT"] },
    "voice": ["add cube", "キューブ追加"],
    "gesture": { "type": "swipe_right", "area": "viewport" },
    "midi": { "channel": 1, "note": 60 }
  }
}
```

**利点**:
- 多様な入力デバイス対応
- アクセシビリティ向上
- クリエイティブワークフロー

---

## 4. GPU 描画対応

### 4.1 カスタム描画情報

```json
{
  "rendering": {
    "mode": "gpu_custom",
    "shader": "radial_gradient",
    "theme": {
      "background": { "color": "#1a1a2e", "opacity": 0.95 },
      "border": { "color": "#4a90d9", "width": 2 },
      "text": { "color": "#ffffff", "shadow": true },
      "highlight": { "color": "#ff6b6b", "glow": true }
    },
    "animation": {
      "enter": { "type": "scale_bounce", "duration": 0.15 },
      "hover": { "type": "glow_pulse", "duration": 0.3 }
    }
  }
}
```

**将来の GPU 描画に対応**:
- カスタムシェーダー
- アニメーション効果
- テーマのカスタマイズ

### 4.2 レイアウト情報

```json
{
  "layout": {
    "type": "radial",
    "radius": 150,
    "item_size": { "width": 80, "height": 80 },
    "spacing": 10,
    "overflow": "scroll"
  }
}
```

---

## 5. 実装戦略: 拡張可能なスキーマ設計

### 5.1 「未知のフィールドを保持」パターン

```python
@dataclass
class MenuSchema:
    name: str
    mode: str
    # ... 既知のフィールド

    # 拡張フィールド（将来互換）
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        result = { ... }
        # extensions の内容をマージ
        result.update(self.extensions)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "MenuSchema":
        known_fields = {"name", "mode", ...}
        extensions = {k: v for k, v in data.items() if k not in known_fields}
        return cls(
            name=data["name"],
            mode=data["mode"],
            # ...
            extensions=extensions,
        )
```

**利点**:
- 古いバージョンで作成した JSON が新機能を含んでいても読める
- 新しいバージョンで追加したフィールドが古いバージョンで消えない

### 5.2 バージョニングと機能フラグ

```json
{
  "$schema": "PME2",
  "version": "2.0.0",
  "features": ["conditions", "meta", "spatial"],

  "menus": [ ... ]
}
```

**利点**:
- どの機能を使っているか明示
- 非対応機能の警告を出せる

### 5.3 プラグイン拡張ポイント

```json
{
  "plugins": {
    "context_sensitive": {
      "enabled": true,
      "config": {
        "prefix": "My ",
        "suffix": " Menu"
      }
    },
    "ai_assistant": {
      "enabled": true,
      "model": "gpt-4"
    }
  }
}
```

---

## 6. 現在のスキーマへの最小限の変更提案

### 6.1 2.0.0 で入れるべき変更

| 変更 | 理由 | リスク |
|------|------|--------|
| `extensions: {}` フィールド追加 | 将来拡張のプレースホルダー | 低 |
| MenuItem に `description` 追加 | ツールチップ用（将来） | 低 |
| Menu に `meta` セクション追加 | 説明/カテゴリ/カラー | 低 |

### 6.2 2.1.0 以降で検討

| 変更 | 理由 |
|------|------|
| `conditions` セクション | Context Sensitive Menu のスキーマ化 |
| `visibility` / `enabled` | アイテムレベルの条件 |
| `style` セクション | カラー/サイズのカスタマイズ |
| `spatial` セクション | VR 対応 |
| `ai` セクション | AI 統合 |

---

## 7. 具体的なスキーマ改訂案

### 現在の MenuItem

```json
{
  "name": "Add Cube",
  "action": { "type": "command", "value": "..." },
  "icon": "MESH_CUBE",
  "enabled": true
}
```

### 提案: 拡張された MenuItem

```json
{
  "name": "Add Cube",
  "action": { "type": "command", "value": "...", "context": null },
  "icon": "MESH_CUBE",
  "enabled": true,

  // 2.0.0 で追加（オプショナル）
  "description": "シーンに立方体プリミティブを追加",

  // 将来拡張用（2.0.0 では空 or 省略可）
  "extensions": {
    // 2.1.0+: 条件付き表示
    "visibility": { "when": "context.mode == 'OBJECT'" },
    // 2.2.0+: スタイル
    "style": { "color": "#4CAF50" },
    // 将来: AI ヒント
    "ai": { "intent": "add_primitive", "mesh_type": "cube" }
  }
}
```

---

## 8. 決定が必要な項目

### 2.0.0 で決める

| # | 項目 | 選択肢 | 推奨 |
|---|------|--------|------|
| E1 | `extensions` フィールド追加 | Yes / No | **Yes** |
| E2 | MenuItem に `description` 追加 | Yes / No | **Yes** |
| E3 | Menu に `meta` セクション追加 | Yes / No | Yes（オプショナル） |

### 2.1.0 で検討

| # | 項目 |
|---|------|
| E4 | `conditions` セクションの仕様 |
| E5 | `visibility` / `enabled` の式評価 |
| E6 | `style` セクションの仕様 |

---

## 9. Context Sensitive Menu のスキーマ化（将来像）

### 現在（Python 必須）

```python
CSM.from_context(context, prefix="My ", suffix=" Menu").open_menu()
```

### 将来（スキーマで表現）

```json
{
  "name": "Smart Context Menu",
  "mode": "PMENU",
  "type": "context_sensitive",

  "routing": {
    "prefix": "My ",
    "suffix": " Menu",
    "rules": [
      { "when": "context.mode == 'EDIT_MESH' and mesh_select_mode[0]", "menu": "Vertex" },
      { "when": "context.mode == 'EDIT_MESH' and mesh_select_mode[1]", "menu": "Edge" },
      { "when": "context.mode == 'EDIT_MESH' and mesh_select_mode[2]", "menu": "Face" },
      { "when": "context.mode == 'SCULPT'", "menu": "Sculpt" },
      { "when": "object.type == 'ARMATURE'", "menu": "Armature" },
      { "default": true, "menu": "Any Object" }
    ]
  }
}
```

**利点**:
- Python 不要
- UI でルールを編集可能
- インポート/エクスポートで共有
- AI がルールを理解して提案

---

## 10. まとめ

### 現在のスキーマの評価

| 観点 | 評価 | 備考 |
|------|------|------|
| **基本機能** | ✅ 十分 | メニュー/アイテム/アクション |
| **後方互換** | ✅ 十分 | PME1 からの変換対応 |
| **将来拡張** | ⚠️ 弱い | 拡張ポイントがない |
| **動的機能** | ❌ 不足 | 条件分岐がない |
| **メタデータ** | ❌ 不足 | description がない |
| **スタイル** | ❌ 不足 | カラー/サイズがない |
| **VR/AI** | ❌ 未対応 | 将来の準備がない |

### 推奨アクション

1. **2.0.0**: `extensions` と `description` を追加（最小限の変更）
2. **2.1.0**: `conditions` と Context Sensitive のスキーマ化
3. **2.2.0+**: `style`, `spatial`, `ai` セクション

**「今は使わないが、将来壊さずに追加できる」設計にすることが重要。**

---

*このドキュメントは将来の可能性を探るものです。すべてを実装する必要はありません。*
