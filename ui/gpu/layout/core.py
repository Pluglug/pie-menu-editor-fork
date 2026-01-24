# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Main Layout Class

Blender UILayout API を模した GPU 描画レイアウトシステム。
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ..style import GPULayoutStyle, Direction, Alignment, SizingPolicy
from ..items import LayoutItem
from ..interactive import HitTestManager, HitRect
from ..binding import ContextResolverCache, PropertyBinding
from ..uilayout_stubs import UILayoutStubMixin
from .constants import MIN_PANEL_WIDTH
from .containers import LayoutContainerMixin
from .props import LayoutPropMixin
from .utils import LayoutUtilityMixin
from .flow import LayoutFlowMixin
from .panel import LayoutPanelMixin
from .render import LayoutRenderMixin
from .interaction import LayoutInteractionMixin


class GPULayout(
    LayoutContainerMixin,
    LayoutPropMixin,
    LayoutUtilityMixin,
    LayoutFlowMixin,
    LayoutPanelMixin,
    LayoutRenderMixin,
    LayoutInteractionMixin,
    UILayoutStubMixin,
):
    """
    Blender UILayout を模した GPU 描画レイアウトシステム

    使用例:
        layout = GPULayout(x=100, y=500, width=300)
        layout.label(text="Title", icon='INFO')

        row = layout.row()
        row.label(text="Left")
        row.label(text="Right")

        layout.separator()
        layout.prop_display(context.object, "name", text="Object")

        layout.operator(text="Click Me", on_click=lambda: print("Clicked!"))

        # 描画
        layout.draw()

        # イベント処理（modal オペレーター内で）
        layout.handle_event(event)
    """

    def __init__(self, x: float, y: float, width: float,
                 style: Optional[GPULayoutStyle] = None,
                 direction: Direction = Direction.VERTICAL,
                 parent: Optional[GPULayout] = None):
        """
        Args:
            x: 左上 X 座標
            y: 左上 Y 座標（Blender は左下原点なので注意）
            width: 幅
            style: スタイル（None の場合は Blender テーマから自動取得）
            direction: レイアウト方向
            parent: 親レイアウト
        """
        self.x = x
        self.y = y
        self.width = width
        self.style = style or GPULayoutStyle.from_blender_theme()
        self.direction = direction
        self.parent = parent

        # 統合要素リスト（追加順序を保持）
        # Phase 1: _items と _children を _elements に統合
        self._elements: list[LayoutItem | GPULayout] = []
        self._layout_path: str = "root" if parent is None else ""
        self._path_counters: dict[str, int] = {}

        # 2-pass レイアウト用の測定結果
        self._measured_widths: list[float] = []
        self._measured_gap: float = 0.0
        self.height: float = 0.0  # measure() で計算される

        # Phase 1 v3: width sizing policy (measure results, fixed width)
        self.sizing = SizingPolicy()

        # Phase 1 v3: estimated height (measure phase)
        self.estimated_height: float = 0.0

        # カーソル位置
        self._cursor_x = x + self.style.scaled_padding_x()
        self._cursor_y = y - self.style.scaled_padding_y()

        # 状態プロパティ（UILayout 互換）
        self.active: bool = True
        self.active_default: bool = False  # Return key activates operator button
        self.activate_init: bool = False   # Auto-activate buttons in popups
        self.enabled: bool = True
        self.alert: bool = False
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self._alignment: Alignment = Alignment.EXPAND
        # emboss: 'NORMAL', 'NONE', 'PULLDOWN_MENU', 'PIE_MENU', 'NONE_OR_STATUS'
        self.emboss: str = "NORMAL"
        # ui_units for fixed sizing
        self.ui_units_x: float = 0.0
        self.ui_units_y: float = 0.0
        # Property layout options
        self.use_property_split: bool = False
        self.use_property_decorate: bool = False
        self.operator_context: str = "INVOKE_DEFAULT"

        # アイテム間スペースを制御（align=True で 0）
        self._align: bool = False

        # split 用（0.0 = 自動計算、0.0-1.0 = 最初の column の割合）
        self._split_factor: float = 0.0
        self._is_split: bool = False
        self._split_column_index: int = 0  # column() が呼ばれるたびにインクリメント

        # heading (row/column の見出し)
        self._heading: str = ""

        # ボックス描画フラグ
        self._draw_background: bool = False
        self._draw_outline: bool = False

        # タイトルバー
        self._show_title_bar: bool = False
        self._title: str = ""
        self._show_close_button: bool = False
        self._on_close: Optional[Callable[[], None]] = None
        self._title_bar_rect: Optional[HitRect] = None
        self._close_button_rect: Optional[HitRect] = None
        self._close_button_hovered: bool = False

        self._hit_manager: Optional[HitTestManager] = None

        # Dirty Flag: レイアウト再計算が必要かどうか
        self._dirty: bool = True

        # リサイズハンドル
        self._show_resize_handle: bool = False
        self._resize_handle_rect: Optional[HitRect] = None
        self._resize_handle_hovered: bool = False
        self._panel_uid: Optional[str] = None
        self._min_width: float = MIN_PANEL_WIDTH

        # 境界クランプ用のリージョンサイズ（None = クランプ無効）
        self._region_width: Optional[float] = None
        self._region_height: Optional[float] = None

        # prop() reactive bindings (context-resolved) and static fallback
        self._context_tracker: Optional[Any] = None
        self._context_cache = ContextResolverCache()
        self._bindings: list[PropertyBinding] = []
        self._static_bindings: list[PropertyBinding] = []
        self._epoch = 0

    @property
    def alignment(self) -> Alignment:
        return self._alignment

    @alignment.setter
    def alignment(self, value: Alignment | str) -> None:
        if isinstance(value, Alignment):
            self._alignment = value
            return
        if isinstance(value, str):
            try:
                self._alignment = Alignment[value]
            except KeyError as exc:
                raise ValueError(f"Unknown alignment: {value}") from exc
            return
        raise TypeError(f"Alignment must be Alignment or str, got {type(value).__name__}")

    @property
    def hit_manager(self) -> Optional[HitTestManager]:
        """HitTestManager（未使用なら None）"""
        return self._hit_manager

    @property
    def dirty(self) -> bool:
        """レイアウト再計算が必要かどうか"""
        return self._dirty

    @property
    def _items(self) -> list[LayoutItem]:
        """LayoutItem のみをフィルタして返す（後方互換）"""
        return [e for e in self._elements if isinstance(e, LayoutItem)]

    @property
    def _children(self) -> list['GPULayout']:
        """GPULayout のみをフィルタして返す（後方互換）"""
        return [e for e in self._elements if isinstance(e, GPULayout)]

    def mark_dirty(self) -> None:
        """レイアウトの再計算が必要であることをマーク"""
        self._dirty = True

    def reset_for_rebuild(self, *, preserve_hovered: bool = False) -> None:
        """
        既存レイアウトを再構築できる状態に戻す

        Note:
            同一インスタンス上で draw_panel() を再実行する用途向け。
        """
        self._elements.clear()
        self._path_counters.clear()
        self._measured_widths = []
        self._measured_gap = 0.0
        padding_x, padding_y = self._get_padding()
        self._cursor_x = self.x + padding_x
        self._cursor_y = self.y - padding_y
        self._split_column_index = 0
        self._bindings.clear()
        self._static_bindings.clear()
        self._context_tracker = None
        if self._hit_manager:
            self._hit_manager.reset_rects(preserve_hovered=preserve_hovered)
        # 既存の HitRect は再登録させる（titlebar/close/resize など）
        self._title_bar_rect = None
        self._close_button_rect = None
        self._resize_handle_rect = None
        self._close_button_hovered = False
        self._resize_handle_hovered = False
        self._dirty = True
        for element in self._elements:
            if isinstance(element, GPULayout):
                element.mark_dirty()


# Inject GPULayout into mixin module namespaces for runtime lookups.
from . import containers as _containers  # noqa: E402
from . import flow as _flow  # noqa: E402
from . import interaction as _interaction  # noqa: E402
from . import props as _props  # noqa: E402
from . import render as _render  # noqa: E402
from . import utils as _utils  # noqa: E402

_containers.GPULayout = GPULayout
_flow.GPULayout = GPULayout
_interaction.GPULayout = GPULayout
_props.GPULayout = GPULayout
_render.GPULayout = GPULayout
_utils.GPULayout = GPULayout
