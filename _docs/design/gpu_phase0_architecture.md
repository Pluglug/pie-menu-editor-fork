# GPU Layout Phase 0: Architecture Improvements

> Status: **Design**
> Created: 2026-01-15
> Related: #104 (GPU Layout Tracking)

---

## 問題分析

### 1. フェーズ混在

**現状**:
```python
# layout.py:621-624
def draw(self) -> None:
    """GPU 描画を実行"""
    # レイアウト計算
    self.layout()  # ❌ Paint フェーズで Layout を実行
```

**問題**:
- 予測不可能な挙動（draw() のたびにレイアウトが変わる可能性）
- パフォーマンス問題（毎フレーム再計算）
- Dirty Flag 最適化の妨げ

### 2. 状態管理の散在

**現状**:
```
LayoutItem (items.py)
├── ButtonItem._hovered, _pressed  # 状態 A
├── ToggleItem._hovered            # 状態 B
└── ...

HitTestManager (interactive.py)
├── InteractionState.hovered       # 状態 C (HitRect への参照)
├── InteractionState.pressed       # 状態 D
└── ...

GPULayout (layout.py)
└── _close_button_hovered          # 状態 E
```

**問題**:
- 同じ概念（hovered/pressed）が複数箇所に存在
- 同期が必要だが漏れやすい
- テストが困難

### 3. イベント処理の二重実装

**現状**:
- `ButtonItem.handle_event()` - 個別アイテムのイベント処理
- `HitTestManager.handle_event()` - 集中管理のイベント処理

**問題**:
- どちらを使うべきか曖昧
- 両方が動作すると予期せぬ挙動

### 4. イベント伝播モデルの不完全さ

**現状**: Bubble のみ（子優先で処理）
**不足**: Capture phase、stopPropagation

---

## 解決設計

### Step 1: フェーズ分離の明確化

```python
class GPULayout:
    _dirty: bool = True  # Dirty Flag

    def mark_dirty(self) -> None:
        """レイアウトの再計算が必要であることをマーク"""
        self._dirty = True
        for child in self._children:
            child.mark_dirty()

    def layout(self) -> None:
        """レイアウト計算（変更時のみ）"""
        if not self._dirty:
            return
        self._layout_internal()
        self._dirty = False

    def draw(self) -> None:
        """描画のみ（レイアウト計算は行わない）"""
        # layout() を呼ばない - 呼び出し側の責任
        self._draw_internal()

    def update_and_draw(self) -> None:
        """便利メソッド: レイアウト + 描画"""
        self.layout()
        self.draw()
```

**呼び出し側の変更**:
```python
# Before
layout.draw()  # 内部で layout() も呼ぶ

# After
layout.layout()  # 明示的
layout.draw()    # 描画のみ
# または
layout.update_and_draw()  # 便利メソッド
```

### Step 2: 状態管理の集中化

**新規: `UIState` dataclass**

```python
# interactive.py に追加

@dataclass
class UIState:
    """UI 状態の集中管理"""
    hovered_id: Optional[str] = None
    pressed_id: Optional[str] = None
    focused_id: Optional[str] = None
    dragging_id: Optional[str] = None

    def clear(self) -> None:
        self.hovered_id = None
        self.pressed_id = None
        self.focused_id = None
        self.dragging_id = None


@dataclass
class ItemRenderState:
    """描画時に参照するアイテム状態"""
    hovered: bool = False
    pressed: bool = False
    focused: bool = False
    enabled: bool = True
```

**HitTestManager の変更**:
```python
class HitTestManager:
    _ui_state: UIState  # 集中管理

    def get_render_state(self, item_id: str) -> ItemRenderState:
        """描画用の状態を取得"""
        return ItemRenderState(
            hovered=self._ui_state.hovered_id == item_id,
            pressed=self._ui_state.pressed_id == item_id,
            focused=self._ui_state.focused_id == item_id,
        )
```

