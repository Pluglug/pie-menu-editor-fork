# GPUPanelOperator 設計書

> Version: 0.4.0 (Draft)
> Created: 2026-01-19
> Status: **Design Phase**
> Related: `ui/gpu/test_layout.py`, Issue #100

---

## 概要

`GPUPanelMixin` は GPU 描画によるオーバーレイパネルの Mixin クラス。
開発者は `draw_panel()` メソッドのみ実装すれば、ドラッグ移動・リサイズ・
閉じるボタンなどの機能を持つパネルを作成できる。

### 設計目標

1. **シンプルな API**: `bpy.types.Panel` の `draw()` と同じ感覚
2. **オペレーターベース**: Blender エコシステム（キーマップ、メニュー）と統合
3. **PME 統合**: PME のホットキーシステムで呼び出し可能
4. **Mixin パターン**: ローダー側で Operator との合成を制御可能
5. **再利用可能**: 他の開発者・アドオンでも利用可能な設計

---

## アーキテクチャ

### パッケージ構造

PME では `api/` ディレクトリが公開 API を提供し、`import pme` でアクセス可能。

```
pie_menu_editor/
├── api/                          ← 公開 API（import pme でアクセス）
│   ├── __init__.py               ← pme モジュール本体
│   ├── _types.py                 ← ExecuteResult, PMHandle など
│   ├── dev.py                    ← pme.dev.* 開発者ユーティリティ
│   ├── gpu.py                    ← pme.gpu.* GPU パネル操作（新規）
│   └── types.py                  ← pme.types.* 公開型（新規）
├── ui/
│   └── gpu/
│       ├── panel_mixin.py        ← GPUPanelMixin（新規）
│       ├── state.py              ← GPUPanelState（新規）
│       ├── panel_manager.py      ← GPUPanelManager
│       └── layout.py             ← GPULayout
└── addon.py                      ← GPUPanelOperator 合成
```

### pme.py 削除と移行

**タイミング**: 2.0.0 RC 前に削除

**移行パス**:

| 現在の使用方法 | 移行後 |
|--------------|--------|
| `from pie_menu_editor import pme` | `import pme`（変更なし）|
| `from pie_menu_editor.pme import ...` | `from pme import ...` |

**なぜ変更不要か**:

PME は `addon.py` の register 時に `sys.modules['pme'] = api` を設定しているため、
`import pme` は既に `api/__init__.py` を参照している。`pme.py` は現在 dead code である。

**内部参照の移行**（PME 内部のみ影響）:

```python
# Before: 相対 import（動作するが非推奨）
from .pme import context

# After: 絶対 import に統一
import pme
pme.context
```

**削除手順**:
1. PME 内部の `from .pme import ...` を洗い出し
2. `import pme` への書き換え
3. `pme.py` 削除
4. RC ビルド

### Mixin パターン

`GPUPanelMixin` は Operator を直接継承せず、ローダー側で合成する。

```
┌─────────────────────────────────────────────────────────┐
│ ui/gpu/panel_mixin.py                                   │
│                                                         │
│   class GPUPanelMixin:                                  │
│       """Mixin: Operator と組み合わせて使う"""          │
│       gpu_panel_uid: str                                │
│       def draw_panel(self, layout, context): ...        │
│       def _modal_impl(self, context, event): ...        │
│       def _invoke_impl(self, context, event): ...       │
│       def _cancel_impl(self, context): ...              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ addon.py (ローダー)                                     │
│                                                         │
│   from bpy.types import Operator                        │
│   from .ui.gpu import GPUPanelMixin                     │
│                                                         │
│   class GPUPanelOperator(Operator, GPUPanelMixin):      │
│       """合成されたクラス"""                            │
│       def modal(self, context, event):                  │
│           return self._modal_impl(context, event)       │
│       def invoke(self, context, event):                 │
│           return self._invoke_impl(context, event)      │
│       def cancel(self, context):                        │
│           return self._cancel_impl(context)             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ api/types.py (公開 API)                                 │
│                                                         │
│   from ..addon import GPUPanelOperator                  │
│   __all__ = ['GPUPanelOperator']                        │
└─────────────────────────────────────────────────────────┘
```

