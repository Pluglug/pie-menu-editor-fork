# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout System

Blender UILayout API を模した GPU 描画レイアウトシステム。

Phase 1: 読み取り専用レイアウト（ツールチップ向け）
Phase 2: インタラクティブ要素（ボタン、トグル）

使用例:
    from pie_menu_editor.ui.gpu import GPULayout, GPULayoutStyle, GPUTooltip

    # スタイル取得
    style = GPULayoutStyle.from_blender_theme('TOOLTIP')

    # レイアウト作成
    layout = GPULayout(x=100, y=100, width=300, style=style)
    layout._draw_background = True
    layout._draw_outline = True

    layout.label(text="Hello", icon='INFO')
    row = layout.row()
    row.label(text="Left")
    row.label(text="Right")

    layout.separator()
    layout.draw()

    # ツールチップ
    tooltip = GPUTooltip()
    tooltip.title("Add Cube")
    tooltip.description("シーンに立方体プリミティブを追加します")
    tooltip.draw(x, y)

参考: bl_ui_widgets (GPL-3.0) https://github.com/mmmrqs/bl_ui_widgets
"""

# Style & Enums
from .style import (
    GPULayoutStyle,
    Direction,
    Alignment,
    SHADER_NAME,
    FONT_ID,
)

# Drawing Utilities
from .drawing import (
    GPUDrawing,
    BLFDrawing,
    IconDrawing,
    CORNER_SEGMENTS,
    CIRCLE_SEGMENTS,
)

# Layout Items
from .items import (
    LayoutItem,
    LabelItem,
    SeparatorItem,
    ButtonItem,
    ToggleItem,
    PropDisplayItem,
    BoxItem,
)

# Main Layout
from .layout import GPULayout

# Tooltip
from .tooltip import GPUTooltip

# Interactive
from .interactive import (
    HitRect,
    HitTestManager,
    InteractionState,
    UIState,
    ItemRenderState,
)


__all__ = [
    # Style
    'GPULayoutStyle',
    'Direction',
    'Alignment',
    'SHADER_NAME',
    'FONT_ID',
    # Drawing
    'GPUDrawing',
    'BLFDrawing',
    'IconDrawing',
    'CORNER_SEGMENTS',
    'CIRCLE_SEGMENTS',
    # Items
    'LayoutItem',
    'LabelItem',
    'SeparatorItem',
    'ButtonItem',
    'ToggleItem',
    'PropDisplayItem',
    'BoxItem',
    # Layout
    'GPULayout',
    # Tooltip
    'GPUTooltip',
    # Interactive
    'HitRect',
    'HitTestManager',
    'InteractionState',
    'UIState',
    'ItemRenderState',
]
