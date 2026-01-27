# GPU Layout - Reactive Context Architecture

> Version: 1.1.0
> Status: **Implemented**
> Created: 2026-01-17
> Updated: 2026-01-17
> Related: Issue #104 (GPU Panel)

## 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.1.0 | フレームキャッシュを廃止、PropertyBinding に変更検知を追加 |
| 1.0.0 | 初版（フレームキャッシュあり、問題あり） |

---

## 1. 問題の定義

### 1.1 現在の状況

```python
# layout.py - 現在の実装
def prop(self, data: Any, property: str, ...):
    # data は作成時の参照（スナップショット）
    current_value = get_property_value(data, property)

    def on_toggle(new_value: bool):
        set_property_value(data, property, new_value)  # ← stale reference

    self._prop_bindings.append((item, data, property, meta))

def sync_props(self) -> None:
    for item, data, prop_name, meta in self._prop_bindings:
        current_value = get_property_value(data, prop_name)  # ← can crash
```

### 1.2 問題点

| 問題 | 影響 | 深刻度 |
|------|------|--------|
| **Stale Reference** | ユーザーが別オブジェクト選択後も古いオブジェクトを編集 | 高 |
| **Dangling Pointer** | 削除されたオブジェクトへのアクセスでクラッシュ | 高 |
| **コンテキスト不整合** | 表示と実際のコンテキストが乖離 | 中 |
| **メモリリーク** | 古いオブジェクトへの参照がGCを妨害 | 低 |

### 1.3 要件

- **常時表示パネル**として、Blender UI の拡張として機能する
- ユーザーの選択変更に**リアルタイム**で追従する
- オブジェクト削除時にクラッシュしない
- パフォーマンスを維持する（60fps での動作）

---

## 2. 設計の選択肢

### 2.1 Pattern A: Lazy Evaluation (遅延評価)

```python
# data の代わりに getter を保存
data_getter: Callable[[], Any] = lambda: context.object

def sync_props(self):
    data = data_getter()  # 毎回最新を取得
    if data is None:
        return  # 選択なし
    value = get_property_value(data, prop_name)
```

**メリット**: シンプル、既存コードへの影響が小さい
**デメリット**: コールバック内の `data` 参照も更新が必要

### 2.2 Pattern B: Context Path (文字列パス)

```python
# data_path: "context.object" or "context.scene.render"
data_path: str = "context.object"

def resolve_path(context, path: str) -> Any:
    parts = path.split('.')
    obj = context
    for part in parts[1:]:  # skip "context"
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj
```

**メリット**: 柔軟、シリアライズ可能
**デメリット**: `eval()` 的なセキュリティ懸念、エラー処理が複雑

### 2.3 Pattern C: Every-Frame Rebuild (毎フレーム再構築)

```python
# modal() 内で毎フレーム UI を再構築
def modal(self, context, event):
    self._layout = self._build_layout(context)  # 毎フレーム新規作成
    self._layout.draw()
```

**メリット**: 常に最新、シンプルなメンタルモデル
**デメリット**: パフォーマンス懸念（ただし GPU 描画は軽量）

### 2.4 Pattern D: Observable Context (イベント駆動)

```python
# Blender handler で変更を検知
@bpy.app.handlers.depsgraph_update_post
def on_depsgraph_update(scene, depsgraph):
    for update in depsgraph.updates:
        if update.is_updated_geometry or update.is_updated_transform:
            layout_manager.invalidate()
```

**メリット**: 変更時のみ更新、効率的
**デメリット**: handler 管理が複雑、Blender バージョン依存

---

## 3. 推奨アーキテクチャ: Hybrid Reactive

**Pattern A (Lazy Evaluation) + Pattern C (Selective Rebuild)** のハイブリッド

### 3.1 コア概念

