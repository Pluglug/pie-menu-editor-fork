# infra/io.py - File I/O utilities for import/export/backup
# LAYER = "infra"
#
# This module provides low-level file operations without depending on
# prefs or editors layers. PM creation logic remains in preferences.py.

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable
from zipfile import ZipFile, is_zipfile

if TYPE_CHECKING:
    from typing import Iterator


# =============================================================================
# Path Helpers
# =============================================================================

from ..addon import ADDON_ID


def _get_addon_id_from_path(addon_path: str) -> str:
    """Extract addon ID from the addon path (directory name)."""
    return os.path.basename(addon_path)


# -----------------------------------------------------------------------------
# User Resource Paths (Blender standard location)
# -----------------------------------------------------------------------------
# These use bpy.utils.user_resource() for Blender-standard user data storage.
# User resources are safe from addon updates/reinstalls.
#
# Directory structure under get_user_config_dir():
#   scripts/
#     autorun/      - Scripts run at addon startup
#     register/     - Scripts run at register()
#     unregister/   - Scripts run at unregister()
#   icons/          - User custom icons
#   backups/        - Backup files
# -----------------------------------------------------------------------------

def get_user_config_dir(create: bool = False) -> str:
    """
    Get PME's user config directory (Blender standard location).

    Location: {blender_config}/addons/pie_menu_editor/

    This is the base directory for all user-specific data that should
    survive addon updates. Subdirectories include:
      - scripts/         User scripts (autorun/, register/, unregister/)
      - icons/           User custom icons
      - backups/         Backup files

    Args:
        create: If True, create the directory if it doesn't exist.

    Returns:
        Path to the user config directory.
    """
    # Import here to avoid bpy dependency at module load time
    from bpy.utils import user_resource

    config_path = user_resource("CONFIG", path="addons", create=create)
    user_dir = os.path.join(config_path, ADDON_ID)

    if create and not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)

    return user_dir


def get_user_scripts_dir(create: bool = False) -> str:
    """
    Get user scripts directory.

    Location: {user_config}/scripts/

    Subdirectories (implicit, same structure as system scripts):
      - autorun/      Scripts run at addon startup
      - register/     Scripts run at register()
      - unregister/   Scripts run at unregister()

    Args:
        create: If True, create the directory if it doesn't exist.
    """
    scripts_dir = os.path.join(get_user_config_dir(create=create), "scripts")

    if create and not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir, exist_ok=True)

    return scripts_dir


def get_user_icons_dir(create: bool = False) -> str:
    """
    Get user icons directory.

    Location: {user_config}/icons/

    Args:
        create: If True, create the directory if it doesn't exist.
    """
    icons_dir = os.path.join(get_user_config_dir(create=create), "icons")

    if create and not os.path.exists(icons_dir):
        os.makedirs(icons_dir, exist_ok=True)

    return icons_dir


def get_user_backup_dir(create: bool = False) -> str:
    """
    Get user backup directory.

    Location: {user_config}/backups/

    Args:
        create: If True, create the directory if it doesn't exist.
    """
    backup_dir = os.path.join(get_user_config_dir(create=create), "backups")

    if create and not os.path.exists(backup_dir):
        os.makedirs(backup_dir, exist_ok=True)

    return backup_dir


# -----------------------------------------------------------------------------
# System Resource Paths (Addon directory, read-only)
# -----------------------------------------------------------------------------
# These are bundled with the addon and should not be modified by users.
# -----------------------------------------------------------------------------

def get_system_scripts_dir(addon_path: str) -> str:
    """
    Get PME system scripts directory.

    Location: {addon_path}/scripts/

    Contains:
      - command_*.py    Command templates
      - custom_*.py     Custom templates
      - autorun/functions.py  PME system functions (DO NOT EDIT)
    """
    return os.path.join(addon_path, "scripts")


def get_system_icons_dir(addon_path: str) -> str:
    """
    Get PME system icons directory.

    Location: {addon_path}/icons/

    Contains system icons (p*.png, brush.*.dat, etc.)
    """
    return os.path.join(addon_path, "icons")