### 利点

- ローダーが Operator の継承を制御できる
- 他の Mixin と組み合わせ可能
- テスト時にモックしやすい
- 将来的なパッケージ単体提供時に PME 依存を除去可能

---

## クラス設計

### GPUPanelMixin

```python
from dataclasses import dataclass
from typing import ClassVar

class GPUPanelMixin:
    """GPU描画パネルの Mixin クラス

    Usage:
        from pme.types import GPUPanelOperator

        class MY_OT_panel(GPUPanelOperator):
            bl_idname = "my.panel"
            bl_label = "My Panel"

            gpu_panel_uid = "my_panel"
            gpu_title = "My Panel"

            def draw_panel(self, layout, context):
                layout.label(text="Hello World")
    """

    # ═══════════════════════════════════════════════════════════════
    # クラス変数（サブクラスでオーバーライド）
    # ═══════════════════════════════════════════════════════════════

    gpu_panel_uid: str = ""
    """パネルの一意識別子（必須）。
    重複チェックに使用。同一 uid のパネルは同時に1つしか開けない。
    """

    gpu_space_type: str = 'VIEW_3D'
    """パネルを表示するエディタタイプ。
    'VIEW_3D', 'IMAGE_EDITOR', 'NODE_EDITOR', etc.
    """

    gpu_width: int = 250
    """パネルの初期幅（ピクセル）。"""

    gpu_style: str = 'PANEL'
    """GPULayoutStyle のプリセット名。
    'PANEL', 'MENU', 'TOOLTIP', 'BOX', etc.
    """

    gpu_title: str = ""
    """タイトルバーのテキスト。空文字ならタイトルバー非表示。"""

    gpu_resizable: bool = True
    """リサイズ可能かどうか。"""

    gpu_show_close: bool = True
    """閉じるボタンを表示するか。gpu_title が空の場合は無視。"""

    gpu_default_x: int = 50
    """初期位置 X（リージョン左端からのオフセット）。"""

    gpu_default_y_offset: int = 50
    """初期位置 Y（リージョン上端からのオフセット）。"""

    gpu_close_on: set[str] = {'ESC'}
    """パネルを閉じるイベントタイプのセット。
    空セットなら閉じるボタンまたはトグル操作のみで閉じる。
    例: {'ESC'}, {'ESC', 'RIGHTMOUSE'}, set()
    """

    # ═══════════════════════════════════════════════════════════════
    # メソッド（サブクラスでオーバーライド）
    # ═══════════════════════════════════════════════════════════════

    def draw_panel(self, layout: 'GPULayout', context) -> None:
        """パネルの内容を描画（必須）。

        Args:
            layout: GPULayout インスタンス。UILayout 風の API を持つ。
            context: bpy.context

        Example:
            def draw_panel(self, layout, context):
                layout.label(text="Settings")
                layout.prop(context.scene.render, "resolution_percentage")
        """
        pass

    # Note: poll() は Operator 標準の @classmethod poll(cls, context) を使用

    # ═══════════════════════════════════════════════════════════════
    # 内部状態（Mixin で管理）
    # ═══════════════════════════════════════════════════════════════

    _manager: 'GPUPanelManager' = None
    _layout: 'GPULayout' = None
    _should_close: bool = False
    _panel_x: float | None = None
    _panel_y: float | None = None

    # パネル内で消費すべきマウスイベント
    _CONSUME_EVENTS: ClassVar[set] = {
        'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE',
        'WHEELUPMOUSE', 'WHEELDOWNMOUSE',
    }

    # ═══════════════════════════════════════════════════════════════
    # プライベートメソッド（内部実装）
    # ═══════════════════════════════════════════════════════════════
    # 以下のメソッドは GPUPanelMixin 内に実装される。
    # test_layout.py の各デモから抽出した共通パターン。

    def _get_window_region(self, context) -> 'bpy.types.Region | None':
        """WINDOW タイプのリージョンを取得

        Args:
            context: Blender コンテキスト

        Returns:
            WINDOW リージョン、または None（見つからない場合）

        Note:
            context.region は modal() 呼び出し時に HEADER など別のリージョンを
            指している場合があるため、明示的に WINDOW リージョンを検索する。
        """
        ...

    def _rebuild_layout(self, context, region: 'bpy.types.Region') -> None:
        """GPULayout を再構築し、draw_panel() を呼び出す

        Args:
            context: Blender コンテキスト
            region: WINDOW リージョン

        Side Effects:
            - self._layout を新規作成または更新
            - self._layout.x/y を self._panel_x/_panel_y から復元
            - self.draw_panel() を呼び出してウィジェットを追加
            - self._layout.build() を呼び出してレイアウト計算

        Note:
            毎フレーム呼ばれる。パネル内容が動的に変化する場合に対応。
            パフォーマンス上の理由から、将来的に dirty フラグによる
            スキップ機構を追加する可能性あり。
        """
        ...

    def _draw_callback(self, manager: 'GPUPanelManager', context) -> None:
        """GPU 描画コールバック（SpaceView3D.draw_handler で呼ばれる）

        Args:
            manager: GPUPanelManager インスタンス
            context: 描画時のコンテキスト（modal 時と異なる場合あり）

        Side Effects:
            - self._layout.draw() を呼び出してパネルを描画

        Note:
            draw_handler_add() に渡されるコールバック。
            manager.should_draw(context) で描画判定を行う。
        """
        ...

    def _restore_position(self) -> None:
        """永続化された位置を self._panel_x/y に復元"""
        ...

    def _save_position(self) -> None:
        """現在の位置を永続化ストレージに保存"""
        ...
```