```
┌─────────────────────────────────────────────────────────────┐
│                    GPULayout (Root)                          │
├─────────────────────────────────────────────────────────────┤
│  ContextProvider                                             │
│  ├── data_getters: Dict[str, Callable[[], Any]]             │
│  │   ├── "object" → lambda: context.object                  │
│  │   └── "scene.render" → lambda: context.scene.render      │
│  └── invalidation_keys: Set[str]                            │
├─────────────────────────────────────────────────────────────┤
│  PropertyBinding                                             │
│  ├── data_key: str  ("object")                              │
│  ├── prop_name: str ("hide_viewport")                       │
│  ├── widget: LayoutItem                                      │
│  └── on_change: Callable                                     │
├─────────────────────────────────────────────────────────────┤
│  Lifecycle                                                   │
│  ├── build()   → UI 構築、バインディング登録                 │
│  ├── sync()    → バインディングから値を同期                  │
│  ├── draw()    → GPU 描画                                    │
│  └── rebuild() → invalidation 時に再構築                     │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 ContextProvider クラス（キャッシュレス設計）

> **重要な変更 (v1.1.0)**: フレームキャッシュを廃止しました。
> Blender の選択変更やモード変更は同一フレーム内で発生するため、
> キャッシュは stale data の原因になっていました。

```python
from typing import Callable, Dict, Any, Optional
import bpy

class ContextProvider:
    """
    Blender コンテキストへの遅延アクセスを提供

    特徴:
        - 遅延評価: getter は実際にアクセスされるまで実行されない
        - **キャッシュレス**: 毎回 getter を実行し、常に最新のデータを取得
        - 安全なアクセス: ReferenceError, AttributeError を適切に処理

    使用例:
        provider = ContextProvider()
        provider.register("object", lambda ctx: ctx.object)
        provider.register("render", lambda ctx: ctx.scene.render)

        # 最新のデータを取得（毎回 getter が実行される）
        obj = provider.get("object", bpy.context)
    """

    def __init__(self):
        self._getters: Dict[str, Callable[[bpy.types.Context], Any]] = {}
        # プリセット登録（"object", "scene", "render" など）
        self._register_presets()

    def get(self, key: str, context: bpy.types.Context) -> Optional[Any]:
        """
        最新のデータを取得

        **キャッシュレス**: 毎回 getter を実行し、常に最新のデータを返す。
        """
        getter = self._getters.get(key)
        if getter is None:
            return None

        try:
            return getter(context)
        except (ReferenceError, AttributeError, TypeError):
            return None
```

### 3.3 PropertyBinding クラス（変更検知あり）

> **重要な変更 (v1.1.0)**: 前回値と前回データ ID を保存し、変更検知を実装。
> これにより、コンテキスト変更（オブジェクト選択変更など）を検知できる。

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

@dataclass
class PropertyBinding:
    """
    プロパティとウィジェットのバインディング

    遅延評価により、常に最新のデータにアクセス。
    前回値と比較して変更を検知。
    """
    data_key: str                              # ContextProvider のキー
    prop_name: str                             # プロパティ名
    widget: 'LayoutItem'                       # バインドされたウィジェット
    meta: dict                                 # 追加メタデータ
    on_change: Optional[Callable[[Any], None]] # 値変更コールバック
    _last_value: Any = None                    # 前回同期時の値
    _last_data_id: Optional[int] = None        # 前回同期時のデータオブジェクト ID

    def sync(self, provider: ContextProvider, context: bpy.types.Context) -> tuple[bool, bool]:
        """
        ウィジェットの値を RNA から同期

        Returns:
            (is_valid, has_changed):
            - is_valid: True=同期成功, False=データが無効
            - has_changed: True=値またはデータ参照が変化した
        """
        data = provider.get(self.data_key, context)
        if data is None:
            return (False, True)  # データなし、変化あり扱い

        try:
            # データ参照の変更を検知
            current_data_id = id(data)
            data_changed = current_data_id != self._last_data_id
            self._last_data_id = current_data_id

            # プロパティ値の変更を検知
            value = get_property_value(data, self.prop_name)
            value_changed = not self._values_equal(value, self._last_value)
            self._last_value = self._copy_value(value)

            # 変更があればウィジェットを更新
            if data_changed or value_changed:
                self._update_widget(data, value)

            return (True, data_changed or value_changed)
        except (ReferenceError, AttributeError):
            return (False, True)
```