**LayoutItem の変更**:
```python
@dataclass
class ButtonItem(LayoutItem):
    # _hovered, _pressed を削除
    item_id: str = ""  # 一意識別子を追加

    def draw(self, style: GPULayoutStyle, state: ItemRenderState) -> None:
        # state から hovered/pressed を参照
        if state.pressed:
            bg_color = style.button_press_color
        elif state.hovered:
            bg_color = style.button_hover_color
        ...
```

### Step 3: イベント伝播の改善

**新規: `UIEvent` dataclass**

```python
@dataclass
class UIEvent:
    """UI イベント（DOM 風モデル）"""
    type: str  # 'mouse_move', 'click', 'hover_enter', 'hover_leave', etc.
    mouse_x: float = 0
    mouse_y: float = 0
    target: Optional[HitRect] = None

    # イベント制御
    _consumed: bool = field(default=False, repr=False)
    _propagation_stopped: bool = field(default=False, repr=False)

    def consume(self) -> None:
        """イベントを消費（他のハンドラーに渡さない）"""
        self._consumed = True

    def stop_propagation(self) -> None:
        """バブリングを停止"""
        self._propagation_stopped = True

    @property
    def consumed(self) -> bool:
        return self._consumed

    @property
    def propagation_stopped(self) -> bool:
        return self._propagation_stopped
```

**HitTestManager の変更**:
```python
class HitTestManager:
    def dispatch(self, event: UIEvent) -> bool:
        """イベントをディスパッチ"""
        # Target phase
        if event.target:
            self._handle_target(event)
            if event.consumed:
                return True

        # Bubble phase（現在の実装に近い）
        if not event.propagation_stopped:
            self._handle_bubble(event)

        return event.consumed
```

---

## 実装順序

| Phase | タスク | 影響範囲 | 互換性 |
|-------|--------|----------|--------|
| 0-A | フェーズ分離 | layout.py, test_layout.py | 低リスク |
| 0-B | UIState 導入 | interactive.py, items.py, layout.py | 中リスク |
| 0-C | UIEvent 導入 | interactive.py | 低リスク |

### Phase 0-A: フェーズ分離（最優先）

1. `draw()` から `layout()` 呼び出しを削除
2. `update_and_draw()` 便利メソッドを追加
3. `test_layout.py` を更新
4. Dirty Flag を導入（オプショナル）

### Phase 0-B: 状態管理集中化

1. `UIState`, `ItemRenderState` を追加
2. `ButtonItem`, `ToggleItem` から `_hovered`, `_pressed` を削除
3. `draw()` シグネチャを変更
4. `HitTestManager.get_render_state()` を追加

### Phase 0-C: イベント伝播改善

1. `UIEvent` を追加
2. `HitTestManager.dispatch()` を実装
3. 既存の `handle_event()` を内部で `dispatch()` に委譲

---

## マイグレーションパス

### 呼び出し側の変更（test_layout.py）

```python
# Before
self._layout.draw()

# After (Option 1: 明示的)
self._layout.layout()
self._layout.draw()

# After (Option 2: 便利メソッド)
self._layout.update_and_draw()
```

### 描画メソッドの変更（items.py）

```python
# Before
def draw(self, style: GPULayoutStyle) -> None:
    if self._pressed:
        ...

# After
def draw(self, style: GPULayoutStyle, state: ItemRenderState) -> None:
    if state.pressed:
        ...
```

---

## 検証項目

- [ ] `TEST_OT_gpu_layout` が正常動作
- [ ] `TEST_OT_gpu_interactive` が正常動作
- [ ] ドラッグが動作する
- [ ] クローズボタンが動作する
- [ ] ホバー状態が正しく表示される
- [ ] プレス状態が正しく表示される

---

## 参考

- [Flutter Layout Constraints](https://flutter.dev/docs/development/ui/layout/constraints)
- [React Reconciliation](https://reactjs.org/docs/reconciliation.html)
- [DOM Event Model](https://www.w3.org/TR/DOM-Level-3-Events/)