---

## 基底クラスの実装

### _modal_impl

```python
def _modal_impl(self, context, event):
    context.area.tag_redraw()

    # クローズ要求チェック
    if self._should_close:
        self._cancel_impl(context)
        return {'CANCELLED'}

    # gpu_close_on で指定されたイベントで閉じる
    if event.type in self.gpu_close_on and event.value == 'PRESS':
        self._cancel_impl(context)
        return {'CANCELLED'}

    # レイアウト再構築
    region = self._get_window_region(context)
    self._rebuild_layout(context, region)

    # prop() ウィジェットの値を RNA から同期
    if self._layout:
        self._layout.sync_props()

    # イベント処理
    if self._manager:
        handled = self._manager.handle_event(event, context)
        if self._layout:
            self._panel_x = self._layout.x
            self._panel_y = self._layout.y
        if handled:
            return {'RUNNING_MODAL'}

        # パネル内でのマウスイベントは消費
        if event.type in self._CONSUME_EVENTS:
            if self._manager.contains_point(event.mouse_region_x, event.mouse_region_y):
                return {'RUNNING_MODAL'}

    return {'PASS_THROUGH'}
```

### _invoke_impl

```python
def _invoke_impl(self, context, event):
    # エリアタイプチェック
    if context.area.type != self.gpu_space_type:
        self.report({'WARNING'}, f"{self.gpu_space_type} で実行してください")
        return {'CANCELLED'}

    # Note: poll() は Operator 標準の poll() が事前に呼ばれる

    # 重複チェック → トグル動作
    if GPUPanelManager.is_active(self.gpu_panel_uid):
        GPUPanelManager.close_by_uid(self.gpu_panel_uid, context)
        return {'CANCELLED'}

    # 初期化
    self._should_close = False
    self._layout = None
    self._manager = None
    self._restore_position()  # 永続化された位置を復元

    # レイアウト構築
    region = self._get_window_region(context)
    self._rebuild_layout(context, region)

    if self._layout is None:
        self.report({'ERROR'}, "レイアウトの作成に失敗しました")
        return {'CANCELLED'}

    # マネージャー作成
    self._manager = GPUPanelManager(self.gpu_panel_uid, self._layout)
    if not self._manager.open(context, self._draw_callback, self.gpu_space_type):
        self.report({'ERROR'}, "パネルを開けませんでした")
        return {'CANCELLED'}

    context.window_manager.modal_handler_add(self)
    return {'RUNNING_MODAL'}
```

### _cancel_impl

