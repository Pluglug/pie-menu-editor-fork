# compatibility_fixes.py - Data migration and version compatibility fixes
# LAYER = "infra"
#
# Handles automatic migration of PME data when upgrading from older versions.
# Similar to database migrations - modifies saved data to match new format.

LAYER = "infra"

import re
from .. import addon
from ..addon import get_prefs
from .debug import *
from ..core import constants as CC
from .utils import extract_str_flags_b


def fix(pms=None, version=None):
    DBG_INIT and logh("PME Fixes")
    pr = get_prefs()
    pr_version = version or tuple(pr.version)
    if pr_version == addon.VERSION:
        return

    fixes = []
    re_fix = re.compile(r"fix_(\d+)_(\d+)_(\d+)")
    for k, v in globals().items():
        mo = re_fix.search(k)
        if not mo:
            continue

        fix_version = (int(mo.group(1)), int(mo.group(2)), int(mo.group(3)))
        if fix_version <= pr_version or fix_version > addon.VERSION:
            continue
        fixes.append((fix_version, v))

    fixes.sort(key=lambda item: item[0])

    if pms is None:
        pms = pr.pie_menus

    for pm in pms:
        for fix_version, fix_func in fixes:
            fix_func(pr, pm)

    pr.version = addon.VERSION


def fix_json(pm, menu, version):
    DBG_INIT and logh("PME JSON Fixes")
    pr = get_prefs()
    fixes = []
    re_fix = re.compile(r"fix_json_(\d+)_(\d+)_(\d+)")
    for k, v in globals().items():
        mo = re_fix.search(k)
        if not mo:
            continue

        fix_version = (int(mo.group(1)), int(mo.group(2)), int(mo.group(3)))
        if fix_version <= version:
            continue
        fixes.append((fix_version, v))

    fixes.sort(key=lambda item: item[0])

    for fix_version, fix_func in fixes:
        fix_func(pr, pm, menu)


def fix_1_14_0(pr, pm):
    if pm.mode == 'PMENU':
        for pmi in pm.pmis:
            if pmi.mode == 'MENU':
                sub_pm = pmi.text in pr.pie_menus and pr.pie_menus[pmi.text]

                if (
                    sub_pm
                    and sub_pm.mode == 'DIALOG'
                    and sub_pm.get_data("pd_panel") == 0
                ):
                    pmi.text = CC.F_EXPAND + pmi.text

                    if sub_pm.get_data("pd_box"):
                        pmi.text = CC.F_EXPAND + pmi.text

    elif pm.mode == 'DIALOG':
        if pm.get_data("pd_expand"):
            pm.set_data("pd_expand", False)
            for pmi in pm.pmis:
                if pmi.mode == 'MENU':
                    sub_pm = pmi.text in pr.pie_menus and pr.pie_menus[pmi.text]
                    if sub_pm and sub_pm.mode == 'DIALOG':
                        pmi.text = CC.F_EXPAND + pmi.text


def fix_1_14_9(pr, pm):
    if pm.mode == 'STICKY':
        pm.data = re.sub(r"([^_])block_ui", r"\1sk_block_ui", pm.data)


def fix_1_17_0(pr, pm):
    if pm.mode == 'PMENU':
        for i in range(len(pm.pmis), 10):
            pm.pmis.add()


def fix_1_17_1(pr, pm):
    if not pm.ed.has_hotkey:
        return

    pm.km_name = (CC.KEYMAP_SPLITTER + " ").join(pm.km_name.split(","))


def fix_json_1_17_1(pr, pm, menu):
    if not pm.ed.has_hotkey:
        return

    menu[1] = (CC.KEYMAP_SPLITTER + " ").join(menu[1].split(","))

# =============================================================================
# PME2 2.0.0 Migrations: Prefix standardization (#92)
# =============================================================================
# MODAL: confirm, block_ui, lock → md_confirm, md_block_ui, md_lock
# PROPERTY: prop? → pr?, vector → pr_vector, etc.


def _migrate_modal_data(data):
    """Migrate MODAL data string to use md_ prefix."""
    if "md_confirm" not in data:
        data = re.sub(r'\bconfirm\b', 'md_confirm', data)
    if "md_block_ui" not in data:
        data = re.sub(r'\bblock_ui\b', 'md_block_ui', data)
    if "md_lock" not in data:
        data = re.sub(r'\block\b', 'md_lock', data)
    return data


