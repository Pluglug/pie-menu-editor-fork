# GPU_DIALOG 実装計画

> Version: 0.1.0 (Draft)
> Created: 2026-01-19
> Status: **Planning**
> Related: Issue #100, `gpu_panel_operator.md`

---

## 概要

GPU_DIALOG は DIALOG モードの GPU 描画版。GPUPanelMixin を使用して、
ユーザーが定義した PMI（アイテム）を GPULayout で描画する新しい Editor タイプ。

### 目標

1. 既存 DIALOG と同じユーザーカスタマイズ体験
2. GPU 描画による柔軟な表現（将来的にアニメーション等）
3. GPUPanelMixin/GPUPanelOperator の実用例

---

## 前提条件（完了済み）

| コンポーネント | 状態 | 場所 |
|--------------|------|------|
| GPUPanelMixin | ✅ | `ui/gpu/panel_mixin.py` |
| GPUPanelState | ✅ | `ui/gpu/state.py` |
| GPULayout | ✅ | `ui/gpu/layout.py` |
| UILayoutStubMixin | ✅ | `ui/gpu/uilayout_stubs.py` |
| ExecutionFrame | ✅ | `ui/gpu/execution.py` |

---

## アーキテクチャ

### PMI → GPULayout 変換フロー

```
┌─ PME 既存システム ────────────────────────────────────────────┐
│                                                                │
│  PMItem Collection (Preferences に保存)                       │
│  ├─ [0] mode='COMMAND', name='Add Cube', text='bpy.ops...'   │
│  ├─ [1] mode='CUSTOM', text='L.label("Custom")'              │
│  ├─ [2] mode='PROP', text='C.object.location'                │
│  └─ [3] mode='EMPTY', text='row?'                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌─ 変換レイヤー ────────────────────────────────────────────────┐
│                                                                │
│  draw_pme_layout(pm, layout, _draw_item)                      │
│  └─ ui/layout.py:734                                          │
│                                                                │
│  _draw_item(pr, pm, pmi, idx)                                 │
│  └─ operators/__init__.py:1170                                │
│      ├─ COMMAND → layout.operator() or lh.operator()         │
│      ├─ CUSTOM  → ExecutionFrame + exec(pmi.text)            │
│      ├─ PROP    → layout.prop()                              │
│      ├─ MENU    → サブメニュー展開                            │
│      └─ EMPTY   → レイアウト制御 (row, spacer)               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌─ GPU 描画 ────────────────────────────────────────────────────┐
│                                                                │
│  GPULayout (UILayoutStubMixin 継承)                           │
│  ├─ label(), separator()           ✅ 実装済み               │
│  ├─ prop()                         ⚠️ 基本対応               │
│  ├─ operator()                     ⚠️ OperatorProperties     │
│  └─ row(), column(), box()         ✅ 実装済み               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Custom モード実行の仕組み

```python
# operators/__init__.py:1367-1396
if GPULayout and isinstance(layout, GPULayout):
    # GPU 環境用の実行フレーム
    tracker = ContextTracker(bl_context)
    bpy_proxy = BpyContextProxy(tracker)

    with ExecutionFrame(
        pme.context,
        bpy.context,
        layout=layout,           # L = GPULayout
        context_tracker=tracker, # C = ContextTracker
        bpy_proxy=bpy_proxy,     # bpy = BpyContextProxy
    ):
        exec_globals = pme.context.gen_globals()
        pme.context.exe(pmi.text, exec_globals)
```

**重要**: Custom コードの GPU 対応は **既に実装済み**。

---

## 実装タスク

### Phase 1: プロトタイプ（test_layout.py）

**目的**: 既存 DIALOG メニューを GPU で描画できるか検証

```python
# test_layout.py に追加
class PROTO_OT_gpu_dialog(Operator, GPUPanelMixin):
    """GPU DIALOG プロトタイプ"""
    bl_idname = "proto.gpu_dialog"
    bl_label = "Proto: GPU Dialog"

    gpu_panel_uid = "proto_gpu_dialog"
    gpu_title = "GPU Dialog Proto"

    # 描画対象の DIALOG メニュー名
    target_menu: StringProperty()

    def draw_panel(self, layout, context):
        pr = get_prefs()
        if self.target_menu not in pr.pie_menus:
            layout.label(text=f"Menu not found: {self.target_menu}")
            return

        pm = pr.pie_menus[self.target_menu]

        # 既存の draw_pme_layout を流用
        # lh.lt(layout) で GPULayout を設定
        lh.lt(layout)
        draw_pme_layout(pm, layout, WM_OT_pme_user_pie_menu_call._draw_item)
```

**検証項目**:
- [ ] COMMAND モード（operator 呼び出し）
- [ ] CUSTOM モード（ユーザーコード実行）
- [ ] PROP モード（プロパティ表示）
- [ ] レイアウト制御（row, spacer）

### Phase 2: Editor 作成

**ファイル**: `editors/gpu_dialog.py`

```python
LAYER = "editors"

from ..core.schema import schema
from .base import EditorBase