# -----------------------------------------------------------------------------
# Legacy Paths (for backward compatibility, will be deprecated)
# -----------------------------------------------------------------------------

def get_addon_data_path(addon_path: str) -> str:
    """
    Get the addon data directory path.

    DEPRECATED: Use get_user_config_dir() instead.

    Currently: {addon_path}/../{addon_id}_data/
    """
    addon_id = _get_addon_id_from_path(addon_path)
    return os.path.abspath(
        os.path.join(addon_path, os.pardir, addon_id + "_data")
    )


def get_backup_folder_path(addon_path: str) -> str:
    """
    Get the backup folder path.

    DEPRECATED: Use get_user_backup_dir() instead.
    Currently returns legacy path for backward compatibility.
    """
    return os.path.join(get_addon_data_path(addon_path), "backups")


def get_user_icons_path(addon_path: str) -> str:
    """
    Get the user icons directory path.

    DEPRECATED: Use get_user_icons_dir() instead.
    Currently returns legacy path (addon directory).
    """
    return os.path.join(addon_path, "icons")


# =============================================================================
# Import Helpers
# =============================================================================

@dataclass
class ImportResult:
    """Result of reading an import file."""
    json_data_list: list[str]
    """List of JSON strings (one per .json file in archive)."""

    extracted_files: list[str]
    """List of extracted file paths (relative to addon path)."""

    has_icons: bool
    """Whether icons were extracted."""

    errors: list[str]
    """List of error messages."""


def read_import_file(
    filepath: str,
    addon_path: str,
    password: str | None = None,
    conflict_mode: str = 'RENAME',
) -> ImportResult:
    """
    Read an import file (JSON or ZIP) and return its contents.

    Args:
        filepath: Path to the import file.
        addon_path: Path to the addon directory (for resource extraction).
        password: Optional password for encrypted ZIP files.
        conflict_mode: How to handle file conflicts ('RENAME', 'SKIP', 'REPLACE').

    Returns:
        ImportResult with JSON data and extracted files.
    """
    result = ImportResult(
        json_data_list=[],
        extracted_files=[],
        has_icons=False,
        errors=[],
    )

    if is_zipfile(filepath):
        _read_zip_file(filepath, addon_path, password, conflict_mode, result)
    else:
        _read_json_file(filepath, result)

    return result