def _migrate_property_data(data):
    """Migrate PROPERTY data string to use pr_ prefix."""
    # Change type prefix: prop? → pr?
    if data.startswith("prop?"):
        data = "pr?" + data[5:]

    # Migrate property names
    if "pr_vector" not in data:
        data = re.sub(r'\bvector\b', 'pr_vector', data)
    if "pr_mulsel" not in data:
        data = re.sub(r'\bmulsel\b', 'pr_mulsel', data)
    if "pr_hor_exp" not in data:
        data = re.sub(r'\bhor_exp\b', 'pr_hor_exp', data)
    if "pr_exp" not in data:
        data = re.sub(r'(?<!hor_)\bexp\b', 'pr_exp', data)
    if "pr_save" not in data:
        data = re.sub(r'\bsave\b', 'pr_save', data)
    return data


# Valid property types for JSON migration (defined here to avoid forward reference)
_JSON_VALID_PROP_TYPES = {'BOOL', 'INT', 'FLOAT', 'STRING', 'ENUM'}


def _migrate_json_property_poll_cmd(menu):
    """Migrate PROPERTY prop_type from menu[7] to menu[5] in JSON import.

    PME1 JSON format stores prop_type in menu[7] (poll_cmd field).
    PME2 stores it in menu[5] (pm.data) as pr_prop_type.

    This migration:
    1. Reads prop_type from menu[7] if valid
    2. Adds pr_prop_type to menu[5] (data string)
    3. Clears menu[7] to use default poll condition
    """
    # Get prop_type from menu[7] if present
    prop_type = 'BOOL'
    if len(menu) > 7 and menu[7] in _JSON_VALID_PROP_TYPES:
        prop_type = menu[7]

    # Get current data string
    data = menu[5] if len(menu) > 5 else ""
    if not data:
        data = "pr?"

    # Add pr_prop_type to data if not already present
    if "pr_prop_type" not in data:
        # Parse and append to data string
        if "?" in data:
            prefix, _, params = data.partition("?")
            if params:
                data = f"{prefix}?pr_prop_type={prop_type}&{params}"
            else:
                data = f"{prefix}?pr_prop_type={prop_type}"
        else:
            data = f"pr?pr_prop_type={prop_type}"
        menu[5] = data

    # Clear menu[7] (poll_cmd) - use default poll condition
    if len(menu) > 7:
        menu[7] = ""


def _migrate_json_extend_target(menu):
    """Migrate extend_target from menu[0] (pm.name) to menu[5] (pm.data) for JSON import.

    PME1 JSON format encodes extend information in pm.name:
    - "VIEW3D_PT_tools_pre" → prepend to VIEW3D_PT_tools
    - "TOPBAR_HT_upper_bar_right" → right region of TOPBAR_HT_upper_bar

    PME2 stores these in pm.data:
    - pd_extend_target / rm_extend_target: Blender Panel/Menu ID
    - pd_extend_side / rm_extend_side: "prepend" | "append"
    - pd_extend_order: int (0 = innermost)
    - pd_extend_is_right: bool (Header right region, DIALOG only)

    Args:
        menu: JSON menu array [name, km_name, hotkey, icon, mode, data, ...]
    """
    mode = menu[4]
    if mode not in ('DIALOG', 'RMENU'):
        return

    name = menu[0]
    # Parse name for Blender ID and position flags
    tp_name, is_right, is_prepend = extract_str_flags_b(name, CC.F_RIGHT, CC.F_PRE)

    # Check if tp_name is a valid Blender type ID
    if not any(x in tp_name for x in ('_PT_', '_MT_', '_HT_')):
        return

    # Determine prefix and values
    prefix = "pd" if mode == 'DIALOG' else "rm"
    extend_side = "prepend" if is_prepend else "append"

    # Get current data string
    data = menu[5] if len(menu) > 5 else ""

    # Build new data string with extend properties
    # Parse existing data to preserve other settings
    if data and "?" in data:
        base_prefix, _, params = data.partition("?")
        # Remove any existing extend properties (shouldn't exist, but be safe)
        param_pairs = [p for p in params.split("&") if p and not p.startswith(f"{prefix}_extend")]
        new_params = [
            f"{prefix}_extend_target={tp_name}",
            f"{prefix}_extend_side={extend_side}",
            f"{prefix}_extend_order=0",
        ]
        if prefix == "pd" and is_right:
            new_params.append(f"{prefix}_extend_is_right=True")
        all_params = new_params + param_pairs
        data = f"{base_prefix}?{'&'.join(all_params)}"
    else:
        # No existing data, create new
        base_prefix = prefix
        new_params = [
            f"{prefix}_extend_target={tp_name}",
            f"{prefix}_extend_side={extend_side}",
            f"{prefix}_extend_order=0",
        ]
        if prefix == "pd" and is_right:
            new_params.append(f"{prefix}_extend_is_right=True")
        data = f"{base_prefix}?{'&'.join(new_params)}"

    menu[5] = data

    DBG_INIT and logi(
        "PME JSON: migrated extend_target",
        f"name={name!r}",
        f"extend_target={tp_name!r}",
        f"extend_side={extend_side!r}",
        f"is_right={is_right}"
    )


