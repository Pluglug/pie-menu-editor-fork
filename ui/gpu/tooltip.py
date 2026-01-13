# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Tooltip Builder

ツールチップ専用の簡易ビルダー。
"""

from __future__ import annotations

import bpy
from typing import Optional

from .style import GPULayoutStyle
from .drawing import BLFDrawing
from .items import LabelItem
from .layout import GPULayout


class GPUTooltip:
    """
    ツールチップ専用の簡易ビルダー

    使用例:
        tooltip = GPUTooltip()
        tooltip.title("Add Cube")
        tooltip.description("シーンに立方体プリミティブを追加します")
        tooltip.shortcut("Shift + A > M > C")
        tooltip.python("bpy.ops.mesh.primitive_cube_add()")

        # マウス位置の近くに描画
        tooltip.draw(mouse_x + 20, mouse_y - 10)
    """

    def __init__(self, max_width: float = 400):
        self.max_width = max_width
        self._title_text: str = ""
        self._description_text: str = ""
        self._shortcut_text: str = ""
        self._python_text: str = ""
        self._style = GPULayoutStyle.from_blender_theme('TOOLTIP')

    def title(self, text: str) -> GPUTooltip:
        """タイトルを設定"""
        self._title_text = text
        return self

    def description(self, text: str) -> GPUTooltip:
        """説明文を設定"""
        self._description_text = text
        return self

    def shortcut(self, text: str) -> GPUTooltip:
        """ショートカットを設定"""
        self._shortcut_text = text
        return self

    def python(self, text: str) -> GPUTooltip:
        """Python コマンドを設定"""
        self._python_text = text
        return self

    def _build_layout(self, x: float, y: float) -> Optional[GPULayout]:
        """内部でレイアウトを構築"""
        # Blender の show_tooltips_python 設定を確認
        show_python = bpy.context.preferences.view.show_tooltips_python

        # コンテンツがなければ None を返す
        if not any([self._title_text, self._description_text,
                    self._shortcut_text, self._python_text and show_python]):
            return None

        # 幅を計算
        width = self._calc_width()

        # レイアウト作成
        layout = GPULayout(x=x, y=y, width=width, style=self._style)
        layout._draw_background = True
        layout._draw_outline = True

        # タイトル
        if self._title_text:
            layout.label(text=self._title_text)

        # 説明文（折り返し）
        if self._description_text:
            if self._title_text:
                layout.separator(factor=0.5)

            lines = BLFDrawing.wrap_text(
                self._description_text,
                width - self._style.scaled_padding() * 2,
                self._style.scaled_text_size()
            )
            for line in lines:
                layout.label(text=line)

        # ショートカット
        if self._shortcut_text:
            layout.separator(factor=0.5)
            # グレー色で表示
            item = LabelItem(
                text=self._shortcut_text,
                text_color=self._style.text_color_secondary
            )
            layout._add_item(item)

        # Python コマンド
        if self._python_text and show_python:
            layout.separator(factor=0.5)
            # さらに暗いグレーで表示
            item = LabelItem(
                text=self._python_text,
                text_color=self._style.text_color_disabled
            )
            layout._add_item(item)

        return layout

    def calc_size(self, x: float = 0, y: float = 0) -> tuple[float, float]:
        """
        ツールチップのサイズを計算

        Returns:
            (width, height) タプル。コンテンツがなければ (0, 0)
        """
        layout = self._build_layout(x, y)
        if layout is None:
            return (0.0, 0.0)

        # レイアウト計算を実行
        layout.layout()
        return (layout.width, layout.calc_height())

    def draw(self, x: float, y: float) -> float:
        """
        ツールチップを描画

        Returns:
            描画した高さ（重ならないように次の要素を配置するため）
        """
        layout = self._build_layout(x, y)
        if layout is None:
            return 0.0

        layout.draw()
        return layout.calc_height()

    def _calc_width(self) -> float:
        """必要な幅を計算"""
        text_size = self._style.scaled_text_size()
        max_text_width = 0

        for text in [self._title_text, self._shortcut_text, self._python_text]:
            if text:
                w, _ = BLFDrawing.get_text_dimensions(text, text_size)
                max_text_width = max(max_text_width, w)

        # 説明文は折り返されるので max_width を超えない
        return min(max_text_width + self._style.scaled_padding() * 2, self.max_width)