### 3.4 GPULayout の拡張

```python
class GPULayout:
    def __init__(self, ...):
        # ... existing code ...

        # Reactive Context
        self._context_provider: Optional[ContextProvider] = None
        self._bindings: list[PropertyBinding] = []
        self._last_context_hash: Optional[int] = None

    def set_context_provider(self, provider: ContextProvider) -> None:
        """コンテキストプロバイダを設定"""
        self._context_provider = provider

    def prop(self, data_key: str, property: str, *, text: str = "", ...) -> Optional[LayoutItem]:
        """
        プロパティをバインド（リアクティブ版）

        Args:
            data_key: ContextProvider に登録されたキー（例: "object", "scene.render"）
            property: プロパティ名

        Note:
            従来の prop(data, property, ...) との後方互換性は別メソッドで維持
        """
        if self._context_provider is None:
            raise ValueError("ContextProvider not set. Call set_context_provider() first.")

        # 現在のコンテキストから一時的にデータを取得（UI構築用）
        context = bpy.context
        data = self._context_provider.get(data_key, context)

        if data is None:
            # データがない場合はプレースホルダーを表示
            self.label(text=f"{text or property}: (No Data)")
            return None

        # プロパティ情報を取得
        info = get_property_info(data, property)
        if info is None:
            self.label(text=f"{text or property}: (Invalid Property)")
            return None

        # ウィジェットを作成
        display_text = text if text else info.name
        current_value = get_property_value(data, property)

        # on_change コールバックを遅延生成
        def make_on_change():
            def on_change(new_value):
                ctx = bpy.context
                current_data = self._context_provider.get(data_key, ctx)
                if current_data is not None:
                    set_property_value(current_data, property, new_value)
            return on_change

        widget = self._create_reactive_widget(
            data, property, info, display_text, current_value, make_on_change()
        )

        if widget:
            # バインディングを登録
            binding = PropertyBinding(
                data_key=data_key,
                prop_name=property,
                widget=widget,
                meta={'is_dynamic_enum': info.is_dynamic_enum},
                on_change=make_on_change(),
            )
            self._bindings.append(binding)

        return widget

    def sync_reactive(self, context: bpy.types.Context) -> None:
        """
        リアクティブバインディングを同期

        従来の sync_props() に代わる新メソッド
        """
        if self._context_provider is None:
            return

        # コンテキスト変更を検知
        context_hash = self._compute_context_hash(context)
        if context_hash != self._last_context_hash:
            self._last_context_hash = context_hash
            self.mark_dirty()  # UI 再構築をトリガー

        # バインディングを同期
        valid_bindings = []
        for binding in self._bindings:
            if binding.sync(self._context_provider, context):
                valid_bindings.append(binding)
            # 無効なバインディングは削除

        self._bindings = valid_bindings

        # 子レイアウトも同期
        for child in self._children:
            child.sync_reactive(context)

    def _compute_context_hash(self, context: bpy.types.Context) -> int:
        """
        コンテキストのハッシュを計算

        選択オブジェクト、アクティブモードなどの変更を検知
        """
        parts = []

        # アクティブオブジェクトのポインタ
        if context.object:
            parts.append(id(context.object))
        else:
            parts.append(0)

        # オブジェクトモード
        if context.object:
            parts.append(context.object.mode)

        # アクティブマテリアル
        if context.object and context.object.active_material:
            parts.append(id(context.object.active_material))

        return hash(tuple(parts))
```

---

## 4. 使用例

### 4.1 基本的な使用