```python
def _cancel_impl(self, context):
    self._save_position()  # 位置を永続化

    if self._manager:
        self._manager.close(context)
        self._manager = None

    self._layout = None
```

---

## 永続化

### 注意事項

**永続化はセッション限定（メモリのみ）**。Blender 再起動後はリセットされる。
ファイルへの保存が必要な場合は、将来的に `addon_prefs` への保存を検討。

### GPUPanelState（スキーマ）

```python
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class GPUPanelState:
    """パネルの永続化状態（セッション限定）"""
    x: Optional[float] = None  # None = 未保存（デフォルト位置を使用）
    y: Optional[float] = None
    width: float = 250.0
    # 将来拡張
    # anchor: str = 'TOP_LEFT'
    # collapsed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'GPUPanelState':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def has_position(self) -> bool:
        """位置が保存されているかどうか"""
        return self.x is not None and self.y is not None
```

### ストレージ

```python
# ui/gpu/state.py
_gpu_panel_states: dict[str, GPUPanelState] = {}

def get_panel_state(uid: str) -> GPUPanelState:
    """パネルの状態を取得。存在しなければデフォルト状態を返す。"""
    return _gpu_panel_states.setdefault(uid, GPUPanelState())

def set_panel_state(uid: str, state: GPUPanelState) -> None:
    """パネルの状態を保存。"""
    _gpu_panel_states[uid] = state

def clear_panel_states() -> None:
    """全パネル状態をクリア（テスト用）。"""
    _gpu_panel_states.clear()
```

### GPUPanelMixin での使用

```python
def _restore_position(self) -> None:
    state = get_panel_state(self.gpu_panel_uid)
    if state.has_position:
        self._panel_x = state.x
        self._panel_y = state.y
    # else: デフォルト位置を使用（gpu_default_x, gpu_default_y_offset）

def _save_position(self) -> None:
    if self._panel_x is not None and self._panel_y is not None:
        state = GPUPanelState(x=self._panel_x, y=self._panel_y)
        set_panel_state(self.gpu_panel_uid, state)
```

---

## PME API

### api/gpu.py モジュール

```python
# api/gpu.py
"""GPU パネル操作の公開 API

Usage:
    import pme
    pme.gpu.is_panel_open("my_panel")
    pme.gpu.close_panel("my_panel")
"""

from ..ui.gpu.panel_manager import GPUPanelManager
from ..ui.gpu.state import (
    get_panel_state as _get_state,  # 内部用エイリアス
    GPUPanelState,
)

__all__ = [
    "is_panel_open",
    "close_panel",
    "list_open_panels",
    "get_panel_state",
    "GPUPanelState",  # 型も公開
]


def is_panel_open(uid: str) -> bool:
    """指定 uid の GPU パネルが開いているか確認

    Args:
        uid: パネルの一意識別子

    Returns:
        パネルが開いていれば True

    Stability: Experimental
    """
    return GPUPanelManager.is_active(uid)


def close_panel(uid: str) -> bool:
    """指定 uid の GPU パネルを閉じる

    Args:
        uid: パネルの一意識別子

    Returns:
        パネルが存在して閉じられたら True

    Stability: Experimental
    """
    return GPUPanelManager.close_by_uid(uid)


def list_open_panels() -> list[str]:
    """開いている GPU パネルの uid リストを返す

    Returns:
        アクティブなパネルの uid リスト

    Stability: Experimental
    """
    return GPUPanelManager.list_active_uids()


def get_panel_state(uid: str) -> GPUPanelState:
    """パネルの永続化状態を取得

    Args:
        uid: パネルの一意識別子

    Returns:
        GPUPanelState オブジェクト

    Stability: Experimental
    """
    return _get_state(uid)
```

### GPUPanelManager への追加メソッド

```python
# ui/gpu/panel_manager.py に追加

@classmethod
def list_active_uids(cls) -> list[str]:
    """アクティブなパネルの uid リストを返す"""
    return list(cls._active.keys())
```

### api/types.py モジュール