def fix_json_2_0_0(pr, pm, menu):
    """
    Migrate MODAL, PROPERTY, and Extend properties in JSON import.

    JSON menu structure (PME1 format):
      menu[0] = name (may contain Blender type ID for Extend menus)
      menu[4] = mode
      menu[5] = data (pm.data string)
      menu[7] = poll_cmd (or prop_type for PROPERTY mode in PME1)
    """
    if len(menu) < 6:
        return

    mode = menu[4]
    data = menu[5]

    if mode == 'MODAL' and data:
        menu[5] = _migrate_modal_data(data)
    elif mode == 'PROPERTY':
        if data:
            menu[5] = _migrate_property_data(data)
        # Migrate prop_type from menu[7] to menu[5] (pm.data)
        _migrate_json_property_poll_cmd(menu)

    # Migrate extend_target from pm.name to pm.data (DIALOG/RMENU)
    if mode in ('DIALOG', 'RMENU'):
        _migrate_json_extend_target(menu)


def fix_2_0_0(pr, pm):
    """
    Migrate MODAL and PROPERTY properties to use standardized prefixes.
    Generate uid for menus without one.
    Migrate PROPERTY prop_type from poll_cmd to pm.data.

    Uses the same helper functions as fix_json_2_0_0 for consistency.
    """
    if pm.mode == 'MODAL' and pm.data:
        pm.data = _migrate_modal_data(pm.data)
    elif pm.mode == 'PROPERTY':
        if pm.data:
            pm.data = _migrate_property_data(pm.data)
        # Migrate prop_type from poll_cmd to pm.data (9-D-1)
        _migrate_property_poll_cmd(pm)

    # Generate uid for existing menus (Phase 9-X: uid implementation)
    if not pm.uid:
        from ..core.uid import generate_uid
        pm.uid = generate_uid(pm.mode)

    # Migrate extend_target from pm.name suffix to pm.data (Phase 9-X: #89)
    if pm.mode in ('DIALOG', 'RMENU'):
        _migrate_extend_target(pm)


def parse_extend_from_pme1_name(name):
    """Parse extend information from PME1 format pm.name.

    PME1 encodes extend information in pm.name with suffixes:
    - F_PRE ("_pre") → prepend position
    - F_RIGHT ("_right") → right region (header only, ignored in PME2)

    Args:
        name: PME1 format menu name (e.g., "VIEW3D_PT_tools_active_pre")

    Returns:
        tuple: (extend_target, extend_position) or (None, None) if not valid
            - extend_target: Blender Panel/Menu/Header ID (e.g., "VIEW3D_PT_tools_active")
            - extend_position: int (-1 for prepend, 0 for append)

    Example:
        >>> parse_extend_from_pme1_name("VIEW3D_PT_tools_active_pre")
        ("VIEW3D_PT_tools_active", -1)
        >>> parse_extend_from_pme1_name("TOPBAR_MT_file")
        ("TOPBAR_MT_file", 0)
        >>> parse_extend_from_pme1_name("My Custom Menu")
        (None, None)
    """
    # Parse name for Blender ID and position flags
    tp_name, is_right, is_prepend = extract_str_flags_b(
        name, CC.F_RIGHT, CC.F_PRE
    )

    # Check if tp_name is a valid Blender type ID
    if not any(x in tp_name for x in ('_PT_', '_MT_', '_HT_')):
        return None, None

    # Determine position: -1 for prepend, 0 for append
    extend_position = -1 if is_prepend else 0

    return tp_name, extend_position