```python
class PME_OT_gpu_panel(bpy.types.Operator):
    bl_idname = "pme.gpu_panel"
    bl_label = "GPU Panel"

    def invoke(self, context, event):
        # コンテキストプロバイダを設定
        self._provider = ContextProvider()
        self._provider.register("object", lambda ctx: ctx.object)
        self._provider.register("render", lambda ctx: ctx.scene.render)

        # レイアウトを作成
        self._layout = GPULayout(x=100, y=500, width=300)
        self._layout.set_context_provider(self._provider)

        # UI を構築
        self._build_ui()

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _build_ui(self):
        layout = self._layout
        layout.label(text="Object Properties")

        # リアクティブ prop（data_key を使用）
        layout.prop("object", "hide_viewport", text="Hide")
        layout.prop("object", "name", text="Name")
        layout.prop("render", "engine", text="Render Engine", expand=True)

    def modal(self, context, event):
        # リアクティブ同期（選択変更に追従）
        self._layout.sync_reactive(context)

        # 描画
        if self._layout.dirty:
            self._layout.layout()
        self._layout.draw()

        return {'PASS_THROUGH'}
```

### 4.2 コンテキスト変更時の自動再構築

```python
def modal(self, context, event):
    # コンテキストが大きく変わった場合（モード変更など）は UI を再構築
    if self._should_rebuild(context):
        self._rebuild_ui(context)

    self._layout.sync_reactive(context)
    self._layout.draw()

def _should_rebuild(self, context) -> bool:
    """UI 再構築が必要か判定"""
    # 例: オブジェクトモードが変わった
    current_mode = context.object.mode if context.object else None
    if current_mode != self._last_mode:
        self._last_mode = current_mode
        return True
    return False
```

---

## 5. 移行計画

### Phase 1: ContextProvider 実装
- `ContextProvider` クラスを `ui/gpu/context.py` に追加
- 既存コードに影響なし

### Phase 2: PropertyBinding 実装
- `PropertyBinding` クラスを追加
- `GPULayout` に `_bindings` と `sync_reactive()` を追加

### Phase 3: 新 API の導入
- `prop(data_key, property)` シグネチャを追加
- 従来の `prop(data, property)` は後方互換として維持

### Phase 4: テストと検証
- `test_reactive_layout.py` でリアルタイム追従をテスト
- パフォーマンス測定

### Phase 5: 既存コードの移行
- `test_layout.py` を新 API に移行
- ドキュメント更新

---

## 6. パフォーマンス考慮事項

### 6.1 キャッシュ戦略

```python
# 同一フレーム内では getter を再実行しない
class ContextProvider:
    def get(self, key: str, context: bpy.types.Context) -> Any:
        # フレームベースのキャッシュ
        if current_frame == self._cache_frame and key in self._cache:
            return self._cache[key]
```

### 6.2 Dirty Flag の活用

```python
# 変更がなければ再描画をスキップ
def modal(self, context, event):
    self._layout.sync_reactive(context)

    if self._layout.dirty:
        self._layout.layout()  # 位置計算

    self._layout.draw()  # 描画は常に実行（GPU は高速）
```

### 6.3 選択的同期

```python
# 変更があったバインディングのみ更新
def sync_reactive(self, context):
    for binding in self._bindings:
        if binding.needs_sync(context):  # 変更検知
            binding.sync(...)
```

---

## 7. 将来の拡張

### 7.1 Computed Properties

```python
# 計算プロパティのサポート
layout.computed(
    getter=lambda ctx: len(ctx.selected_objects),
    format=lambda n: f"Selected: {n} objects",
)
```

### 7.2 Conditional Visibility

```python
# コンテキストに応じた表示切り替え
layout.prop("object", "hide_viewport", visible_when=lambda ctx: ctx.object is not None)
```

### 7.3 Depsgraph Integration

```python
# depsgraph_update_post handler との統合
@bpy.app.handlers.depsgraph_update_post
def on_update(scene, depsgraph):
    for panel in GPUPanelManager.get_active_panels():
        panel.layout.invalidate()
```

---

## 8. 参照

- Blender Python API: [bpy.types.Context](https://docs.blender.org/api/current/bpy.types.Context.html)
- Blender Python API: [Application Handlers](https://docs.blender.org/api/current/bpy.app.handlers.html)
- React Hooks: [useContext](https://react.dev/reference/react/useContext) - 類似コンセプト