```python
# api/types.py
"""PME 公開型

Usage:
    from pme.types import GPUPanelOperator

    class MY_OT_panel(GPUPanelOperator):
        ...
"""

from ..addon import GPUPanelOperator
from ..ui.gpu.state import GPUPanelState

__all__ = ['GPUPanelOperator', 'GPUPanelState']
```

### api/__init__.py への追加

```python
# api/__init__.py に追加

__all__ = [
    # ... 既存のエクスポート ...
    # GPU Panel API (submodule)
    "gpu",    # pme.gpu.* - GPU パネル操作
    "types",  # pme.types.* - 公開型
]

# サブモジュールのインポート
from . import gpu
from . import types
```

### 使用例

```python
import pme
from pme.types import GPUPanelOperator

# パネル状態の確認
if pme.gpu.is_panel_open("my_panel"):
    print("Panel is open")

# パネルを閉じる
pme.gpu.close_panel("my_panel")

# 開いているパネル一覧
for uid in pme.gpu.list_open_panels():
    print(f"Open: {uid}")

# パネルクラスの定義
class MY_OT_panel(GPUPanelOperator):
    bl_idname = "my.panel"
    bl_label = "My Panel"

    gpu_panel_uid = "my_panel"
    gpu_title = "My Panel"

    def draw_panel(self, layout, context):
        layout.label(text="Hello World")
```

---

## 状態アクセス API

```python
class GPUPanelMixin:
    # ...

    @classmethod
    def is_open(cls) -> bool:
        """このパネルが現在開いているかを返す。"""
        return GPUPanelManager.is_active(cls.gpu_panel_uid)
```

### 外部からの使用例

```python
# クラスメソッド経由
if QUICK_OT_viewport_settings.is_open():
    print("Viewport settings panel is open")

# pme.gpu API 経由
if pme.gpu.is_panel_open("quick_viewport"):
    print("Viewport settings panel is open")

# 直接オペレーター呼び出し（トグル動作）
bpy.ops.quick.viewport_settings('INVOKE_DEFAULT')
```

---

## 使用例

### 基本的なパネル

```python
from pme.types import GPUPanelOperator

class QUICK_OT_viewport(GPUPanelOperator):
    bl_idname = "quick.viewport"
    bl_label = "Quick Viewport"
    bl_options = {'REGISTER'}

    gpu_panel_uid = "quick_viewport"
    gpu_space_type = 'VIEW_3D'
    gpu_width = 220
    gpu_title = "Quick Viewport"

    def draw_panel(self, layout, context):
        space = context.space_data
        tool = context.scene.tool_settings

        layout.label(text="Display")
        layout.prop(space.overlay, "show_overlays", toggle=1)
        layout.prop(space.overlay, "show_wireframes")

        layout.separator()
        layout.label(text="Snapping")
        layout.prop(tool, "use_snap", toggle=1)
```

### poll を使ったパネル

```python
class EDIT_OT_mesh_tools(GPUPanelOperator):
    """Edit Mesh 専用のツールパネル"""
    bl_idname = "edit.mesh_tools"
    bl_label = "Mesh Tools"

    gpu_panel_uid = "edit_mesh_tools"
    gpu_title = "Mesh Tools"

    @classmethod
    def poll(cls, context):
        # Operator 標準の poll() を使用
        return context.mode == 'EDIT_MESH'

    def draw_panel(self, layout, context):
        layout.operator("mesh.subdivide", text="Subdivide")
        layout.operator("mesh.extrude_region_move", text="Extrude")
```

### ESC で閉じないパネル

```python
class PERSISTENT_OT_panel(GPUPanelOperator):
    """ESC で閉じない常駐パネル"""
    bl_idname = "persistent.panel"
    bl_label = "Persistent Panel"

    gpu_panel_uid = "persistent_panel"
    gpu_title = "Persistent"
    gpu_close_on = set()  # 空セット → ESC で閉じない

    def draw_panel(self, layout, context):
        layout.label(text="閉じるボタンまたはトグルで閉じる")
```

### 状態を持つパネル