def _migrate_extend_target(pm):
    """Migrate extend_target from pm.name suffix to pm.data.

    Uses parse_extend_from_pme1_name() to extract extend information
    from PME1 format names.

    Phase 9-X (#97): Updated to use extend_side + extend_order schema.
    Also fixes existing data where extend_target contains suffix.

    PME2 stores these in pm.data:
    - pd_extend_target / rm_extend_target: Blender Panel/Menu ID (no suffix)
    - pd_extend_side / rm_extend_side: "prepend" | "append"
    - pd_extend_order / rm_extend_order: int (0 = innermost)
    - pd_extend_is_right: bool (Header right region, DIALOG only)
    """
    # Get prefix based on mode
    prefix = "pd" if pm.mode == 'DIALOG' else "rm"
    extend_target_key = f"{prefix}_extend_target"
    extend_side_key = f"{prefix}_extend_side"
    extend_order_key = f"{prefix}_extend_order"
    extend_is_right_key = f"{prefix}_extend_is_right" if prefix == "pd" else None
    # Legacy key (to be removed after migration)
    extend_position_key = f"{prefix}_extend_position"

    current_target = pm.get_data(extend_target_key)
    current_side = pm.get_data(extend_side_key)

    # Case 1: Already fully migrated (has extend_side and clean extend_target)
    if current_side and current_target:
        # Still need to fix suffix in extend_target if present
        clean_target, is_right, is_prepend = extract_str_flags_b(
            current_target, CC.F_RIGHT, CC.F_PRE
        )
        if clean_target != current_target:
            # extend_target had suffix, fix it
            pm.set_data(extend_target_key, clean_target)
            # Migrate is_right from suffix (Header only)
            if extend_is_right_key and is_right:
                pm.set_data(extend_is_right_key, True)
            DBG_INIT and logi(
                "PME: fixed extend_target suffix",
                f"pm={pm.name!r}",
                f"old={current_target!r}",
                f"new={clean_target!r}",
                f"is_right={is_right}"
            )
        return

    # Case 2: Has extend_target but no extend_side (old schema)
    if current_target and not current_side:
        # Parse suffix from extend_target (might have _pre/_right)
        clean_target, is_right, is_prepend = extract_str_flags_b(
            current_target, CC.F_RIGHT, CC.F_PRE
        )
        # Get extend_side from old extend_position or suffix
        old_position = pm.get_data(extend_position_key)
        if old_position is not None and old_position < 0:
            extend_side = "prepend"
        elif is_prepend:
            extend_side = "prepend"
        else:
            extend_side = "append"

        pm.set_data(extend_target_key, clean_target)
        pm.set_data(extend_side_key, extend_side)
        pm.set_data(extend_order_key, 0)
        # Migrate is_right from suffix (Header only)
        if extend_is_right_key and is_right:
            pm.set_data(extend_is_right_key, True)

        DBG_INIT and logi(
            "PME: migrated extend_target (old schema)",
            f"pm={pm.name!r}",
            f"extend_target={clean_target!r}",
            f"extend_side={extend_side!r}",
            f"is_right={is_right}"
        )
        return

    # Case 3: No extend_target, parse from pm.name
    # Extract is_right directly since parse_extend_from_pme1_name doesn't return it
    _, is_right, _ = extract_str_flags_b(pm.name, CC.F_RIGHT, CC.F_PRE)
    extend_target, extend_position = parse_extend_from_pme1_name(pm.name)

    if not extend_target:
        return

    # Convert extend_position to extend_side
    extend_side = "prepend" if extend_position < 0 else "append"

    # Set new schema values
    pm.set_data(extend_target_key, extend_target)
    pm.set_data(extend_side_key, extend_side)
    pm.set_data(extend_order_key, 0)
    # Migrate is_right from pm.name suffix (Header only)
    if extend_is_right_key and is_right:
        pm.set_data(extend_is_right_key, True)

    DBG_INIT and logi(
        "PME: migrated extend_target (from name)",
        f"pm={pm.name!r}",
        f"extend_target={extend_target!r}",
        f"extend_side={extend_side!r}",
        f"is_right={is_right}"
    )


# Valid property types for PROPERTY mode migration
_VALID_PROP_TYPES = {'BOOL', 'INT', 'FLOAT', 'STRING', 'ENUM'}


def _migrate_property_poll_cmd(pm):
    """Migrate PROPERTY mode: move prop_type from poll_cmd to pm.data.

    PME1 stored prop_type in poll_cmd (a field meant for poll conditions).
    PME2 stores it in pm.data as pr_prop_type.

    This migration:
    1. Reads prop_type from poll_cmd if valid
    2. Sets pr_prop_type in pm.data
    3. Clears poll_cmd to prevent crash from invalid Python code compilation
    """
    # Check if pr_prop_type already exists in pm.data
    if "pr_prop_type" in pm.data:
        # Already migrated, just clear poll_cmd if it has old value
        if pm.poll_cmd in _VALID_PROP_TYPES:
            DBG_INIT and logi("PME: clearing legacy poll_cmd", f"pm={pm.name}")
            pm.poll_cmd = CC.DEFAULT_POLL
        return

    # Read prop_type from poll_cmd
    prop_type = pm.poll_cmd if pm.poll_cmd in _VALID_PROP_TYPES else 'BOOL'

    # Set pr_prop_type in pm.data
    pm.set_data("pr_prop_type", prop_type)
    DBG_INIT and logi(
        "PME: migrated prop_type to pm.data",
        f"pm={pm.name}",
        f"prop_type={prop_type}"
    )

    # Clear poll_cmd to prevent crash (#33 related)
    # poll_cmd with "BOOL" etc. would cause compile() to fail
    pm.poll_cmd = CC.DEFAULT_POLL
