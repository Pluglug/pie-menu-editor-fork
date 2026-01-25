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
# 描画品質設定（アンチエイリアス的な滑らかさ）
# ═══════════════════════════════════════════════════════════════════════════════

# 角丸のセグメント数 [推奨: 8-24, 高品質: 16]
CORNER_SEGMENTS: int = 16

# 円のセグメント数 [推奨: 16-32, 高品質: 32]
CIRCLE_SEGMENTS: int = 32

# シャドウ用セグメント数（角丸コーナー）
SHADOW_CORNER_SEGMENTS: int = 8


# ═══════════════════════════════════════════════════════════════════════════════
# Shadow Shader - Blender 準拠シャドウ描画
# ═══════════════════════════════════════════════════════════════════════════════

# スムースシャドウを使用するかどうか（フォールバック用フラグ）
USE_SMOOTH_SHADOW: bool = True


class ShadowShader:
    """
    Blender 準拠のシャドウ描画

    SMOOTH_COLOR 組み込みシェーダーを使用して、ピクセル単位の滑らかなグラデーションを実現。
    各頂点に色（alpha 値）を設定し、GPU が自動的に補間。

    減衰曲線（Blender 準拠）:
        alpha * (falloff² × 0.722 + falloff × 0.277)
        - falloff = 1.0（内側）: alpha
        - falloff = 0.0（外側）: 0（透明）

    Reference:
        - blender/source/blender/gpu/shaders/gpu_shader_2D_widget_shadow_*.glsl
        - blender/source/blender/editors/interface/interface_draw.cc:ui_draw_dropshadow()
    """

    _shader: gpu.types.GPUShader | None = None

    @classmethod
    def get_shader(cls) -> gpu.types.GPUShader:
        """
        SMOOTH_COLOR シェーダーを取得（キャッシュ）

        Returns:
            GPUShader（組み込みシェーダーなので常に成功）
        """
        if cls._shader is None:
            cls._shader = gpu.shader.from_builtin('SMOOTH_COLOR')
        return cls._shader

    @staticmethod
    def calc_shadow_alpha(falloff: float, base_alpha: float) -> float:
        """
        Blender の減衰曲線で alpha を計算

        Args:
            falloff: 0.0（外側、透明）〜 1.0（内側、影の色）
            base_alpha: 基本 alpha 値

        Returns:
            計算された alpha 値

        調整ガイド:
            - 影を濃くする: 係数を大きくする or base_alpha を増やす
            - 影を薄くする: 係数を小さくする or base_alpha を減らす
            - グラデーションを急に: falloff² の係数を増やす
            - グラデーションを緩やかに: falloff の係数を増やす
        """
        # ═══════════════════════════════════════════════════════════════════════
        # 【調整可能】減衰曲線の係数
        # Blender 標準: falloff² × 0.722 + falloff × 0.277
        # 合計が 1.0 になるように調整すると falloff=1.0 で base_alpha になる
        # ═══════════════════════════════════════════════════════════════════════
        QUADRATIC_COEFF = 0.722  # 二次係数（大きいほど内側が急に濃くなる）
        LINEAR_COEFF = 0.277    # 一次係数（大きいほど外側まで影が広がる）

        return base_alpha * (falloff * falloff * QUADRATIC_COEFF + falloff * LINEAR_COEFF)


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
    def draw_triangle(cls, x1: float, y1: float, x2: float, y2: float,
                      x3: float, y3: float,
                      color: tuple[float, float, float, float]) -> None:
        """三角形を描画"""
        shader = cls.get_shader()
        vertices = ((x1, y1), (x2, y2), (x3, y3))
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices})
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
        segments = CORNER_SEGMENTS

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
                                                   segments: int = CORNER_SEGMENTS) -> list[tuple[float, float]]:
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
        segments = CORNER_SEGMENTS  # 固定セグメント数で滑らかな角丸

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

        segments = CORNER_SEGMENTS  # 固定セグメント数で滑らかな角丸

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
                    segments: int = CIRCLE_SEGMENTS) -> None:
        """
        塗りつぶし円を描画

        Args:
            cx, cy: 中心座標
            radius: 半径
            color: 色 (RGBA)
            segments: 分割数（滑らかさ、デフォルト: CIRCLE_SEGMENTS）
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
                          width: float = 0.0, segments: int = CIRCLE_SEGMENTS) -> None:
        """
        先端が丸い線を描画

        GPU の線描画は先端が平らなので、両端に円を追加して丸みを表現。

        Args:
            x1, y1: 始点
            x2, y2: 終点
            color: 色 (RGBA)
            width: ライン太さ（0.0 の場合は system.ui_line_width を使用）
            segments: 円の分割数（デフォルト: CIRCLE_SEGMENTS）
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

    @classmethod
    def draw_panel_shadow(cls, x: float, y: float, width: float, height: float,
                          radius: int, shadow_width: int, alpha: float) -> None:
        """
        Blender スタイルのパネルシャドウ（3辺: 左、下、右）

        Blender の ui_draw_dropshadow() に準拠した影描画。
        上辺には影を描画せず、左・下・右の3辺に影を表示する。

        Args:
            x, y: パネル左上座標
            width, height: パネルサイズ
            radius: パネル角丸半径
            shadow_width: 影の幅（テーマの menu_shadow_width）
            alpha: 影の透明度（テーマの menu_shadow_fac）

        Implementation:
            SMOOTH_COLOR シェーダーを使用してピクセル単位の滑らかなグラデーションを実現。
            フラグで無効化された場合は、レイヤー方式にフォールバック。
        """
        if shadow_width <= 0 or alpha <= 0:
            return

        # スムースシャドウを使用
        if USE_SMOOTH_SHADOW:
            cls._draw_panel_shadow_smooth(x, y, width, height, radius, shadow_width, alpha)
            return

        # フォールバック: レイヤー方式
        cls._draw_panel_shadow_layered(x, y, width, height, radius, shadow_width, alpha)

    @classmethod
    def _draw_panel_shadow_smooth(cls, x: float, y: float, width: float, height: float,
                                   radius: int, shadow_width: int, alpha: float) -> None:
        """
        SMOOTH_COLOR シェーダーを使用してパネルシャドウを描画

        TRI_STRIP メッシュで外側（透明）と内側（影の色）の頂点を交互に配置し、
        GPU が自動的に補間してピクセル単位の滑らかなグラデーションを生成。

        Blender の GPU_SHADER_2D_WIDGET_SHADOW と同等の品質を実現。
        """
        shader = ShadowShader.get_shader()
        positions, colors = cls._generate_shadow_mesh(
            x, y, width, height, radius, shadow_width, alpha
        )

        batch = batch_for_shader(
            shader, 'TRI_STRIP',
            {"pos": positions, "color": colors}
        )

        shader.bind()
        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def _generate_shadow_mesh(cls, x: float, y: float, width: float, height: float,
                               radius: int, shadow_width: int, alpha: float
                               ) -> tuple[list[tuple[float, float]], list[tuple[float, float, float, float]]]:
        """
        影用の TRI_STRIP メッシュ頂点を生成

        外側頂点（透明）と内側頂点（影の色）を交互に配置。
        GPU が自動的に補間して滑らかなグラデーションを生成する。

        3辺シャドウ（上辺なし）:
        - 左、下、右の3辺は shadow_width だけ外側に拡張
        - 上辺は拡張しない（上辺の外側頂点は内側と同じ位置）

        Returns:
            (positions, colors): 頂点座標と頂点色のタプル
        """
        positions: list[tuple[float, float]] = []
        colors: list[tuple[float, float, float, float]] = []

        # 外側頂点の色（透明）
        outer_color = (0.0, 0.0, 0.0, 0.0)
        # 内側頂点の色（Blender の減衰曲線で alpha 計算、falloff=1.0）
        inner_alpha = ShadowShader.calc_shadow_alpha(1.0, alpha)
        inner_color = (0.0, 0.0, 0.0, inner_alpha)

        # 角丸半径を制限
        r = min(radius, int(height / 2), int(width / 2))
        r = max(0, r)

        # 外側半径（影の外縁）
        outer_r = r + shadow_width
        # セグメント数
        segments = SHADOW_CORNER_SEGMENTS

        # パネル境界（内側）
        inner_left = x
        inner_right = x + width
        inner_top = y
        inner_bottom = y - height

        # 影境界（外側）- 上辺は拡張しない
        outer_left = x - shadow_width
        outer_right = x + width + shadow_width
        outer_top = y  # 上辺は拡張しない
        outer_bottom = y - height - shadow_width

        def add_vertex_pair(outer_pos: tuple[float, float],
                           inner_pos: tuple[float, float],
                           outer_col: tuple[float, float, float, float] = None,
                           inner_col: tuple[float, float, float, float] = None) -> None:
            """外側と内側の頂点ペアを追加"""
            positions.append(outer_pos)
            colors.append(outer_col if outer_col else outer_color)
            positions.append(inner_pos)
            colors.append(inner_col if inner_col else inner_color)

        # ═══════════════════════════════════════════════════════════════════════
        # 頂点生成順序: 左上 → 左 → 左下 → 下 → 右下 → 右 → 右上
        # ═══════════════════════════════════════════════════════════════════════

        # --- 左上（上辺は影なし → 外側頂点は内側と同じ位置） ---
        if r > 0:
            # 角丸コーナーの頂点
            cx_inner = inner_left + r
            cy_inner = inner_top - r
            for j in range(segments + 1):
                # 角度: 90° → 180°
                angle = pi / 2 * (1 + j / segments)
                # 内側頂点（パネル境界）
                inner_x = cx_inner + r * cos(angle)
                inner_y = cy_inner + r * sin(angle)

                # 外側頂点: 上辺に近い部分は影なし（外側=内側）
                # j=0 で angle=90°（上向き）、j=segments で angle=180°（左向き）
                # 上向き（j=0）は影なし、左向き（j=segments）は影あり
                shadow_factor = j / segments  # 0→1 で影の強さを変化
                outer_expand = shadow_width * shadow_factor
                outer_x = cx_inner + (r + outer_expand) * cos(angle) - outer_expand * (1 - shadow_factor)
                outer_y = cy_inner + (r + outer_expand) * sin(angle)

                # よりシンプルな計算: 外側座標を直接計算
                outer_x = inner_x - shadow_factor * shadow_width
                outer_y = inner_y  # 上部は影なし

                add_vertex_pair((outer_x, outer_y), (inner_x, inner_y))
        else:
            # 角丸なし: 左上の点
            add_vertex_pair((inner_left, inner_top), (inner_left, inner_top))

        # --- 左辺（フル影） ---
        # 左辺の中間点（必要に応じて）
        if r > 0:
            # 左上コーナーから左下コーナーへの直線部分
            add_vertex_pair(
                (outer_left, inner_top - r),
                (inner_left, inner_top - r)
            )
            add_vertex_pair(
                (outer_left, inner_bottom + r),
                (inner_left, inner_bottom + r)
            )
        else:
            add_vertex_pair(
                (outer_left, inner_top),
                (inner_left, inner_top)
            )
            add_vertex_pair(
                (outer_left, inner_bottom),
                (inner_left, inner_bottom)
            )

        # --- 左下コーナー（フル影） ---
        if r > 0:
            cx_inner = inner_left + r
            cy_inner = inner_bottom + r
            cx_outer = outer_left + outer_r
            cy_outer = outer_bottom + outer_r
            for j in range(segments + 1):
                # 角度: 180° → 270°
                angle = pi * (1 + 0.5 * j / segments)
                inner_x = cx_inner + r * cos(angle)
                inner_y = cy_inner + r * sin(angle)
                outer_x = cx_outer + outer_r * cos(angle)
                outer_y = cy_outer + outer_r * sin(angle)
                add_vertex_pair((outer_x, outer_y), (inner_x, inner_y))
        else:
            add_vertex_pair((outer_left, outer_bottom), (inner_left, inner_bottom))

        # --- 下辺（フル影） ---
        if r > 0:
            add_vertex_pair(
                (outer_left + outer_r, outer_bottom),
                (inner_left + r, inner_bottom)
            )
            add_vertex_pair(
                (outer_right - outer_r, outer_bottom),
                (inner_right - r, inner_bottom)
            )
        else:
            add_vertex_pair(
                (outer_left, outer_bottom),
                (inner_left, inner_bottom)
            )
            add_vertex_pair(
                (outer_right, outer_bottom),
                (inner_right, inner_bottom)
            )

        # --- 右下コーナー（フル影） ---
        if r > 0:
            cx_inner = inner_right - r
            cy_inner = inner_bottom + r
            cx_outer = outer_right - outer_r
            cy_outer = outer_bottom + outer_r
            for j in range(segments + 1):
                # 角度: 270° → 360°
                angle = pi * (1.5 + 0.5 * j / segments)
                inner_x = cx_inner + r * cos(angle)
                inner_y = cy_inner + r * sin(angle)
                outer_x = cx_outer + outer_r * cos(angle)
                outer_y = cy_outer + outer_r * sin(angle)
                add_vertex_pair((outer_x, outer_y), (inner_x, inner_y))
        else:
            add_vertex_pair((outer_right, outer_bottom), (inner_right, inner_bottom))

        # --- 右辺（フル影） ---
        if r > 0:
            add_vertex_pair(
                (outer_right, inner_bottom + r),
                (inner_right, inner_bottom + r)
            )
            add_vertex_pair(
                (outer_right, inner_top - r),
                (inner_right, inner_top - r)
            )
        else:
            add_vertex_pair(
                (outer_right, inner_bottom),
                (inner_right, inner_bottom)
            )
            add_vertex_pair(
                (outer_right, inner_top),
                (inner_right, inner_top)
            )

        # --- 右上（上辺は影なし → 外側頂点は内側と同じ位置） ---
        if r > 0:
            cx_inner = inner_right - r
            cy_inner = inner_top - r
            for j in range(segments + 1):
                # 角度: 0° → 90°
                angle = pi / 2 * j / segments
                inner_x = cx_inner + r * cos(angle)
                inner_y = cy_inner + r * sin(angle)

                # 右向き（j=0）は影あり、上向き（j=segments）は影なし
                shadow_factor = 1 - j / segments  # 1→0 で影の強さを変化
                outer_x = inner_x + shadow_factor * shadow_width
                outer_y = inner_y  # 上部は影なし

                add_vertex_pair((outer_x, outer_y), (inner_x, inner_y))
        else:
            add_vertex_pair((inner_right, inner_top), (inner_right, inner_top))

        return positions, colors

    @classmethod
    def _draw_panel_shadow_layered(cls, x: float, y: float, width: float, height: float,
                                    radius: int, shadow_width: int, alpha: float) -> None:
        """
        レイヤー方式でパネルシャドウを描画（フォールバック）

        複数の半透明レイヤーを重ねてグラデーションを近似。
        シェーダーが使えない環境向けのフォールバック実装。

        Note:
            最大6レイヤーに制限されるため、shadow_width が大きい場合は
            バンディング（段階）が目立つ可能性がある。
        """
        # 複数レイヤーでグラデーションを近似
        layers = min(shadow_width, 6)  # 最大6レイヤー

        for i in range(layers, 0, -1):
            # 外側のレイヤーほど大きく、透明に
            # falloff: 1.0（内側）→ 0.0（外側）
            falloff = 1.0 - (i - 1) / layers
            expand = i * (shadow_width / layers)

            # Blender の減衰曲線を近似: falloff² * 0.722 + falloff * 0.277
            layer_alpha = alpha * (falloff * falloff * 0.722 + falloff * 0.277)

            # 影の矩形（上辺は拡張しない、左・下・右のみ）
            shadow_x = x - expand           # 左に拡張
            shadow_y = y                    # 上辺は拡張しない
            shadow_w = width + expand * 2   # 左右に拡張
            shadow_h = height + expand      # 下に拡張

            layer_color = (0.0, 0.0, 0.0, layer_alpha)
            cls.draw_rounded_rect(
                shadow_x, shadow_y,
                shadow_w, shadow_h,
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
    def truncate_text(cls, text: str, size: int, max_width: float,
                      ellipsis: str = "...", font_id: int = FONT_ID) -> str:
        """
        テキストを指定幅に収まるよう省略

        Args:
            text: 元のテキスト
            size: フォントサイズ
            max_width: 最大幅（ピクセル）
            ellipsis: 省略記号（デフォルト: "..."）
            font_id: フォントID

        Returns:
            省略されたテキスト（収まる場合は元のまま）
        """
        blf.size(font_id, size)
        width, _ = blf.dimensions(font_id, text)

        if width <= max_width:
            return text

        # 省略記号の幅を取得
        ellipsis_width, _ = blf.dimensions(font_id, ellipsis)
        target_width = max_width - ellipsis_width

        if target_width <= 0:
            return ellipsis

        # 二分探索で適切な長さを見つける
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            test_text = text[:mid]
            w, _ = blf.dimensions(font_id, test_text)
            if w <= target_width:
                low = mid
            else:
                high = mid - 1

        return text[:low] + ellipsis if low < len(text) else text

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
    - フォールバックアイコン対応（PNG がない場合に代替表示）

    使用例:
        # PNG ファイルから直接描画
        IconDrawing.draw_texture_file("/path/to/icon.png", x, y, 20, 20)

        # PME カスタムアイコン名で描画（PreviewsHelper 経由）
        IconDrawing.draw_custom_icon("my_icon", x, y)

        # Blender アイコン名で描画（PNG があれば使用、なければフォールバック）
        IconDrawing.draw_icon(x, y, "RESTRICT_VIEW_OFF")
    """

    # アイコンサイズ（Blender 標準、基準値）
    ICON_SIZE = 20

    # フォールバックアイコン（PNG が見つからない場合に使用）
    FALLBACK_ICON = "roaoao"

    # Blender アイコン名 → PNG ファイル名のマッピング
    # 将来的にここに頻出アイコンを追加していく
    _icon_name_map: dict[str, str] = {
        # 例: "RESTRICT_VIEW_OFF": "hide_viewport",
        # 例: "RESTRICT_RENDER_OFF": "hide_render",
    }

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
            import hashlib
            if not os.path.exists(filepath):
                return None

            # Blender Image としてロード
            # フルパスのハッシュを使用して一意の名前を生成（同名ファイル衝突防止）
            path_hash = hashlib.md5(filepath.encode()).hexdigest()[:8]
            basename = os.path.basename(filepath)
            img_name = f"_gpu_icon_{path_hash}_{basename}"

            if img_name in bpy.data.images:
                img = bpy.data.images[img_name]
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
                  alpha: float = 1.0, scale: float = 1.0,
                  use_fallback: bool = True) -> bool:
        """
        アイコンを描画（フォールバック対応）

        以下の順序でアイコンを探し、最初に見つかったものを描画:
        1. 指定されたアイコン名でカスタム PNG を探す
        2. マッピングされた名前でカスタム PNG を探す
        3. フォールバックアイコン（roaoao.png）を表示

        Args:
            x, y: 左上座標
            icon: アイコン名（PME カスタムアイコン名 or Blender アイコン名）
            alpha: 透明度
            scale: サイズスケール（UI スケールに加えて追加で適用）
            use_fallback: PNG が見つからない場合にフォールバックを使用するか

        Returns:
            描画成功したかどうか（フォールバック使用時も True）
        """
        if not icon or icon == "NONE":
            return False

        # UI スケールを適用した基準サイズに、追加スケールを乗算
        size = cls.get_scaled_icon_size() * scale

        # 1. 指定されたアイコン名でカスタム PNG を試す
        if cls.draw_custom_icon(icon, x, y, size, alpha):
            return True

        # 2. マッピングされた名前で試す（Blender アイコン名 → PNG 名）
        mapped_name = cls._icon_name_map.get(icon)
        if mapped_name and cls.draw_custom_icon(mapped_name, x, y, size, alpha):
            return True

        # 3. フォールバックアイコンを表示
        if use_fallback:
            return cls.draw_custom_icon(cls.FALLBACK_ICON, x, y, size, alpha)

        return False
