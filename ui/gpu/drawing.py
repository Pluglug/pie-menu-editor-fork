# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Drawing Utilities

低レベル GPU 描画、テキスト描画、アイコン描画。
"""

from __future__ import annotations

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from math import pi, cos, sin
from typing import Optional

from .style import SHADER_NAME, FONT_ID


# ═══════════════════════════════════════════════════════════════════════════════
# GPU Drawing - 図形描画
# ═══════════════════════════════════════════════════════════════════════════════

class GPUDrawing:
    """GPU 描画ユーティリティ"""

    _shader: gpu.types.GPUShader = None

    @classmethod
    def get_shader(cls) -> gpu.types.GPUShader:
        """シェーダーを取得（キャッシュ）"""
        if cls._shader is None:
            cls._shader = gpu.shader.from_builtin(SHADER_NAME)
        return cls._shader

    @classmethod
    def draw_rect(cls, x: float, y: float, width: float, height: float,
                  color: tuple[float, float, float, float]) -> None:
        """矩形を描画"""
        shader = cls.get_shader()
        vertices = (
            (x, y),
            (x + width, y),
            (x + width, y - height),
            (x, y - height),
        )
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_rounded_rect(cls, x: float, y: float, width: float, height: float,
                          radius: int, color: tuple[float, float, float, float],
                          corners: tuple[bool, bool, bool, bool] = (True, True, True, True)) -> None:
        """
        角丸矩形を描画

        Args:
            corners: (bottomLeft, topLeft, topRight, bottomRight)
        """
        shader = cls.get_shader()
        vertices = cls._calc_rounded_rect_vertices(x, y, width, height, radius, corners)
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_rounded_rect_outline(cls, x: float, y: float, width: float, height: float,
                                   radius: int, color: tuple[float, float, float, float],
                                   corners: tuple[bool, bool, bool, bool] = (True, True, True, True),
                                   line_width: float = 0.0) -> None:
        """
        角丸矩形のアウトラインを描画（ストローク方式）

        Args:
            line_width: ライン太さ（0.0 の場合は system.ui_line_width を使用）

        Note:
            GPU の LINE_LOOP は太い線で角が正しく接続されないため、
            内側と外側の 2 つのパスを TRIANGLE_STRIP で塗りつぶす方式を使用。
        """
        if line_width <= 0.0:
            line_width = bpy.context.preferences.system.ui_line_width

        # 細い線（1px 以下）の場合は従来の LINE_LOOP を使用
        if line_width <= 1.0:
            shader = cls.get_shader()
            vertices = cls._calc_rounded_rect_outline_vertices(x, y, width, height, radius, corners)
            batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": vertices})
            shader.bind()
            shader.uniform_float("color", color)
            gpu.state.blend_set('ALPHA')
            gpu.state.line_width_set(line_width)
            batch.draw(shader)
            gpu.state.blend_set('NONE')
            return

        # 太い線の場合はストローク描画（内外 2 パスの塗りつぶし）
        cls._draw_rounded_rect_stroke(x, y, width, height, radius, color, line_width, corners)

    @classmethod
    def _draw_rounded_rect_stroke(cls, x: float, y: float, width: float, height: float,
                                   radius: int, color: tuple[float, float, float, float],
                                   stroke_width: float,
                                   corners: tuple[bool, bool, bool, bool] = (True, True, True, True)) -> None:
        """
        ストローク方式で角丸矩形のアウトラインを描画

        内側と外側の頂点を交互に配置し、TRIANGLE_STRIP で描画することで
        均一な太さのストロークを実現。
        """
        shader = cls.get_shader()
        half = stroke_width / 2.0

        # セグメント数を固定（内外で同じ数にするため）
        segments = 8

        # 外側の頂点（元のサイズ + half）
        outer_radius = radius + int(half)
        outer_verts = cls._calc_rounded_rect_outline_vertices_fixed(
            x - half, y + half,
            width + stroke_width, height + stroke_width,
            outer_radius, corners, segments
        )

        # 内側の頂点（元のサイズ - half）
        inner_radius = max(0, radius - int(half))
        inner_verts = cls._calc_rounded_rect_outline_vertices_fixed(
            x + half, y - half,
            width - stroke_width, height - stroke_width,
            inner_radius, corners, segments
        )

        # TRIANGLE_STRIP 用に交互に配置
        vertices = []
        for i in range(len(outer_verts)):
            vertices.append(outer_verts[i])
            vertices.append(inner_verts[i])

        # 閉じる（最初の頂点ペアを追加）
        if len(outer_verts) > 0:
            vertices.append(outer_verts[0])
            vertices.append(inner_verts[0])

        batch = batch_for_shader(shader, 'TRI_STRIP', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def _calc_rounded_rect_outline_vertices_fixed(cls, x: float, y: float, width: float, height: float,
                                                   radius: int, corners: tuple[bool, bool, bool, bool],
                                                   segments: int = 8) -> list[tuple[float, float]]:
        """
        固定セグメント数で角丸矩形のアウトライン頂点を計算

        ストローク描画用に、セグメント数を固定して内外で頂点数を揃える。
        radius が 0 でも同じ頂点数を返す（角の位置に重複頂点を配置）。
        """
        r = max(0, min(radius, int(height / 2), int(width / 2)))

        vertices = []

        # 各角に (segments + 1) 個の頂点を配置（常に同じ数）
        # topLeft (corners[1]) - 角度 90° → 180°
        if corners[1] and r > 0:
            cx, cy = x + r, y - r
            for j in range(segments + 1):
                angle = pi / 2 * (1 + j / segments)
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            # 角丸なしでも同じ頂点数（全て同じ点）
            for _ in range(segments + 1):
                vertices.append((x, y))

        # bottomLeft (corners[0]) - 角度 180° → 270°
        if corners[0] and r > 0:
            cx, cy = x + r, y - height + r
            for j in range(segments + 1):
                angle = pi * (1 + 0.5 * j / segments)
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            for _ in range(segments + 1):
                vertices.append((x, y - height))

        # bottomRight (corners[3]) - 角度 270° → 360°
        if corners[3] and r > 0:
            cx, cy = x + width - r, y - height + r
            for j in range(segments + 1):
                angle = pi * (1.5 + 0.5 * j / segments)
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            for _ in range(segments + 1):
                vertices.append((x + width, y - height))

        # topRight (corners[2]) - 角度 0° → 90°
        if corners[2] and r > 0:
            cx, cy = x + width - r, y - r
            for j in range(segments + 1):
                angle = pi / 2 * j / segments
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            for _ in range(segments + 1):
                vertices.append((x + width, y))

        return vertices

    @classmethod
    def _calc_rounded_rect_outline_vertices(cls, x: float, y: float, width: float, height: float,
                                             radius: int, corners: tuple[bool, bool, bool, bool]) -> list[tuple[float, float]]:
        """
        角丸矩形のアウトライン用頂点を計算（中心点なし、LINE_LOOP 用）
        """
        r = min(radius, int(height / 2), int(width / 2))

        # 角丸なしの場合
        if r <= 0:
            return [
                (x, y),                    # topLeft
                (x, y - height),           # bottomLeft
                (x + width, y - height),   # bottomRight
                (x + width, y),            # topRight
            ]

        vertices = []
        segments = max(4, r)

        # topLeft (corners[1]) - 角度 90° → 180°
        if corners[1]:
            cx, cy = x + r, y - r
            for j in range(segments + 1):
                angle = pi / 2 * (1 + j / segments)
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            vertices.append((x, y))

        # bottomLeft (corners[0]) - 角度 180° → 270°
        if corners[0]:
            cx, cy = x + r, y - height + r
            for j in range(segments + 1):
                angle = pi * (1 + 0.5 * j / segments)
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            vertices.append((x, y - height))

        # bottomRight (corners[3]) - 角度 270° → 360°
        if corners[3]:
            cx, cy = x + width - r, y - height + r
            for j in range(segments + 1):
                angle = pi * (1.5 + 0.5 * j / segments)
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            vertices.append((x + width, y - height))

        # topRight (corners[2]) - 角度 0° → 90°
        if corners[2]:
            cx, cy = x + width - r, y - r
            for j in range(segments + 1):
                angle = pi / 2 * j / segments
                vertices.append((cx + r * cos(angle), cy + r * sin(angle)))
        else:
            vertices.append((x + width, y))

        return vertices

    @classmethod
    def _calc_rounded_rect_vertices(cls, x: float, y: float, width: float, height: float,
                                     radius: int, corners: tuple[bool, bool, bool, bool]) -> list[tuple[float, float]]:
        """
        角丸矩形の頂点を計算

        座標系: 左下原点、Y は上が正
        corners: (bottomLeft, topLeft, topRight, bottomRight)

        頂点順序（TRI_FAN 用）:
        center → topLeft → topRight → bottomRight → bottomLeft → topLeft（閉じる）
        """
        r = min(radius, int(height / 2), int(width / 2))

        # 中心点（TRI_FAN の起点）
        center = (x + width / 2, y - height / 2)
        vertices = [center]

        # 角丸なしの場合
        if r <= 0:
            vertices.extend([
                (x, y),                    # topLeft
                (x + width, y),            # topRight
                (x + width, y - height),   # bottomRight
                (x, y - height),           # bottomLeft
                (x, y),                    # topLeft（閉じる）
            ])
            return vertices

        segments = max(4, r)  # 角の滑らかさ

        # topLeft (corners[1]) - 角度 90° → 180°
        if corners[1]:
            cx, cy = x + r, y - r
            for j in range(segments + 1):
                angle = pi / 2 * (1 + j / segments)  # 90° → 180°
                vx = cx + r * cos(angle)
                vy = cy + r * sin(angle)
                vertices.append((vx, vy))
        else:
            vertices.append((x, y))

        # bottomLeft (corners[0]) - 角度 180° → 270°
        if corners[0]:
            cx, cy = x + r, y - height + r
            for j in range(segments + 1):
                angle = pi * (1 + 0.5 * j / segments)  # 180° → 270°
                vx = cx + r * cos(angle)
                vy = cy + r * sin(angle)
                vertices.append((vx, vy))
        else:
            vertices.append((x, y - height))

        # bottomRight (corners[3]) - 角度 270° → 360°
        if corners[3]:
            cx, cy = x + width - r, y - height + r
            for j in range(segments + 1):
                angle = pi * (1.5 + 0.5 * j / segments)  # 270° → 360°
                vx = cx + r * cos(angle)
                vy = cy + r * sin(angle)
                vertices.append((vx, vy))
        else:
            vertices.append((x + width, y - height))

        # topRight (corners[2]) - 角度 0° → 90°
        if corners[2]:
            cx, cy = x + width - r, y - r
            for j in range(segments + 1):
                angle = pi / 2 * j / segments  # 0° → 90°
                vx = cx + r * cos(angle)
                vy = cy + r * sin(angle)
                vertices.append((vx, vy))
        else:
            vertices.append((x + width, y))

        # 閉じる（最初の外周頂点に戻る）
        if corners[1]:
            cx, cy = x + r, y - r
            vx = cx + r * cos(pi / 2)
            vy = cy + r * sin(pi / 2)
            vertices.append((vx, vy))
        else:
            vertices.append((x, y))

        return vertices

    @classmethod
    def draw_line(cls, x1: float, y1: float, x2: float, y2: float,
                  color: tuple[float, float, float, float], width: float = 0.0) -> None:
        """
        線を描画

        Args:
            width: ライン太さ（0.0 の場合は system.ui_line_width を使用）
        """
        shader = cls.get_shader()
        vertices = ((x1, y1), (x2, y2))
        batch = batch_for_shader(shader, 'LINES', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)

        # ライン太さを設定（0.0 の場合はシステム推奨値を使用）
        if width <= 0.0:
            width = bpy.context.preferences.system.ui_line_width
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(width)
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_circle(cls, cx: float, cy: float, radius: float,
                    color: tuple[float, float, float, float],
                    segments: int = 16) -> None:
        """
        塗りつぶし円を描画

        Args:
            cx, cy: 中心座標
            radius: 半径
            color: 色 (RGBA)
            segments: 分割数（滑らかさ）
        """
        shader = cls.get_shader()

        # 中心点 + 円周上の頂点
        vertices = [(cx, cy)]
        for i in range(segments + 1):
            angle = 2 * pi * i / segments
            vertices.append((cx + radius * cos(angle), cy + radius * sin(angle)))

        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", color)
        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_rounded_line(cls, x1: float, y1: float, x2: float, y2: float,
                          color: tuple[float, float, float, float],
                          width: float = 0.0, segments: int = 8) -> None:
        """
        先端が丸い線を描画

        GPU の線描画は先端が平らなので、両端に円を追加して丸みを表現。

        Args:
            x1, y1: 始点
            x2, y2: 終点
            color: 色 (RGBA)
            width: ライン太さ（0.0 の場合は system.ui_line_width を使用）
            segments: 円の分割数
        """
        if width <= 0.0:
            width = bpy.context.preferences.system.ui_line_width

        # 線を描画
        cls.draw_line(x1, y1, x2, y2, color, width)

        # 先端の円を描画（半径は線の太さの半分）
        radius = width / 2.0
        if radius >= 1.0:
            cls.draw_circle(x1, y1, radius, color, segments)
            cls.draw_circle(x2, y2, radius, color, segments)

    @classmethod
    def draw_drop_shadow(cls, x: float, y: float, width: float, height: float,
                         radius: int, color: tuple[float, float, float, float],
                         offset: tuple[int, int] = (4, -4),
                         blur: int = 8) -> None:
        """
        ドロップシャドウを描画

        複数の半透明レイヤーを重ねてぼかし効果を近似。

        Args:
            x, y: 左上座標
            width, height: サイズ
            radius: 角丸半径
            color: シャドウ色 (RGBA)
            offset: オフセット (x, y)
            blur: ぼかし半径
        """
        if blur <= 0:
            # ぼかしなし - 単純なシャドウ
            cls.draw_rounded_rect(
                x + offset[0], y + offset[1],
                width, height, radius, color
            )
            return

        # ぼかし効果を近似（複数レイヤー）
        layers = min(blur, 6)  # 最大6レイヤー
        base_alpha = color[3]

        for i in range(layers, 0, -1):
            # 外側のレイヤーほど大きく、透明に
            expand = i * (blur / layers)
            layer_alpha = base_alpha * (1.0 - i / (layers + 1)) * 0.5

            layer_color = (color[0], color[1], color[2], layer_alpha)
            cls.draw_rounded_rect(
                x + offset[0] - expand / 2,
                y + offset[1] + expand / 2,
                width + expand,
                height + expand,
                radius + int(expand / 2),
                layer_color
            )


# ═══════════════════════════════════════════════════════════════════════════════
# BLF Drawing - テキスト描画
# ═══════════════════════════════════════════════════════════════════════════════

class BLFDrawing:
    """BLF テキスト描画ユーティリティ"""

    @classmethod
    def draw_text(cls, x: float, y: float, text: str,
                  color: tuple[float, float, float, float],
                  size: int = 13, font_id: int = FONT_ID) -> None:
        """テキストを描画"""
        blf.size(font_id, size)

        blf.color(font_id, *color)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, text)

    @classmethod
    def draw_text_with_shadow(cls, x: float, y: float, text: str,
                               color: tuple[float, float, float, float],
                               size: int = 13,
                               shadow_color: float = 0.0,
                               shadow_alpha: float = 0.5,
                               shadow_offset: tuple[int, int] = (1, -1),
                               font_id: int = FONT_ID) -> None:
        """シャドウ付きテキストを描画"""
        blf.size(font_id, size)

        # シャドウ
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, shadow_color, shadow_color, shadow_color, shadow_alpha)
        blf.shadow_offset(font_id, shadow_offset[0], shadow_offset[1])

        blf.color(font_id, *color)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, text)

        blf.disable(font_id, blf.SHADOW)

    @classmethod
    def get_text_dimensions(cls, text: str, size: int = 13, font_id: int = FONT_ID) -> tuple[float, float]:
        """テキストの幅と高さを取得"""
        blf.size(font_id, size)
        return blf.dimensions(font_id, text)

    @classmethod
    def wrap_text(cls, text: str, max_width: float, size: int = 13,
                  font_id: int = FONT_ID) -> list[str]:
        """テキストを指定幅で折り返し"""
        blf.size(font_id, size)

        lines = []
        for paragraph in text.split('\n'):
            if not paragraph:
                lines.append('')
                continue

            words = paragraph.split(' ')
            current_line = ''

            for word in words:
                test_line = f"{current_line} {word}".strip()
                width, _ = blf.dimensions(font_id, test_line)

                if width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

        return lines

    @classmethod
    def get_line_height(cls, size: int = 13, line_spacing: float = 1.2,
                        font_id: int = FONT_ID) -> float:
        """
        行の高さを取得（行間を含む）

        Args:
            size: フォントサイズ
            line_spacing: 行間係数（デフォルト 1.2x）
            font_id: フォント ID

        Returns:
            行の高さ（ピクセル）
        """
        blf.size(font_id, size)
        _, text_height = blf.dimensions(font_id, "Wg")  # 基準文字
        return text_height * line_spacing

    @classmethod
    def get_text_with_ellipsis(cls, text: str, max_width: float,
                                size: int = 13, font_id: int = FONT_ID,
                                ellipsis: str = "…") -> str:
        """
        テキストが max_width を超える場合、末尾に省略記号を追加

        二分探索で最適な切り詰め位置を見つける。
        日本語など CJK 文字も文字単位で正しく処理される。

        Args:
            text: 元のテキスト
            max_width: 最大幅（ピクセル）
            size: フォントサイズ
            font_id: フォント ID
            ellipsis: 省略記号（デフォルト: Unicode HORIZONTAL ELLIPSIS）

        Returns:
            max_width に収まるテキスト（必要に応じて省略記号付き）
        """
        blf.size(font_id, size)
        text_width, _ = blf.dimensions(font_id, text)

        if text_width <= max_width:
            return text

        ellipsis_width, _ = blf.dimensions(font_id, ellipsis)
        available_width = max_width - ellipsis_width

        if available_width <= 0:
            return ellipsis

        # 二分探索で最適な切り詰め位置を見つける
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            test_width, _ = blf.dimensions(font_id, text[:mid])
            if test_width <= available_width:
                low = mid
            else:
                high = mid - 1

        return text[:low] + ellipsis if low > 0 else ellipsis

    @classmethod
    def draw_text_clipped(cls, x: float, y: float, text: str,
                          color: tuple[float, float, float, float],
                          size: int, clip_rect: tuple[float, float, float, float],
                          font_id: int = FONT_ID) -> None:
        """
        クリッピング付きテキスト描画

        テキストが clip_rect の範囲外にはみ出す部分は描画されない。
        GPU レベルでのクリッピングなので、正確かつ高速。

        Args:
            x, y: テキスト位置（y は baseline）
            text: 描画するテキスト
            color: 色 (RGBA)
            size: フォントサイズ
            clip_rect: クリップ領域 (xmin, ymin, xmax, ymax)
            font_id: フォント ID
        """
        blf.size(font_id, size)
        blf.color(font_id, *color)
        blf.position(font_id, x, y, 0)

        # クリッピング有効化
        blf.enable(font_id, blf.CLIPPING)
        blf.clipping(font_id, clip_rect[0], clip_rect[1],
                     clip_rect[2], clip_rect[3])

        blf.draw(font_id, text)

        blf.disable(font_id, blf.CLIPPING)

    @classmethod
    def draw_text_clipped_with_shadow(cls, x: float, y: float, text: str,
                                       color: tuple[float, float, float, float],
                                       size: int,
                                       clip_rect: tuple[float, float, float, float],
                                       shadow_color: float = 0.0,
                                       shadow_alpha: float = 0.5,
                                       shadow_offset: tuple[int, int] = (1, -1),
                                       font_id: int = FONT_ID) -> None:
        """
        シャドウ + クリッピング付きテキスト描画

        テキストシャドウとクリッピングを組み合わせて、
        パネル内に収まる影付きテキストを描画する。

        Args:
            x, y: テキスト位置（y は baseline）
            text: 描画するテキスト
            color: 色 (RGBA)
            size: フォントサイズ
            clip_rect: クリップ領域 (xmin, ymin, xmax, ymax)
            shadow_color: シャドウの色（0.0=黒, 1.0=白）
            shadow_alpha: シャドウの透明度
            shadow_offset: シャドウのオフセット (x, y)
            font_id: フォント ID
        """
        blf.size(font_id, size)

        # クリッピング有効化
        blf.enable(font_id, blf.CLIPPING)
        blf.clipping(font_id, clip_rect[0], clip_rect[1],
                     clip_rect[2], clip_rect[3])

        # シャドウ有効化
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, shadow_color, shadow_color, shadow_color, shadow_alpha)
        blf.shadow_offset(font_id, shadow_offset[0], shadow_offset[1])

        blf.color(font_id, *color)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, text)

        # 無効化（順序は問わない）
        blf.disable(font_id, blf.SHADOW)
        blf.disable(font_id, blf.CLIPPING)

    @classmethod
    def calc_clip_rect(cls, x: float, y: float, width: float, height: float,
                       padding: int = 0) -> tuple[float, float, float, float]:
        """
        GPULayout 座標系からクリップ矩形を計算

        GPULayout では y は上端を指し、高さは下方向に伸びる。
        blf.clipping は (xmin, ymin, xmax, ymax) を期待する。

        Args:
            x, y: 左上座標（GPULayout 座標系）
            width, height: サイズ
            padding: 内側のパディング（オプション）

        Returns:
            クリップ矩形 (xmin, ymin, xmax, ymax)
        """
        return (
            x + padding,              # xmin
            y - height + padding,     # ymin (GPULayout: y - height が下端)
            x + width - padding,      # xmax
            y - padding               # ymax (GPULayout: y が上端)
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Icon Drawing - アイコン描画
# ═══════════════════════════════════════════════════════════════════════════════

class IconDrawing:
    """
    Blender アイコン描画ユーティリティ

    機能:
    - PNG ファイルからテクスチャをロードして GPU 描画
    - PME カスタムアイコン（ユーザー PNG）のサポート
    - Blender 内蔵アイコンは UILayout 経由でのみ使用可能

    使用例:
        # PNG ファイルから直接描画
        IconDrawing.draw_texture_file("/path/to/icon.png", x, y, 20, 20)

        # PME カスタムアイコン名で描画（PreviewsHelper 経由）
        IconDrawing.draw_custom_icon("my_icon", x, y)
    """

    # アイコンサイズ（Blender 標準、基準値）
    ICON_SIZE = 20

    @classmethod
    def get_scaled_icon_size(cls) -> int:
        """UI スケールを適用したアイコンサイズを取得"""
        return int(cls.ICON_SIZE * bpy.context.preferences.system.ui_scale)

    # シェーダーキャッシュ
    _image_shader: gpu.types.GPUShader = None

    # テクスチャキャッシュ: filepath -> (GPUTexture, width, height)
    _texture_cache: dict[str, tuple[gpu.types.GPUTexture, int, int]] = {}

    # PME カスタムアイコンのパスキャッシュ: icon_name -> filepath
    _icon_path_cache: dict[str, str] = {}

    @classmethod
    def get_image_shader(cls) -> gpu.types.GPUShader:
        """IMAGE_COLOR シェーダーを取得（キャッシュ）"""
        if cls._image_shader is None:
            cls._image_shader = gpu.shader.from_builtin('IMAGE_COLOR')
        return cls._image_shader

    @classmethod
    def get_icon_id(cls, icon_name: str) -> int:
        """Blender 内蔵アイコン名から ID を取得"""
        # TODO: Reserved for Blender built-in icons; currently unused.
        try:
            return bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items[icon_name].value
        except (KeyError, AttributeError):
            return 0

    @classmethod
    def load_texture(cls, filepath: str) -> Optional[tuple[gpu.types.GPUTexture, int, int]]:
        """
        PNG ファイルからテクスチャをロード

        Args:
            filepath: PNG ファイルのパス

        Returns:
            (GPUTexture, width, height) または None（失敗時）
        """
        # キャッシュをチェック
        if filepath in cls._texture_cache:
            return cls._texture_cache[filepath]

        try:
            import os
            if not os.path.exists(filepath):
                return None

            # Blender Image としてロード
            # 既存の同名イメージがあれば再利用
            img_name = f"_gpu_icon_{os.path.basename(filepath)}"
            if img_name in bpy.data.images:
                img = bpy.data.images[img_name]
                # ファイルパスが異なる場合は再読み込み
                if img.filepath != filepath:
                    img.filepath = filepath
                    img.reload()
            else:
                img = bpy.data.images.load(filepath)
                img.name = img_name

            # GPU テクスチャを作成
            texture = gpu.texture.from_image(img)
            result = (texture, img.size[0], img.size[1])

            # キャッシュに保存
            cls._texture_cache[filepath] = result
            return result

        except Exception as e:
            print(f"IconDrawing: Failed to load texture {filepath}: {e}")
            return None

    @classmethod
    def draw_texture(cls, texture: gpu.types.GPUTexture,
                     x: float, y: float, width: float, height: float,
                     alpha: float = 1.0) -> None:
        """
        テクスチャを描画

        Args:
            texture: GPUTexture オブジェクト
            x, y: 左上座標（Y は上から下へ減少）
            width, height: 描画サイズ
            alpha: 透明度 (0.0-1.0)
        """
        shader = cls.get_image_shader()

        # 頂点座標（左上から時計回り）
        # Blender の座標系: 左下原点、Y は上が正
        vertices = (
            (x, y),                    # 左上
            (x + width, y),            # 右上
            (x + width, y - height),   # 右下
            (x, y - height),           # 左下
        )

        # テクスチャ座標（左下原点）
        # 画像は左上原点なので Y を反転
        tex_coords = (
            (0.0, 1.0),  # 左上
            (1.0, 1.0),  # 右上
            (1.0, 0.0),  # 右下
            (0.0, 0.0),  # 左下
        )

        # インデックス（2つの三角形で矩形を構成）
        indices = ((0, 1, 2), (0, 2, 3))

        batch = batch_for_shader(
            shader, 'TRIS',
            {"pos": vertices, "texCoord": tex_coords},
            indices=indices
        )

        shader.bind()
        shader.uniform_float("color", (1.0, 1.0, 1.0, alpha))
        shader.uniform_sampler("image", texture)

        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_texture_file(cls, filepath: str,
                          x: float, y: float,
                          width: Optional[float] = None,
                          height: Optional[float] = None,
                          alpha: float = 1.0) -> bool:
        """
        PNG ファイルからテクスチャを描画

        Args:
            filepath: PNG ファイルのパス
            x, y: 左上座標
            width, height: 描画サイズ（None の場合は元画像サイズ）
            alpha: 透明度

        Returns:
            描画成功したかどうか
        """
        result = cls.load_texture(filepath)
        if result is None:
            return False

        texture, img_w, img_h = result
        draw_w = width if width is not None else img_w
        draw_h = height if height is not None else img_h

        cls.draw_texture(texture, x, y, draw_w, draw_h, alpha)
        return True

    @classmethod
    def draw_custom_icon(cls, icon_name: str,
                         x: float, y: float,
                         size: Optional[float] = None,
                         alpha: float = 1.0) -> bool:
        """
        PME カスタムアイコンを描画

        Args:
            icon_name: PME アイコン名（拡張子なし）
            x, y: 左上座標
            size: 描画サイズ（正方形、None の場合は UI スケールを適用）
            alpha: 透明度

        Returns:
            描画成功したかどうか
        """
        if size is None:
            size = cls.get_scaled_icon_size()
        filepath = cls.find_custom_icon_path(icon_name)
        if not filepath:
            return False
        return cls.draw_texture_file(filepath, x, y, size, size, alpha)

    @classmethod
    def find_custom_icon_path(cls, icon_name: str) -> Optional[str]:
        """PME カスタムアイコンのパスを探す"""
        # パスキャッシュをチェック
        if icon_name in cls._icon_path_cache:
            return cls._icon_path_cache[icon_name]

        # PME の PreviewsHelper からパスを探す
        try:
            from ...infra.io import get_user_icons_dir, get_system_icons_dir
            import os

            # ユーザーアイコンを優先
            user_dir = get_user_icons_dir()
            user_path = os.path.join(user_dir, f"{icon_name}.png")
            if os.path.exists(user_path):
                cls._icon_path_cache[icon_name] = user_path
                return user_path

            # システムアイコンをチェック
            addon_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            system_dir = get_system_icons_dir(addon_root)
            system_path = os.path.join(system_dir, f"{icon_name}.png")
            if os.path.exists(system_path):
                cls._icon_path_cache[icon_name] = system_path
                return system_path

        except Exception as e:
            print(f"IconDrawing: Failed to find custom icon '{icon_name}': {e}")

        return None

    @classmethod
    def clear_cache(cls) -> None:
        """テクスチャキャッシュをクリア"""
        cls._texture_cache.clear()
        cls._icon_path_cache.clear()

    @classmethod
    def draw_icon(cls, x: float, y: float, icon: str,
                  alpha: float = 1.0, scale: float = 1.0) -> bool:
        """
        アイコンを描画

        まず PME カスタムアイコンを試み、なければ何もしない。
        Blender 内蔵アイコンは GPU では描画できないため、
        UILayout を使用するか、カスタムアイコンで代替する必要がある。

        Args:
            icon: アイコン名（PME カスタムアイコン名 or Blender アイコン名）
            x, y: 左上座標
            alpha: 透明度
            scale: サイズスケール（UI スケールに加えて追加で適用）

        Returns:
            描画成功したかどうか
        """
        # UI スケールを適用した基準サイズに、追加スケールを乗算
        size = cls.get_scaled_icon_size() * scale

        # PME カスタムアイコンを試す
        if cls.draw_custom_icon(icon, x, y, size, alpha):
            return True

        # Blender 内蔵アイコンは GPU で描画できない
        # フォールバック: 何もしない（呼び出し側でテキストを表示するなど）
        return False
