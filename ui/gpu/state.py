# pyright: reportInvalidTypeForm=false
"""
PME GPU Layout - Panel State

GPU パネルのセッション限定状態永続化。

Note:
    永続化はメモリのみ（セッション限定）。
    Blender 再起動後はリセットされる。
    ファイルへの保存が必要な場合は、将来的に addon_prefs への保存を検討。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class GPUPanelState:
    """パネルの永続化状態（セッション限定）

    Attributes:
        x: パネルの X 座標（None = 未保存、デフォルト位置を使用）
        y: パネルの Y 座標（None = 未保存、デフォルト位置を使用）
        width: パネルの幅

    Example:
        state = get_panel_state("my_panel")
        if state.has_position:
            # 保存された位置を使用
            x, y = state.x, state.y
        else:
            # デフォルト位置を使用
            x, y = 50, region.height - 50
    """

    x: Optional[float] = None
    y: Optional[float] = None
    width: float = 250.0
    # 将来拡張
    # anchor: str = 'TOP_LEFT'
    # collapsed: bool = False

    def to_dict(self) -> dict:
        """辞書に変換"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> GPUPanelState:
        """辞書から作成"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def has_position(self) -> bool:
        """位置が保存されているかどうか

        Returns:
            x と y の両方が None でなければ True
        """
        return self.x is not None and self.y is not None


# ═══════════════════════════════════════════════════════════════════════════════
# ストレージ
# ═══════════════════════════════════════════════════════════════════════════════

_gpu_panel_states: dict[str, GPUPanelState] = {}


def get_panel_state(uid: str) -> GPUPanelState:
    """パネルの状態を取得

    存在しなければデフォルト状態（位置未保存）を返す。

    Args:
        uid: パネルの一意識別子

    Returns:
        GPUPanelState オブジェクト
    """
    return _gpu_panel_states.setdefault(uid, GPUPanelState())


def set_panel_state(uid: str, state: GPUPanelState) -> None:
    """パネルの状態を保存

    Args:
        uid: パネルの一意識別子
        state: 保存する状態
    """
    _gpu_panel_states[uid] = state


def clear_panel_states() -> None:
    """全パネル状態をクリア（テスト用）"""
    _gpu_panel_states.clear()