# GPU_DIALOG 用スキーマ（DIALOG と同様）
schema.BoolProperty("gd", "gd_title", True)
schema.BoolProperty("gd", "gd_box", True)
schema.IntProperty("gd", "gd_width", 300)

class Editor(EditorBase):
    def __init__(self):
        self.id = 'GPU_DIALOG'
        EditorBase.__init__(self)

        self.docs = "#GPU_Dialog_Editor"
        self.default_pmi_data = "gd?"
        self.supported_slot_modes = {'EMPTY', 'COMMAND', 'PROP', 'MENU', 'HOTKEY', 'CUSTOM'}

    def draw_extra_settings(self, layout, pm):
        EditorBase.draw_extra_settings(self, layout, pm)
        layout.prop(pm, "gd_title")
        layout.prop(pm, "gd_width")
```

### Phase 3: 定数・uid 追加

**`core/constants.py`**:
```python
ED_DATA = (
    # ... 既存 ...
    ('GPU_DIALOG', "GPU Dialog", 'GREASEPENCIL'),  # 追加
)
```

**`core/uid.py`**:
```python
MODE_PREFIX_MAP = {
    # ... 既存 ...
    'GPU_DIALOG': 'gd',  # 追加
}
```

### Phase 4: Runtime Operator

**GPUPanelMixin ベースの呼び出し Operator**:

```python
# operators/gpu_dialog.py (新規)
class WM_OT_pme_gpu_dialog_call(Operator, GPUPanelMixin):
    bl_idname = "wm.pme_gpu_dialog_call"
    bl_label = "PME GPU Dialog"

    pie_menu_name: StringProperty()

    @property
    def gpu_panel_uid(self):
        return f"pme_gpu_dialog_{self.pie_menu_name}"

    def draw_panel(self, layout, context):
        pr = get_prefs()
        pm = pr.pie_menus[self.pie_menu_name]
        lh.lt(layout)
        draw_pme_layout(pm, layout, self._draw_item)
```

---

## 既存コードとの統合ポイント

| ファイル | 変更内容 | 優先度 |
|---------|---------|--------|
| `core/constants.py` | ED_DATA に GPU_DIALOG 追加 | 高 |
| `core/uid.py` | MODE_PREFIX_MAP に 'gd' 追加 | 高 |
| `editors/gpu_dialog.py` | 新規 Editor 作成 | 高 |
| `operators/__init__.py` | _draw_item の GPU 対応確認 | 中（既に対応済み） |
| `ui/layout.py` | draw_pme_layout の GPULayout 対応 | 中 |
| `.claude/rules/json_schema_v2.md` | GPU_DIALOG セクション追加 | 低 |

---

## UILayout 互換性マトリクス

> 詳細: `gpu_uilayout_compatibility_matrix.md`

| メソッド | GPULayout | 備考 |
|---------|-----------|------|
| `label()` | ✅ | text, icon サポート |
| `separator()` | ✅ | factor サポート |
| `operator()` | ⚠️ | OperatorProperties で props 受け取り |
| `prop()` | ⚠️ | 基本対応、expand/slider サポート |
| `row()`, `column()` | ✅ | align サポート |
| `box()`, `split()` | ✅ | - |
| `menu()`, `popover()` | 🔲 | ラベルフォールバック |
| `template_*()` | 🔲 | 60+ メソッドスタブ化 |

---

## 課題と制限

### 1. lh (LayoutHelper) の GPULayout 対応

現在の `_draw_item` は `lh.operator()`, `lh.prop()` を使用。
GPULayout を `lh.lt(layout)` で設定すれば動作するか要検証。

### 2. operator() の実行タイミング

GPULayout の `operator()` は OperatorProperties を返すが、
実際の実行は `on_click` コールバック経由。PME の COMMAND モードと整合性を確認。

### 3. レイアウト制御（row, spacer）

DIALOG の `row?align=CENTER`, `spacer?hsep=COLUMN` などの
パース処理が GPULayout で正しく動作するか要検証。

---

## 参照ファイル

| ファイル | 内容 |
|---------|------|
| `ui/gpu/panel_mixin.py` | GPUPanelMixin 実装 |
| `ui/gpu/layout.py` | GPULayout 実装 |
| `ui/gpu/execution.py` | ExecutionFrame（Custom コード実行） |
| `ui/gpu/uilayout_stubs.py` | UILayout 互換スタブ |
| `ui/layout.py:734` | draw_pme_layout 関数 |
| `operators/__init__.py:1170` | _draw_item 関数 |
| `editors/popup.py` | DIALOG エディタ参考 |
| `editors/sticky_key.py` | 最小 Editor 参考 |

---

## 次のステップ

1. **プロトタイプ作成**: test_layout.py に PROTO_OT_gpu_dialog を追加
2. **動作検証**: 既存 DIALOG メニューを GPU 描画
3. **問題点洗い出し**: lh, operator(), レイアウト制御の互換性確認
4. **Editor 作成**: 問題解決後に正式な Editor を作成

---

*Last Updated: 2026-01-19*
