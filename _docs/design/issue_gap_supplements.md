# Issue Gap Supplements

> Created: 2026-01-06
> Purpose: TBD 部分の具体化、Issue 更新用

---

## Issue #79: uid 補完

### 9.1 Migration Timing

```
┌─────────────────────────────────────────────────────────────┐
│  Migration Strategy: "Load-time with Lazy Persistence"      │
├─────────────────────────────────────────────────────────────┤
│  1. Load JSON/Backup                                         │
│     ├─ If uid exists → use as-is                            │
│     └─ If uid missing → generate uid in memory               │
│                                                              │
│  2. In-Memory State                                          │
│     └─ All menus have uid (generated or loaded)              │
│                                                              │
│  3. Save/Export                                              │
│     └─ Write uid to file (persists the generated uid)        │
├─────────────────────────────────────────────────────────────┤
│  Advantage: No forced migration, gradual rollout             │
│  Disadvantage: uid may change until first save               │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 generate_uid() Specification

```python
import uuid
import base64

# Mode prefix mapping
UID_PREFIX = {
    'PMENU': 'pm',
    'RMENU': 'rm',
    'DIALOG': 'pd',
    'PANEL': 'pg',
    'HPANEL': 'hp',
    'SCRIPT': 'sk',
    'MACRO': 'mc',
    'MODAL': 'md',
    'STICKY': 'st',
    'PROPERTY': 'pr',
}

def generate_uid(mode: str) -> str:
    """Generate a unique identifier for a menu.

    Format: {mode_prefix}_{base32_8chars}
    Example: pm_9f7c2k3h

    Args:
        mode: Menu mode (PMENU, RMENU, etc.)

    Returns:
        Unique identifier string
    """
    prefix = UID_PREFIX.get(mode, 'xx')
    random_bytes = uuid.uuid4().bytes[:5]  # 5 bytes = 40 bits
    b32 = base64.b32encode(random_bytes).decode('ascii').lower()[:8]
    return f"{prefix}_{b32}"
```

### 9.3 Broken Reference Handling

| Scenario | Detection | Action |
|----------|-----------|--------|
| Menu deleted | `uid` not in `pie_menus` | Show warning icon + tooltip |
| Name changed | N/A (uid stable) | No action needed |
| Import collision | Same `uid` exists | Regenerate uid for imported menu |

```python
def resolve_menu_reference(uid_or_name: str) -> Optional[PMItem]:
    """Resolve menu reference with fallback.

    Resolution order:
    1. uid exact match
    2. name exact match (fallback for PME1 compatibility)
    3. None (broken reference)
    """
    pr = get_prefs()

    # Try uid first
    for pm in pr.pie_menus:
        if getattr(pm, 'uid', None) == uid_or_name:
            return pm

    # Fallback to name (PME1 compatibility)
    if uid_or_name in pr.pie_menus:
        return pr.pie_menus[uid_or_name]

    return None
```

### 9.4 PropertyGroup Changes

```python
# pme_types.py - PMItem class addition
class PMItem(PropertyGroup):
    # Existing fields...

    # NEW: uid field
    uid: StringProperty(
        name="UID",
        description="Unique identifier (read-only)",
        options={'HIDDEN'},  # Not shown in UI by default
    )

    def ensure_uid(self):
        """Ensure this menu has a uid, generating one if needed."""
        if not self.uid:
            self.uid = generate_uid(self.mode)
        return self.uid
```

---

## Issue #83: Converter 補完

### 3.1 Version Detection Logic

```python
def detect_pme_version(data: dict | list) -> tuple[str, int]:
    """Detect PME version from JSON data.

    Returns:
        (version_name, tuple_length)
        - version_name: "pme2", "pme1.19", "pme1.18", "pme1.legacy"
        - tuple_length: Expected menu tuple length (0 for PME2)
    """
    # PME2: Has $schema
    if isinstance(data, dict) and "$schema" in data:
        return ("pme2", 0)

    # PME1 dict format
    if isinstance(data, dict) and "menus" in data:
        menus = data.get("menus", [])
        if menus and isinstance(menus[0], (list, tuple)):
            length = len(menus[0])
            if length >= 11:
                return ("pme1.19", 11)  # PME-Fork 1.19.x
            elif length >= 9:
                return ("pme1.18", 9)   # PME 1.18.x
            else:
                return ("pme1.legacy", length)

    # Very old list format
    if isinstance(data, list):
        return ("pme1.legacy", len(data[0]) if data else 0)

    raise ValueError("Unknown PME format")
```

### 3.2 Error Handling Policy

```python
class ConversionError(Exception):
    """Raised when conversion fails."""
    pass

