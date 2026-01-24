# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Measure/Arrange
"""

from __future__ import annotations

from typing import Optional

from ..style import Direction, Alignment, Size, BoxConstraints
from ..items import LayoutItem


class LayoutFlowMixin:
    """Mixin methods."""


    def calc_height(self) -> float:
        """
        合計高さを計算

        Note:
            Phase 1 では measure() で self.height が計算されるため、
            layout() 実行後はそちらの値が使用される。
            このメソッドは measure() 前の互換性のために残置。
        """
        # P1-5 修正: measure() 実行後かつ dirty でなければ計算済みの height を返す
        # dirty=True の場合は再計算が必要（アイテム追加・変更後）
        if self.height > 0 and not self._dirty:
            return self.height

        if not self._elements:
            _, padding_y = self._get_padding()
            return padding_y * 2

        spacing = self._get_spacing()
        if self.direction == Direction.VERTICAL:
            _, padding_y = self._get_padding()
            height = padding_y * 2
            n_elements = 0
            for element in self._elements:
                if isinstance(element, GPULayout):
                    height += element.calc_height()
                else:
                    _, h = element.calc_size(self.style)
                    height += h * self.scale_y
                n_elements += 1
            # スペーシング
            if n_elements > 1:
                height += spacing * (n_elements - 1)
            return height
        else:
            # 水平レイアウト - 最大の高さ
            max_height = 0
            for element in self._elements:
                if isinstance(element, GPULayout):
                    max_height = max(max_height, element.calc_height())
                else:
                    _, h = element.calc_size(self.style)
                    max_height = max(max_height, h * self.scale_y)
            _, padding_y = self._get_padding()
            return max_height + padding_y * 2


    def calc_width(self) -> float:
        """
        合計幅を計算

        Note:
            Phase 1 では measure() で self.width が計算される。
            このメソッドは水平レイアウトの自然幅計算に使用。
        """
        if not self._elements:
            return self.width

        spacing = self._get_spacing()
        if self.direction == Direction.HORIZONTAL:
            padding_x, _ = self._get_padding()
            width = padding_x * 2
            n_elements = 0
            for element in self._elements:
                if isinstance(element, GPULayout):
                    width += element.calc_width()
                else:
                    w, _ = element.calc_size(self.style)
                    width += w * self.scale_x
                n_elements += 1
            # スペーシング
            if n_elements > 1:
                width += spacing * (n_elements - 1)
            return width
        else:
            return self.width

    # ─────────────────────────────────────────────────────────────────────────
    # タイトルバー設定
    # ─────────────────────────────────────────────────────────────────────────


    def measure(self, constraints: BoxConstraints) -> Size:
        """
        Pass 1: サイズを推定（子から親へ積み上げ）

        Args:
            constraints: 親から渡されるサイズ制約

        Returns:
            このレイアウトの推定サイズ

        Note:
            この段階では位置（x, y）は確定しません。
            サイズのみを計算し、self.width / self.height に保存します。
        """
        if self._is_column_flow:
            return self._measure_column_flow(constraints)
        elif self.direction == Direction.VERTICAL:
            return self._measure_vertical(constraints)
        else:
            return self._measure_horizontal(constraints)


    def _measure_vertical(self, constraints: BoxConstraints) -> Size:
        """
        垂直レイアウトのサイズ推定（v3 準拠）

        Changes (P1-3):
            - 子要素の size に scale_x/y を measure で適用
            - 自然サイズを estimated_* に保存
        """
        spacing = self._get_spacing()
        padding_x, padding_y = self._get_padding()
        # NOTE: Blender UILayout alignment is horizontal-only; vertical layouts keep natural widths.
        # パディングを差し引いた内部制約
        inner_constraints = constraints.deflate(padding_x * 2, padding_y * 2)
        available_width = inner_constraints.max_width
        if available_width == float('inf'):
            available_width = self.width - padding_x * 2
        available_width = max(0, available_width)

        total_height = padding_y * 2
        max_width = 0.0
        n_elements = 0

        for element in self._elements:
            if isinstance(element, GPULayout):
                # 子レイアウトは再帰的に measure
                child_constraints = BoxConstraints(
                    min_width=inner_constraints.min_width,
                    max_width=inner_constraints.max_width,
                    min_height=0,
                    max_height=float('inf')
                )
                size = element.measure(child_constraints)
                element.sizing.estimated_width = size.width
                element.estimated_height = size.height
            else:
                # LayoutItem は calc_size で自然サイズを取得
                w, h = element.calc_size(self.style)
                element.sizing.estimated_width = w
                element.estimated_height = h
                if type(element).calc_size_for_width is not LayoutItem.calc_size_for_width:
                    _, height = element.calc_size_for_width(self.style, available_width)
                    element.estimated_height = height

            element.sizing.estimated_width *= self.scale_x
            element.estimated_height *= self.scale_y

            max_width = max(max_width, element.sizing.estimated_width)
            total_height += element.estimated_height
            n_elements += 1

        # スペーシングを加算
        if n_elements > 1:
            total_height += spacing * (n_elements - 1)

        # 自身の推定サイズを記録
        self.sizing.estimated_width = max_width + padding_x * 2
        self.estimated_height = total_height

        self._apply_ui_units_x()

        # 制約に従ってクランプ
        self.width = constraints.clamp_width(self.sizing.estimated_width)
        self.height = constraints.clamp_height(self.estimated_height)

        return Size(self.width, self.height)


    def _measure_horizontal(self, constraints: BoxConstraints) -> Size:
        """
        水平レイアウトのサイズ推定（v3 準拠）

        各子の自然サイズを取得し、estimated_width/height に保存。
        arrange フェーズで _distribute_width() を使って実際の幅を配分。

        Changes (P1-1, P1-3, P1-4):
            - 均等分配 → 自然幅を取得して estimated_width に保存
            - 子要素の size に scale_x/y を measure で適用
            - constraints.clamp_height() を適用
        """
        n = len(self._elements)
        if n == 0:
            padding_x, padding_y = self._get_padding()
            self.sizing.estimated_width = padding_x * 2
            self.estimated_height = padding_y * 2
            self._apply_ui_units_x()
            self.width = constraints.clamp_width(self.sizing.estimated_width)
            self.height = constraints.clamp_height(self.estimated_height)
            return Size(self.width, self.height)

        spacing = self._get_spacing()
        padding_x, padding_y = self._get_padding()
        unit_x = float(self.style.scaled_item_height())
        expand_default_width = unit_x * 10.0
        use_fixed_expand_width = (self.alignment == Alignment.EXPAND)

        # 利用可能な幅を計算（制約の max_width を使用）
        # 負の幅を防ぐため max(0, ...) でクランプ
        available_width = constraints.max_width - padding_x * 2
        if available_width == float('inf'):
            # 制約がない場合は現在の width を使用
            available_width = self.width - padding_x * 2
        available_width = max(0, available_width)

        total_estimated_width = 0.0
        max_height = 0.0
        self._measured_widths = []
        self._measured_gap = spacing

        for element in self._elements:
            if isinstance(element, GPULayout):
                # 子レイアウトは loose constraints で measure（自然サイズを取得）
                child_constraints = BoxConstraints(
                    min_width=0,
                    max_width=max(0, available_width),  # 最大幅は親から継承、負にならないようクランプ
                    min_height=0,
                    max_height=float('inf')
                )
                size = element.measure(child_constraints)
                element.sizing.estimated_width = size.width
                if use_fixed_expand_width and not element.sizing.is_fixed:
                    element.sizing.estimated_width = expand_default_width
                element.estimated_height = size.height
            else:
                # LayoutItem は calc_size で自然サイズを取得
                w, h = element.calc_size(self.style)
                if use_fixed_expand_width and not element.sizing.is_fixed:
                    w = expand_default_width
                element.sizing.estimated_width = w
                element.estimated_height = h

            element.sizing.estimated_width *= self.scale_x
            element.estimated_height *= self.scale_y

            total_estimated_width += element.sizing.estimated_width
            max_height = max(max_height, element.estimated_height)

        # 自身の推定サイズを記録
        total_spacing = spacing * (n - 1)
        self.sizing.estimated_width = total_estimated_width + total_spacing + padding_x * 2
        self.estimated_height = max_height + padding_y * 2

        self._apply_ui_units_x()

        # 制約でクランプ（P1-4 修正: height も制約でクランプ）
        if self.sizing.is_fixed:
            self.width = constraints.clamp_width(self.sizing.estimated_width)
        else:
            self.width = constraints.clamp_width(available_width + padding_x * 2)

        # P1-1: 幅確定後に高さを再計測（幅依存の高さを反映）
        fit_width = max(0, self.width - padding_x * 2)
        if self._is_split and n > 0:
            widths = self._distribute_split_widths(n, fit_width, spacing)
            actual_gap = spacing
        else:
            widths, actual_gap = self._distribute_width(self._elements, fit_width, spacing)
        self._measured_widths = widths
        self._measured_gap = actual_gap

        needs_height_pass = any(
            isinstance(element, GPULayout) or
            type(element).calc_size_for_width is not LayoutItem.calc_size_for_width
            for element in self._elements
        )
        if needs_height_pass and widths:
            max_height = 0.0
            for element, width in zip(self._elements, widths):
                if isinstance(element, GPULayout):
                    child_constraints = BoxConstraints(
                        min_width=width,
                        max_width=width,
                        min_height=0,
                        max_height=float('inf')
                    )
                    size = element.measure(child_constraints)
                    element.sizing.estimated_width = size.width
                    element.estimated_height = size.height
                else:
                    _, height = element.calc_size_for_width(self.style, width)
                    element.estimated_height = height

                element.estimated_height *= self.scale_y
                max_height = max(max_height, element.estimated_height)

            self.estimated_height = max_height + padding_y * 2

        self.height = constraints.clamp_height(self.estimated_height)

        return Size(self.width, self.height)


    def _distribute_width(
        self,
        elements: list,
        available_width: float,
        gap: float,
    ) -> tuple[list[float], float]:
        """
        Row の幅配分（v3 / Blender UILayout 準拠）

        Args:
            elements: 配分対象の要素リスト（LayoutItem または GPULayout）
            available_width: 利用可能な幅（ギャップ含む）
            gap: 要素間のギャップ

        Returns:
            (各要素に割り当てる幅のリスト, 実際のギャップ)

        Note:
            - 縮小が必要な場合: 比例縮小、ギャップは固定
            - EXPAND:
              - expand_width=True の要素: 比例拡大
              - expand_width=False の要素: 自然幅を維持
              - 余白は間隔に均等分配
            - LEFT/CENTER/RIGHT: 元サイズ維持、ギャップは固定
        """
        n = len(elements)
        if n == 0:
            return [], gap

        gaps_total = gap * (n - 1)
        # 負の幅を防ぐため max(0, ...) でクランプ
        available = max(0, available_width - gaps_total)
        total_estimated = sum(e.sizing.estimated_width for e in elements)

        if total_estimated == 0:
            # フォールバック: 均等分配（available が 0 の場合も安全）
            if available > 0 and n > 0:
                return [available / n] * n, gap
            return [0] * n, gap

        result = []
        actual_gap = gap

        if total_estimated > available:
            # 比例縮小（コンテンツがはみ出す）
            sizes = [element.sizing.estimated_width for element in elements]
            result = self._fit_widths(sizes, available, self.alignment)
        elif self.alignment == Alignment.EXPAND:
            # EXPAND: 要素タイプに応じて幅を決定
            # - expand_width=True (ボタン等): 比例拡大
            # - expand_width=False (ラベル等): 自然幅を維持、余白は間隔に分配

            # 拡張可能な要素と固定幅要素を分離
            expandable_width = sum(
                e.sizing.estimated_width for e in elements
                if getattr(e, 'expand_width', True) and not e.sizing.is_fixed
            )
            fixed_width = sum(
                e.sizing.estimated_width for e in elements
                if e.sizing.is_fixed or not getattr(e, 'expand_width', True)
            )

            # 拡張可能な要素に分配する幅
            expand_available = available - fixed_width

            if expandable_width > 0 and expand_available > 0:
                # 拡張可能な要素がある場合: 比例拡大
                expandable_indices = [
                    i for i, element in enumerate(elements)
                    if getattr(element, 'expand_width', True) and not element.sizing.is_fixed
                ]
                expandable_set = set(expandable_indices)
                expandable_sizes = [elements[i].sizing.estimated_width for i in expandable_indices]
                fitted = self._fit_widths(expandable_sizes, expand_available, Alignment.EXPAND)
                fitted_iter = iter(fitted)
                for i, element in enumerate(elements):
                    if i in expandable_set:
                        width = next(fitted_iter)
                    else:
                        width = element.sizing.estimated_width
                    result.append(width)
            else:
                # 全て固定幅要素の場合: 間隔を均等分配
                extra_space = available - total_estimated
                if n > 1 and extra_space > 0:
                    actual_gap = gap + extra_space / (n - 1)
                for element in elements:
                    result.append(element.sizing.estimated_width)
        else:
            # LEFT/CENTER/RIGHT: 元サイズ維持
            for element in elements:
                result.append(element.sizing.estimated_width)

        return result, actual_gap


    def _fit_widths(self, sizes: list[float], available: float,
                    alignment: Alignment) -> list[float]:
        """
        Fit widths to available space with Blender-like rounding.

        Mirrors ui_item_fit() behavior: distribute rounding remainder across items,
        give the last item the leftover pixels.
        """
        if not sizes:
            return []
        total = sum(sizes)
        if total <= 0 or available <= 0:
            return [0.0] * len(sizes)
        if total <= available and alignment != Alignment.EXPAND:
            return list(sizes)

        result = []
        pos = 0.0
        extra_pixel = 0.0
        for idx, item in enumerate(sizes):
            is_last = idx == len(sizes) - 1
            if is_last:
                width = max(0.0, available - pos)
            else:
                width = extra_pixel + (item * available) / total
                extra_pixel = width - int(width)
                width = float(int(width))
            result.append(width)
            pos += width
        return result


    def _distribute_split_widths(
        self,
        n: int,
        available_width: float,
        gap: float
    ) -> list[float]:
        """
        Split レイアウト専用の幅配分（v3 アルゴリズム）

        Args:
            n: 列の総数（arrange 時点で確定）
            available_width: 利用可能な幅
            gap: 列間のギャップ

        Returns:
            各列に割り当てる幅のリスト

        Note:
            factor > 0 の場合:
            - 最初の列: factor 割合
            - 2番目以降: 残り幅を (n-1) で均等分割
            例: factor=0.25 で 3列 → 25% : 37.5% : 37.5%

            factor == 0 の場合:
            - 全列を均等分割
        """
        if n == 0:
            return []

        gaps_total = gap * (n - 1)
        content_width = max(0, available_width - gaps_total)

        if self._split_factor > 0:
            # factor が指定されている場合
            first_width = content_width * self._split_factor
            remaining_width = content_width - first_width

            if n == 1:
                # 1列のみ: factor 無視で全幅
                return [content_width]
            else:
                # 2列以上: 最初は factor、残りを均等分割
                other_width = remaining_width / (n - 1)
                return [first_width] + [other_width] * (n - 1)
        else:
            # factor == 0: 全列均等分割
            if n > 0:
                equal_width = content_width / n
                return [equal_width] * n
            return []


    def arrange(self, x: float, y: float) -> None:
        """
        Pass 2: 位置を確定（親から子へ伝播）

        Args:
            x: このレイアウトの左上 X 座標
            y: このレイアウトの左上 Y 座標

        Note:
            measure() で計算されたサイズを基に、
            各要素の最終的な位置を確定します。
        """
        self.x = x
        self.y = y

        if self._is_column_flow:
            self._arrange_column_flow()
        elif self.direction == Direction.VERTICAL:
            self._arrange_vertical()
        else:
            self._arrange_horizontal()


    def _arrange_vertical(self) -> None:
        """
        垂直レイアウトの位置確定（v3 準拠）

        Changes (P1-2, P1-3):
            - measure で適用済みの estimated_* を使用
            - arrange での scale 適用は行わない
        """
        spacing = self._get_spacing()
        padding_x, padding_y = self._get_padding()
        # 負の幅を防ぐため max(0, ...) でクランプ
        available_width = max(0, self.width - padding_x * 2)

        cursor_x = self.x + padding_x
        cursor_y = self.y - padding_y

        n = len(self._elements)
        if n == 0:
            return

        align_flags = None
        if self._align:
            align_flags = [self._element_can_align(element) for element in self._elements]

        for i, element in enumerate(self._elements):
            if isinstance(element, GPULayout):
                # 子レイアウトは親の幅に合わせる
                element.width = available_width
                element.arrange(cursor_x, cursor_y)
                cursor_y -= element.height + spacing
            else:
                # LayoutItem の配置
                # alignment に応じて幅と位置を計算
                if self.alignment == Alignment.EXPAND:
                    # EXPAND: 利用可能幅全体を使用
                    element.width = available_width
                    element.x = cursor_x
                else:
                    # 自然サイズを維持（measure で scale 済みの estimated_width を使用）
                    element.width = element.sizing.estimated_width
                    if self.alignment == Alignment.CENTER:
                        element.x = cursor_x + (available_width - element.width) / 2
                    elif self.alignment == Alignment.RIGHT:
                        element.x = cursor_x + available_width - element.width
                    else:  # LEFT
                        element.x = cursor_x

                element.y = cursor_y
                # P1-3: scale_y 適用済みの estimated_height を使用（二重適用を防ぐ）
                element.height = element.estimated_height

                # LabelItem に alignment を継承
                if hasattr(element, 'alignment'):
                    element.alignment = self.alignment

                # Phase 2: corners 計算（縦方向）
                if hasattr(element, 'corners'):
                    if self._align:
                        if not align_flags or not align_flags[i]:
                            element.corners = (True, True, True, True)
                        else:
                            top = align_flags[i - 1] if i > 0 else False
                            bottom = align_flags[i + 1] if i < n - 1 else False
                            # corners: (bottomLeft, topLeft, topRight, bottomRight)
                            element.corners = (not bottom, not top, not top, not bottom)
                    else:
                        # align=False: デフォルト（全角丸）にリセット
                        element.corners = (True, True, True, True)

                cursor_y -= element.height + spacing


    def _arrange_horizontal(self) -> None:
        """
        水平レイアウトの位置確定（v3 準拠）

        Changes (P1-2, P1-3):
            - _distribute_width() を使用して幅を配分
            - measure で適用済みの estimated_* を使用
            - split レイアウトは専用の配分ロジックを使用
        """
        spacing = self._get_spacing()
        padding_x, padding_y = self._get_padding()

        n = len(self._elements)
        if n == 0:
            return

        align_flags = None
        if self._align:
            align_flags = [self._element_can_align(element) for element in self._elements]

        cursor_y = self.y - padding_y
        available_width = max(0, self.width - padding_x * 2)

        if self._measured_widths and len(self._measured_widths) == n:
            widths = self._measured_widths
            actual_spacing = self._measured_gap
        elif self._is_split and n > 0:
            # Split レイアウトの場合は専用の配分ロジック
            widths = self._distribute_split_widths(n, available_width, spacing)
            actual_spacing = spacing
        else:
            # v3 アルゴリズムで幅配分（EXPAND 時は間隔も調整される）
            widths, actual_spacing = self._distribute_width(self._elements, available_width, spacing)

        # alignment による開始位置計算
        total_content_width = sum(widths) + actual_spacing * max(0, n - 1)
        min_cursor_x = self.x + padding_x

        if self.alignment == Alignment.CENTER:
            cursor_x = self.x + padding_x + (available_width - total_content_width) / 2
            cursor_x = max(cursor_x, min_cursor_x)  # 左外へのはみ出しを防止
        elif self.alignment == Alignment.RIGHT:
            cursor_x = self.x + padding_x + available_width - total_content_width
            cursor_x = max(cursor_x, min_cursor_x)  # 左外へのはみ出しを防止
        else:  # LEFT or EXPAND
            cursor_x = min_cursor_x

        # 各要素の配置
        for i, element in enumerate(self._elements):
            width = widths[i] if i < len(widths) else 0

            if isinstance(element, GPULayout):
                element.width = width
                element.arrange(cursor_x, cursor_y)
            else:
                element.x = cursor_x
                element.y = cursor_y
                element.width = width
                # P1-3: scale_y 適用済みの estimated_height を使用（二重適用を防ぐ）
                element.height = element.estimated_height

                # Phase 2: corners 計算（水平方向）
                if hasattr(element, 'corners'):
                    if self._align:
                        if not align_flags or not align_flags[i]:
                            element.corners = (True, True, True, True)
                        else:
                            left = align_flags[i - 1] if i > 0 else False
                            right = align_flags[i + 1] if i < n - 1 else False
                            # corners: (bottomLeft, topLeft, topRight, bottomRight)
                            element.corners = (not left, not left, not right, not right)
                    else:
                        # align=False: デフォルト（全角丸）にリセット
                        element.corners = (True, True, True, True)

            cursor_x += width + actual_spacing


    def _measure_column_flow(self, constraints: BoxConstraints) -> Size:
        """
        column_flow レイアウトのサイズ推定

        Blender LayoutItemFlow::estimate_impl() に準拠:
        - 全アイテムの最大幅と合計高さを計算
        - 列数を決定（指定 or 自動）
        - 列の高さ閾値 (toth / totcol) で列分配をシミュレート
        """
        spacing = self._get_spacing()
        padding_x, padding_y = self._get_padding()
        available_width = constraints.max_width - padding_x * 2
        if available_width == float('inf'):
            available_width = self.width - padding_x * 2
        available_width = max(0, available_width)

        # Step 1: 全アイテムのサイズを計算
        max_item_width = 0.0
        total_height = 0.0
        item_count = 0

        for element in self._elements:
            if isinstance(element, GPULayout):
                child_constraints = BoxConstraints(
                    min_width=0, max_width=available_width,
                    min_height=0, max_height=float('inf')
                )
                size = element.measure(child_constraints)
                element.sizing.estimated_width = size.width
                element.estimated_height = size.height
            else:
                w, h = element.calc_size(self.style)
                element.sizing.estimated_width = w * self.scale_x
                element.estimated_height = h * self.scale_y

            max_item_width = max(max_item_width, element.sizing.estimated_width)
            total_height += element.estimated_height
            item_count += 1

        if item_count == 0:
            self.sizing.estimated_width = padding_x * 2
            self.estimated_height = padding_y * 2
            self._apply_ui_units_x()
            self.width = constraints.clamp_width(self.sizing.estimated_width)
            self.height = constraints.clamp_height(self.estimated_height)
            return Size(self.width, self.height)

        # Step 2: 列数を決定
        if self._flow_columns > 0:
            self._flow_totcol = self._flow_columns
        else:
            # 自動計算: 利用可能幅 / 最大アイテム幅
            if max_item_width > 0:
                self._flow_totcol = max(1, int(available_width / max_item_width))
                self._flow_totcol = min(self._flow_totcol, item_count)
            else:
                self._flow_totcol = 1

        # Step 3: 列ごとの高さをシミュレート
        col_spacing = self.style.scaled_spacing_x() if not self._align else 0
        item_spacing = spacing

        # 各列の幅と高さを計算
        total_item_height = total_height + item_spacing * (item_count - 1)
        column_height_threshold = total_item_height / self._flow_totcol

        col_heights = [0.0]
        col_widths = [0.0]
        current_col = 0
        emy = 0.0

        for element in self._elements:
            h = element.estimated_height + item_spacing
            w = element.sizing.estimated_width

            emy -= h
            col_heights[current_col] += h
            col_widths[current_col] = max(col_widths[current_col], w)

            # 次の列に移動するかどうか
            if current_col < self._flow_totcol - 1 and emy <= -column_height_threshold:
                current_col += 1
                col_heights.append(0.0)
                col_widths.append(0.0)
                emy = 0.0

        # 最終スペーシングを調整
        for i in range(len(col_heights)):
            if col_heights[i] > item_spacing:
                col_heights[i] -= item_spacing

        # Step 4: 全体サイズを計算
        total_width = sum(col_widths) + col_spacing * (len(col_widths) - 1) + padding_x * 2
        max_height = max(col_heights) if col_heights else 0.0
        total_layout_height = max_height + padding_y * 2

        self.sizing.estimated_width = total_width
        self.estimated_height = total_layout_height

        self._apply_ui_units_x()
        self.width = constraints.clamp_width(available_width + padding_x * 2)
        self.height = constraints.clamp_height(self.estimated_height)

        return Size(self.width, self.height)


    def _arrange_column_flow(self) -> None:
        """
        column_flow レイアウトの位置確定

        Blender LayoutItemFlow::resolve_impl() に準拠:
        - 列幅を均等に計算
        - アイテムを上から下に配置
        - 累積高さが閾値を超えたら次の列へ
        """
        n = len(self._elements)
        if n == 0:
            return

        spacing = self._get_spacing()
        padding_x, padding_y = self._get_padding()
        col_spacing = self.style.scaled_spacing_x() if not self._align else 0
        item_spacing = spacing

        available_width = max(0, self.width - padding_x * 2)

        # 列幅を計算
        col_width = (available_width - col_spacing * (self._flow_totcol - 1)) / self._flow_totcol

        # 合計高さと閾値
        total_height = sum(e.estimated_height + item_spacing for e in self._elements) - item_spacing
        emh = total_height / self._flow_totcol

        # 配置
        cursor_x = self.x + padding_x
        cursor_y = self.y - padding_y
        start_y = cursor_y
        emy = 0.0
        current_col = 0

        for element in self._elements:
            h = element.estimated_height

            # 位置を設定
            element.y = cursor_y
            element.x = cursor_x

            # 幅を設定（EXPAND か自然幅）
            if self.alignment == Alignment.EXPAND:
                element.width = col_width
            else:
                element.width = min(col_width, element.sizing.estimated_width)

            element.height = h

            # 子レイアウトの場合は再帰的に arrange
            if isinstance(element, GPULayout):
                element.arrange(element.x, element.y)

            # カーソル移動
            cursor_y -= h + item_spacing
            emy -= h + item_spacing

            # 次の列に移動するかどうか
            if current_col < self._flow_totcol - 1 and emy <= -emh:
                cursor_x += col_width + col_spacing
                cursor_y = start_y
                emy = 0.0
                current_col += 1

    # ─────────────────────────────────────────────────────────────────────────
    # レイアウト計算（レガシー互換 + 新アルゴリズム統合）
    # ─────────────────────────────────────────────────────────────────────────


    def layout(self, *, force: bool = False, constraints: Optional[BoxConstraints] = None) -> None:
        """
        レイアウトを計算（2-pass: measure → arrange）

        Args:
            force: True の場合、Dirty Flag に関係なく再計算
            constraints: サイズ制約（None の場合は現在の width から生成）

        Note:
            Phase 1 で導入された 2-pass アルゴリズム:
            1. measure(): 子から親へサイズを積み上げ
            2. arrange(): 親から子へ位置を確定
        """
        if not self._dirty and not force:
            return  # 変更がなければスキップ

        # 制約が指定されていない場合は、現在の幅から制約を生成
        if constraints is None:
            constraints = BoxConstraints.tight_width(self.width)

        # Pass 1: サイズ推定
        self.measure(constraints)

        # Pass 2: 位置確定
        self.arrange(self.x, self.y)

        # タイトルバーの HitRect を登録
        self._register_title_bar()
        self._register_resize_handle()

        # HitRect の位置を更新（子レイアウトも含めて再帰的に同期）
        self._update_hit_positions_recursive()

        self._dirty = False  # レイアウト完了


    def _relayout_items(self) -> None:
        """
        アイテムの位置を再計算（Deprecated）

        Warning:
            Phase 1 で arrange() に機能が統合されたため、
            このメソッドは layout() から呼び出されなくなりました。
            外部から呼び出している箇所がある場合のために残置していますが、
            将来のバージョンで削除される可能性があります。
        """
        padding_x, padding_y = self._get_padding()
        cursor_x = self.x + padding_x
        cursor_y = self.y - padding_y
        available_width = self._get_available_width()
        spacing = self._get_spacing()

        for element in self._elements:
            if not isinstance(element, LayoutItem):
                continue
            item = element
            item_width, item_height = item.calc_size(self.style)

            if self.direction == Direction.VERTICAL:
                # alignment に応じて幅と位置を計算
                if self.alignment == Alignment.EXPAND:
                    item.width = available_width * self.scale_x
                    item.x = cursor_x
                else:
                    item.width = item_width * self.scale_x
                    if self.alignment == Alignment.CENTER:
                        item.x = cursor_x + (available_width - item.width) / 2
                    elif self.alignment == Alignment.RIGHT:
                        item.x = cursor_x + available_width - item.width
                    else:  # LEFT
                        item.x = cursor_x

                item.y = cursor_y
                item.height = item_height * self.scale_y
                cursor_y -= item.height + spacing
            else:
                # 水平レイアウト
                item.x = cursor_x
                item.y = cursor_y
                item.width = item_width * self.scale_x
                item.height = item_height * self.scale_y
                cursor_x += item.width + spacing


    def _update_hit_positions_recursive(self) -> None:
        if self._hit_manager:
            self._hit_manager.update_positions(self.style)
        for element in self._elements:
            if isinstance(element, GPULayout):
                element._update_hit_positions_recursive()

    # ─────────────────────────────────────────────────────────────────────────
    # 描画
    # ─────────────────────────────────────────────────────────────────────────
