# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Constants
"""

from __future__ import annotations

import sys

# プラットフォーム検出
IS_MAC = sys.platform == "darwin"

# パネルリサイズ定数
MIN_PANEL_WIDTH = 200
MIN_PANEL_HEIGHT = 100  # 将来用（高さリサイズ時）
RESIZE_HANDLE_SIZE = 16  # UI スケーリング前のピクセル

# パネル境界クランプ定数
CLAMP_MARGIN = 20  # エリア端からの最小マージン（ピクセル）