class ConversionWarning:
    """Non-fatal conversion issues."""
    def __init__(self, menu_name: str, field: str, message: str):
        self.menu_name = menu_name
        self.field = field
        self.message = message

class ConversionResult:
    """Result of PME1 → PME2 conversion."""
    def __init__(self):
        self.menus: list[MenuSchema] = []
        self.warnings: list[ConversionWarning] = []
        self.errors: list[ConversionError] = []
        self.name_to_uid: dict[str, str] = {}  # For reference resolution

    @property
    def success(self) -> bool:
        return len(self.errors) == 0
```

### 3.3 Hotkey Parsing

```python
def parse_hotkey_string(encoded: str) -> dict:
    """Parse PME1 encoded hotkey string.

    PME1 format: Uses keymap_helper.encode()/decode()
    See: keymap_helper.py lines 200-250
    """
    from . import keymap_helper as KH

    # Use existing decode function
    decoded = KH.decode_hotkey(encoded)

    return {
        "key": decoded.get("key", "NONE"),
        "ctrl": decoded.get("ctrl", False),
        "shift": decoded.get("shift", False),
        "alt": decoded.get("alt", False),
        "oskey": decoded.get("oskey", False),
        "any": decoded.get("any", False),
        "key_mod": decoded.get("key_mod", "NONE"),
        "chord": decoded.get("chord", "NONE"),
    }
```

### 3.4 Settings Data Parsing

```python
def parse_data_string(encoded: str, mode: str) -> dict:
    """Parse PME1 encoded settings data.

    PME1 format: Uses core/schema.py (formerly core/props.py)
    """
    from .core.schema import schema

    # Use existing parse function
    parsed = schema.parse(encoded)

    # Remove mode prefix for schema v2
    result = {}
    prefix_map = {
        'PMENU': 'pm_',
        'RMENU': 'rm_',
        'DIALOG': 'dlg_',
        # ... etc
    }
    prefix = prefix_map.get(mode, '')

    for key, value in parsed.items():
        clean_key = key[len(prefix):] if key.startswith(prefix) else key
        result[clean_key] = value

    return result
```

---

## Issue #84: Dataclass 補完

### 4.1 ActionType Definition

```python
from typing import Literal

# All action types (including Modal-specific)
ActionType = Literal[
    "command",   # Python code / operator
    "custom",    # Custom UI layout
    "prop",      # Property display
    "menu",      # Submenu reference
    "hotkey",    # Hotkey execution
    "empty",     # Empty slot
    "invoke",    # Modal: On Invoke
    "finish",    # Modal: On Confirm
    "cancel",    # Modal: On Cancel
    "update",    # Modal: On Update
]

# Modal-only action types
MODAL_ACTION_TYPES = {"invoke", "finish", "cancel", "update"}
```

### 4.2 Validation Specification

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ValidationError:
    path: str       # e.g., "menus[0].items[2].action"
    field: str      # e.g., "type"
    message: str    # e.g., "Invalid action type: 'unknown'"

class SchemaValidator:
    """Validate PME2 schema objects."""

    def validate_menu(self, menu: "MenuSchema") -> list[ValidationError]:
        errors = []

        # Required fields
        if not menu.uid:
            errors.append(ValidationError(
                path=f"menus[{menu.name}]",
                field="uid",
                message="uid is required"
            ))

        if not menu.name:
            errors.append(ValidationError(
                path=f"menus[{menu.uid}]",
                field="name",
                message="name is required"
            ))

        # Validate items
        for i, item in enumerate(menu.items):
            errors.extend(self.validate_item(item, f"menus[{menu.uid}].items[{i}]"))

        return errors

    def validate_item(self, item: "MenuItemSchema", path: str) -> list[ValidationError]:
        errors = []

        # Action type validation
        if item.action.type not in ActionType.__args__:
            errors.append(ValidationError(
                path=path,
                field="action.type",
                message=f"Invalid action type: '{item.action.type}'"
            ))

        # Modal action type check
        if item.action.type in MODAL_ACTION_TYPES:
            # Validate parent menu is MODAL mode
            pass  # Context-dependent validation

        return errors
```

### 4.3 Full Dataclass Structure

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Style:
    accent_color: Optional[str] = None  # #RRGGBB
    accent_usage: str = "none"  # none, bar-left, bar-right, dot, background

@dataclass
class HotkeySchema:
    key: str = "NONE"
    ctrl: bool = False
    shift: bool = False
    alt: bool = False
    oskey: bool = False
    any: bool = False
    key_mod: str = "NONE"
    chord: str = "NONE"
    keymaps: list[str] = field(default_factory=lambda: ["Window"])
    activation: str = "PRESS"
    drag_direction: str = "ANY"