```python
class COUNTER_OT_panel(GPUPanelOperator):
    bl_idname = "counter.panel"
    bl_label = "Counter"

    gpu_panel_uid = "counter_panel"
    gpu_title = "Counter"

    _count: int = 0

    def draw_panel(self, layout, context):
        layout.label(text=f"Count: {self._count}")
        layout.operator(text="Increment", on_click=self._increment)
        layout.operator(text="Reset", on_click=self._reset)

    def _increment(self):
        self._count += 1

    def _reset(self):
        self._count = 0
```

---

## 実装計画

### Phase 1: Mixin 抽出

1. `test_layout.py` から共通コードを抽出
2. `ui/gpu/panel_mixin.py` に `GPUPanelMixin` を作成
3. `ui/gpu/state.py` に `GPUPanelState` を作成

### Phase 2: ローダー統合

1. `addon.py` で `GPUPanelOperator` を合成
2. 既存デモを `GPUPanelOperator` 継承に書き換え
3. トグル動作・`gpu_close_on` を実装

### Phase 3: API 整備

1. `api/gpu.py` に公開 API を作成
2. `api/types.py` に型エクスポートを追加
3. `GPUPanelManager.list_active_uids()` を実装
4. `api/__init__.py` にサブモジュールを追加

### Phase 4: PME 統合（将来）

1. PME の uid システムとの連携検討
2. PME メニューからの呼び出しサポート
3. PME エディタでの管理 UI

---

## 受け入れ条件と検証手順

### Acceptance Criteria

| ID | 条件 | 検証方法 |
|----|------|---------|
| AC-1 | `GPUPanelOperator` を継承して `draw_panel()` のみ実装したクラスが動作する | 最小サンプルを実行 |
| AC-2 | 同一 uid のパネルは同時に 1 つしか開けない | 2回連続で invoke → 2回目でトグル閉じ |
| AC-3 | トグル動作：開いている状態で再度呼び出すと閉じる | オペレーターを2回呼び出し |
| AC-4 | `gpu_close_on` で指定したイベントでパネルが閉じる | ESC キーでパネルが閉じる |
| AC-5 | `gpu_close_on = set()` でイベント閉じを無効化できる | ESC を押しても閉じない |
| AC-6 | パネル位置がセッション内で永続化される | 閉じて再度開くと同じ位置 |
| AC-7 | 複数リージョン（4分割ビュー等）で正しいリージョンのみ描画 | 4分割で1つのリージョンのみに表示 |
| AC-8 | `pme.gpu.is_panel_open()` が正しく動作する | API 呼び出しで状態を確認 |
| AC-9 | `pme.gpu.close_panel()` が正しく動作する | API 呼び出しでパネルを閉じる |
| AC-10 | Operator 標準の `poll()` が機能する | Edit Mode 以外で呼び出し不可を確認 |

### 検証手順（Manual Testing）

#### 基本動作

```python
# Blender コンソールで実行
import bpy

# 1. パネルを開く
bpy.ops.gpu_test.quick_viewport('INVOKE_DEFAULT')
# → パネルが表示される（AC-1）

# 2. 同じオペレーターを再度呼び出す
bpy.ops.gpu_test.quick_viewport('INVOKE_DEFAULT')
# → パネルが閉じる（AC-2, AC-3）

# 3. 再度開く
bpy.ops.gpu_test.quick_viewport('INVOKE_DEFAULT')
# → パネルが表示される

# 4. ESC キーを押す
# → パネルが閉じる（AC-4）
```

#### 永続化

```python
# 1. パネルを開く
bpy.ops.gpu_test.quick_viewport('INVOKE_DEFAULT')

# 2. パネルをドラッグして移動

# 3. 閉じるボタンで閉じる

# 4. 再度開く
bpy.ops.gpu_test.quick_viewport('INVOKE_DEFAULT')
# → 移動した位置に表示される（AC-6）
```

#### API

```python
import pme

# 1. パネルを開く
bpy.ops.gpu_test.quick_viewport('INVOKE_DEFAULT')

# 2. API で確認
print(pme.gpu.is_panel_open("quick_viewport"))  # True（AC-8）
print(pme.gpu.list_open_panels())  # ['quick_viewport']

# 3. API で閉じる
pme.gpu.close_panel("quick_viewport")  # True（AC-9）
print(pme.gpu.is_panel_open("quick_viewport"))  # False
```

