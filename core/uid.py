# core/uid.py - UID generation for PME2 menus
# LAYER = "core"
#
# This module provides Blender-independent uid generation.
# uid format: {mode_prefix}_{random_id}
# random_id: uuid4 base32 encoded, 8 chars, lowercase
#
# Design Decision: uid prefix matches settings prefix for consistency.
# See: _docs/design/json_schema_v2.md

LAYER = "core"

import uuid
import base64

# Mode prefix mapping (from json_schema_v2.md)
# Note: uid prefix matches settings prefix (e.g., SCRIPT uses s_ for both)
MODE_PREFIX_MAP = {
    'PMENU': 'pm',
    'RMENU': 'rm',
    'DIALOG': 'pd',
    'PANEL': 'pg',
    'HPANEL': 'hpg',
    'SCRIPT': 's',    # Stack Key (matches s_ settings prefix)
    'MACRO': 'mc',
    'MODAL': 'md',
    'STICKY': 'sk',   # Sticky Key (matches sk_ settings prefix)
    'PROPERTY': 'pr',
}

# Reverse mapping for validation and mode extraction
PREFIX_MODE_MAP = {v: k for k, v in MODE_PREFIX_MAP.items()}


def generate_random_id() -> str:
    """Generate a random 8-char base32 ID from uuid4.

    Returns:
        8 character lowercase base32 string
    """
    raw = uuid.uuid4().bytes
    encoded = base64.b32encode(raw).decode('ascii')
    return encoded[:8].lower()


def generate_uid(mode: str) -> str:
    """Generate a uid for the given menu mode.

    Args:
        mode: Menu mode (PMENU, RMENU, DIALOG, PANEL, HPANEL,
              SCRIPT, MACRO, MODAL, STICKY, PROPERTY)

    Returns:
        uid in format "{mode_prefix}_{random_id}"
        Example: "pm_9f7c2k3h", "rm_a2b3c4d5"

    Raises:
        ValueError: If mode is unknown
    """
    prefix = MODE_PREFIX_MAP.get(mode)
    if prefix is None:
        raise ValueError(f"Unknown menu mode: {mode}")
    return f"{prefix}_{generate_random_id()}"


def validate_uid(uid: str) -> bool:
    """Validate uid format.

    Args:
        uid: uid string to validate

    Returns:
        True if valid format, False otherwise
    """
    if not uid or not isinstance(uid, str):
        return False

    if '_' not in uid:
        return False

    parts = uid.split('_', 1)
    if len(parts) != 2:
        return False

    prefix, random_id = parts

    # Check prefix is known
    if prefix not in PREFIX_MODE_MAP:
        return False

    # Check random_id length (should be 8 chars)
    if len(random_id) != 8:
        return False

    # Check random_id is valid base32 chars (lowercase)
    # Base32 uses: a-z and 2-7
    valid_chars = set('abcdefghijklmnopqrstuvwxyz234567')
    if not all(c in valid_chars for c in random_id):
        return False

    return True


def get_mode_from_uid(uid: str) -> str | None:
    """Extract menu mode from uid prefix.

    Args:
        uid: uid string

    Returns:
        Menu mode string (e.g., "PMENU", "RMENU") or None if invalid
    """
    if not uid or not isinstance(uid, str):
        return None

    if '_' not in uid:
        return None

    prefix = uid.split('_', 1)[0]
    return PREFIX_MODE_MAP.get(prefix)


def get_prefix_for_mode(mode: str) -> str | None:
    """Get uid prefix for a menu mode.

    Args:
        mode: Menu mode (e.g., "PMENU", "RMENU")

    Returns:
        uid prefix (e.g., "pm", "rm") or None if unknown mode
    """
    return MODE_PREFIX_MAP.get(mode)