def _read_json_file(filepath: str, result: ImportResult) -> None:
    """Read a plain JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            result.json_data_list.append(f.read())
    except Exception as e:
        result.errors.append(f"Failed to read file: {e}")


def _read_zip_file(
    filepath: str,
    addon_path: str,
    password: str | None,
    conflict_mode: str,
    result: ImportResult,
) -> None:
    """Read a ZIP archive and extract its contents."""
    try:
        with ZipFile(filepath, "r") as zf:
            if password:
                zf.setpassword(password.encode("utf-8"))

            # Test archive integrity
            try:
                zf.testzip()
            except RuntimeError as e:
                result.errors.append(str(e))
                return

            for info in zf.infolist():
                if info.is_dir():
                    # Create directory
                    if info.filename == "icons/":
                        result.has_icons = True
                    try:
                        os.makedirs(
                            os.path.join(addon_path, info.filename),
                            exist_ok=True
                        )
                    except Exception:
                        pass

                elif info.filename.endswith(".json"):
                    # Read JSON content
                    try:
                        json_bytes = zf.read(info.filename)
                        result.json_data_list.append(json_bytes.decode("utf-8"))
                    except Exception as e:
                        result.errors.append(f"Failed to read {info.filename}: {e}")

                else:
                    # Extract other files (icons, etc.)
                    target_path = os.path.join(addon_path, info.filename)
                    should_extract, new_filename = _resolve_file_conflict(
                        target_path, info.filename, conflict_mode
                    )

                    if should_extract:
                        if new_filename:
                            info.filename = new_filename
                        try:
                            zf.extract(info, path=addon_path)
                            result.extracted_files.append(info.filename)
                        except Exception as e:
                            result.errors.append(f"Failed to extract {info.filename}: {e}")

    except Exception as e:
        result.errors.append(f"Failed to open ZIP file: {e}")


def _resolve_file_conflict(
    target_path: str,
    filename: str,
    conflict_mode: str,
) -> tuple[bool, str | None]:
    """
    Resolve a file conflict.

    Returns:
        (should_extract, new_filename or None)
    """
    if not os.path.isfile(target_path):
        return True, None

    if conflict_mode == 'SKIP':
        return False, None

    if conflict_mode == 'REPLACE':
        return True, None

    # RENAME mode: generate unique filename
    mo = re.search(r"(.+)\.(\d{3,})(\.\w+)", filename)
    if mo:
        name, idx, ext = mo.groups()
        idx = int(idx)
    else:
        name, ext = os.path.splitext(filename)
        idx = 0

    base_dir = os.path.dirname(target_path)
    while True:
        idx += 1
        new_filename = f"{name}.{str(idx).zfill(3)}{ext}"
        if not os.path.isfile(os.path.join(base_dir, os.path.basename(new_filename))):
            break

    return True, new_filename


# =============================================================================
# Export Helpers
# =============================================================================

def write_export_file(filepath: str, data: dict[str, Any]) -> None:
    """
    Write data to a JSON file.

    Args:
        filepath: Path to the output file.
        data: Data to serialize as JSON.

    Raises:
        Exception: If writing fails.
    """
    if not filepath.endswith(".json"):
        filepath += ".json"

    json_str = json.dumps(data, indent=2, separators=(", ", ": "))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json_str)


# =============================================================================
# Backup Management
# =============================================================================

# Regex pattern for backup filenames: backup_YYYY.MM.DD_HH.MM.SS.json
RE_BACKUP_FILENAME = re.compile(
    r"backup_\d{4}\.\d{2}\.\d{2}_\d{2}\.\d{2}\.\d{2}\.json"
)

DEFAULT_MAX_BACKUPS = 20


@dataclass
class BackupInfo:
    """Information about a backup file."""
    filename: str
    filepath: str
    timestamp: datetime | None


class BackupManager:
    """Manages backup files for PME data."""

    def __init__(self, addon_path: str | None = None, max_backups: int = DEFAULT_MAX_BACKUPS):
        """
        Initialize the backup manager.

        Args:
            addon_path: Deprecated. Previously used for legacy path.
                        Now uses Blender standard user config location.
            max_backups: Maximum number of backups to keep.
        """
        # addon_path is kept for API compatibility but no longer used
        self.max_backups = max_backups
        self._backup_folder: str | None = None

    @property
    def backup_folder(self) -> str:
        """Get the backup folder path (Blender standard location)."""
        if self._backup_folder is None:
            self._backup_folder = get_user_backup_dir(create=True)
        return self._backup_folder

    def ensure_backup_folder(self) -> None:
        """Create the backup folder if it doesn't exist."""
        # get_user_backup_dir(create=True) already creates the folder
        get_user_backup_dir(create=True)

    def list_backups(self) -> list[BackupInfo]:
        """
        List all backup files, sorted by filename (oldest first).

        Returns:
            List of BackupInfo objects.
        """
        if not os.path.exists(self.backup_folder):
            return []

        backups = []
        for filename in sorted(os.listdir(self.backup_folder)):
            if RE_BACKUP_FILENAME.match(filename):
                filepath = os.path.join(self.backup_folder, filename)
                # Parse timestamp from filename
                try:
                    # backup_YYYY.MM.DD_HH.MM.SS.json
                    ts_str = filename[7:-5]  # Remove "backup_" and ".json"
                    timestamp = datetime.strptime(ts_str, "%Y.%m.%d_%H.%M.%S")
                except ValueError:
                    timestamp = None

                backups.append(BackupInfo(
                    filename=filename,
                    filepath=filepath,
                    timestamp=timestamp,
                ))

        return backups

    def get_latest_backup(self) -> BackupInfo | None:
        """Get the most recent backup, or None if no backups exist."""
        backups = self.list_backups()
        return backups[-1] if backups else None

    def read_backup(self, backup: BackupInfo) -> str | None:
        """
        Read the content of a backup file.

        Returns:
            The backup content as a string, or None if reading fails.
        """
        try:
            with open(backup.filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    def generate_backup_filename(self) -> str:
        """Generate a new backup filename with current timestamp."""
        return "backup_%s.json" % datetime.now().strftime("%Y.%m.%d_%H.%M.%S")

    def should_create_backup(self, current_data: str) -> tuple[bool, str]:
        """
        Check if a new backup should be created.

        Args:
            current_data: The current data as JSON string.

        Returns:
            (should_create, reason)
        """
        if not current_data:
            return False, "No data to backup"

        # Check if backup with same timestamp already exists
        new_filename = self.generate_backup_filename()
        new_filepath = os.path.join(self.backup_folder, new_filename)
        if os.path.isfile(new_filepath):
            return False, f"Backup already exists: {new_filepath}"

        # Compare with latest backup
        latest = self.get_latest_backup()
        if latest:
            last_data = self.read_backup(latest)
            if last_data == current_data:
                return False, "No changes since last backup"

        return True, ""

    def cleanup_old_backups(self) -> list[str]:
        """
        Remove old backups exceeding the maximum count.

        Returns:
            List of removed backup filenames.
        """
        backups = self.list_backups()
        removed = []

        if len(backups) >= self.max_backups:
            # Remove oldest backups
            num_to_remove = len(backups) + 1 - self.max_backups
            for i in range(num_to_remove):
                try:
                    os.remove(backups[i].filepath)
                    removed.append(backups[i].filename)
                except Exception:
                    pass

        return removed

    def create_backup(
        self,
        data: dict[str, Any],
        check_changes: bool = True,
    ) -> tuple[str | None, str]:
        """
        Create a new backup.

        Args:
            data: Data to backup (will be serialized to JSON).
            check_changes: If True, skip backup if no changes from last backup.

        Returns:
            (backup_filepath or None, message)
        """
        self.ensure_backup_folder()

        # Serialize data
        json_str = json.dumps(data, indent=2, separators=(", ", ": "))

        # Check if backup is needed
        if check_changes:
            should_create, reason = self.should_create_backup(json_str)
            if not should_create:
                return None, reason

        # Cleanup old backups
        self.cleanup_old_backups()

        # Create new backup
        new_filename = self.generate_backup_filename()
        new_filepath = os.path.join(self.backup_folder, new_filename)

        try:
            with open(new_filepath, "w", encoding="utf-8") as f:
                f.write(json_str)
            return new_filepath, f"Backup created: {new_filepath}"
        except Exception as e:
            return None, f"Failed to create backup: {e}"


# =============================================================================
# JSON Parsing Utilities
# =============================================================================

def parse_json_data(json_data: str | bytes) -> tuple[dict[str, Any] | None, str | None]:
    """
    Parse JSON data and extract version and menus.

    Args:
        json_data: JSON string or bytes.

    Returns:
        (parsed_dict with 'version' and 'menus', error_message or None)

    The returned dict has:
        - 'version': tuple of ints (e.g., (1, 19, 0))
        - 'menus': list of menu data
    """
    if isinstance(json_data, bytes):
        json_data = json_data.decode("utf-8")

    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"

    # Handle legacy format (list of menus)
    if isinstance(data, list):
        return {
            'version': (1, 13, 6),
            'menus': data,
        }, None

    # Handle modern format (dict with version and menus)
    if isinstance(data, dict):
        try:
            version_str = data.get("version", "1.13.6")
            version = tuple(int(i) for i in version_str.split("."))
            menus = data.get("menus", [])
            return {
                'version': version,
                'menus': menus,
                'schema': data.get('schema'),
            }, None
        except (ValueError, KeyError) as e:
            return None, f"Invalid JSON format: {e}"

    return None, "Invalid JSON format: expected list or dict"


# =============================================================================
# Module Registration (for new loader)
# =============================================================================

def register():
    pass


def unregister():
    pass