#### 複数リージョン

```
1. 3D View を4分割（View > Area > Toggle Quad View）
2. 左上のリージョンにマウスを置いてパネルを開く
3. 確認: パネルは左上リージョンのみに表示される（AC-7）
4. 他のリージョンにマウスを移動
5. 確認: パネルは左上リージョンにのみ表示され続ける
```

#### gpu_close_on 無効化

```python
# 1. gpu_close_on = set() のパネルを開く
bpy.ops.gpu_test.persistent_panel('INVOKE_DEFAULT')

# 2. ESC キーを押す
# → パネルは閉じない（AC-5）

# 3. 閉じるボタンをクリック
# → パネルが閉じる
```

### 自動テスト（将来）

```python
# tests/test_gpu_panel.py（将来実装）
class TestGPUPanelOperator:
    def test_toggle_behavior(self):
        """AC-2, AC-3: トグル動作"""
        ...

    def test_close_on_esc(self):
        """AC-4: ESC で閉じる"""
        ...

    def test_close_on_disabled(self):
        """AC-5: gpu_close_on = set() で ESC 無効"""
        ...

    def test_position_persistence(self):
        """AC-6: 位置永続化"""
        ...
```

---

## 関連ファイル

| ファイル | 役割 |
|----------|------|
| `ui/gpu/panel_mixin.py` | GPUPanelMixin クラス（新規） |
| `ui/gpu/state.py` | GPUPanelState, 永続化関数（新規） |
| `ui/gpu/layout.py` | GPULayout 実装 |
| `ui/gpu/panel_manager.py` | GPUPanelManager 実装 |
| `ui/gpu/test_layout.py` | デモ・テスト用オペレーター |
| `addon.py` | GPUPanelOperator 合成 |
| `api/gpu.py` | 公開 API（新規） |
| `api/types.py` | 型エクスポート（新規） |
| `api/__init__.py` | pme モジュール本体（サブモジュール追加） |

---

## 未解決事項

- [ ] 複数パネル間のマウスイベント奪い合い解消
- [ ] PME uid システムとの統合方式（将来）

### 後回し（ユースケースが出てから）

- リサイズ時の width 永続化
- パネル位置のアンカー（TOP_LEFT, TOP_RIGHT, etc.）
- パネルグループ（呼び出し側で管理）
- on_panel_open/close コールバック
- ファイルへの永続化（addon_prefs）

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 0.1.0 | 2026-01-19 | 初版作成 |
| 0.2.0 | 2026-01-19 | Mixin パターン、gpu_close_on、PME API 追加 |
| 0.3.0 | 2026-01-19 | api/ 構造に合わせて修正、レビュー指摘対応 |
| 0.4.0 | 2026-01-19 | pme.py 移行パス明記、ヘルパー契約追加、AC・検証手順追加 |

### 0.4.0 での修正（レビュー指摘対応）

- **High**: pme.py 削除と移行パスを明記（RC 前削除、既存コードへの影響なし）
- **Medium**: `_get_window_region`, `_rebuild_layout`, `_draw_callback` の契約（引数、戻り値、副作用）を追加
- **Low**: api/gpu.py の `get_panel_state` シャドーイング修正（`_get_state` エイリアス使用）
- **Low**: 受け入れ条件（AC-1〜AC-10）と検証手順を追加

### 0.3.0 での修正（レビュー指摘対応）

- **High**: `pme/` パッケージ → `api/` ディレクトリに修正（`pme.py` 削除方針を反映）
- **Medium**: `request_close()` → `close_by_uid()` に修正（実装に合わせる）
- **Medium**: `_active_panels` → `_active` に修正、`list_active_uids()` 公開メソッド追加
- **Low**: `manager.py` → `panel_manager.py` に修正
- **Low**: 位置の 0.0 問題 → `Optional[float]` + `has_position` プロパティで対応
- **Low**: 永続化がセッション限定であることを明記

---

*Last Updated: 2026-01-19*