@dataclass
class Action:
    type: str  # ActionType
    value: str
    context: Optional[str] = None  # for command
    # Type-specific fields handled via factory methods

    @classmethod
    def command(cls, value: str, context: Optional[str] = None) -> "Action":
        return cls(type="command", value=value, context=context)

    @classmethod
    def menu(cls, uid: str) -> "Action":
        return cls(type="menu", value=uid)

    @classmethod
    def empty(cls) -> "Action":
        return cls(type="empty", value="")

@dataclass
class MenuItemSchema:
    name: str
    action: Action
    icon: Optional[str] = None
    icon_only: bool = False
    hidden: bool = False
    enabled: bool = True
    description: Optional[str] = None
    description_expr: Optional[str] = None
    style: Optional[Style] = None
    extensions: dict = field(default_factory=dict)

@dataclass
class MenuSchema:
    uid: str
    name: str
    mode: str  # MenuMode
    enabled: bool = True
    hotkey: Optional[HotkeySchema] = None
    settings: dict = field(default_factory=dict)
    description: Optional[str] = None
    description_expr: Optional[str] = None
    style: Optional[Style] = None
    poll: str = "return True"
    tags: list[str] = field(default_factory=list)
    items: list[MenuItemSchema] = field(default_factory=list)
    extensions: dict = field(default_factory=dict)

@dataclass
class PME2File:
    schema: str = "https://pluglug.github.io/pme/schema/pme2-2.0.json"
    schema_version: str = "2.0"
    addon_version: str = "2.0.0"
    exported_at: Optional[str] = None
    menus: list[MenuSchema] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    extensions: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        pass  # Use dataclasses.asdict with custom handling

    @classmethod
    def from_dict(cls, data: dict) -> "PME2File":
        """Deserialize from JSON dict."""
        pass  # Recursive construction
```

---

## 補足: pme_mini について

Issue #83, #84 で参照されている `pme_mini/` はこのリポジトリに存在しません。
これは別リポジトリのプロトタイプであり、実装は新規作成となります。

Issue 更新時にこの参照を削除するか、「参考実装なし」と明記することを推奨します。

---

## Issue #80: Style 補完

### 80.1 Blender UI での色表示

Blender の UILayout は任意の色表示をネイティブサポートしていない。

**2.0.0 推奨アプローチ**: Box インジケーター

```python
def draw_item_with_style(layout, item, style):
    if style and style.accent_color and style.accent_usage != "none":
        row = layout.row(align=True)
        if style.accent_usage == "bar-left":
            box = row.box()
            box.scale_x = 0.1
            box.label(text="", icon='BLANK1')
        row.operator(...)
```

**2.1.0 検討**: GPU 描画 or カスタムアイコン生成

### 80.2 継承ロジック

```python
def resolve_style(menu: MenuSchema, item: MenuItemSchema) -> Optional[Style]:
    if item.style and item.style.accent_color:
        return item.style
    if menu.style and menu.style.accent_color:
        return menu.style
    return None
```

---

## Issue #81: description 補完

### 81.1 評価コンテキスト

```python
DESCRIPTION_EVAL_CONTEXT = {
    'C': bpy.context,
    'D': bpy.data,
    'bpy': bpy,
    'item': current_pmi,
    'menu': current_pm,
}
```

### 81.2 エラーハンドリング

| Scenario | Behavior |
|----------|----------|
| Syntax error | Show `[Syntax Error]` |
| Runtime error | Show `[Error: message]` |
| Empty result | Empty string |

---

## Issue #82: Action.context 補完

### 82.1 実行フロー

```python
def execute_command_action(action: Action, globals: dict):
    override_dict = {}
    if action.context:
        try:
            override_dict = eval(action.context, globals)
        except Exception as e:
            print(f"PME: Context evaluation error: {e}")

    if override_dict:
        with bpy.context.temp_override(**override_dict):
            exec(action.value, globals)
    else:
        exec(action.value, globals)
```

### 82.2 セキュリティ

PME は既に `eval()` を command, poll, custom で使用。
`context` フィールドは新たなリスクを導入しない。

---

## Issue #77: Git Mode RFC

### 77.1 Schema v2 との関係

Git Mode は Schema v2 と**独立だが補完的**:
- Schema v2: JSON フォーマット
- Git Mode: どこに保存するか

### 77.2 推奨スコープ

| Version | Scope |
|---------|-------|
| 2.0.0 | Schema v2、単一ファイル export |
| 2.0.1 | Per-menu file export option |
| 2.1.0 | Full Git mode (RFC implementation) |

---

*Created: 2026-01-06*
*Updated: 2026-01-06 - Added #80, #81, #82, #77 supplements*
