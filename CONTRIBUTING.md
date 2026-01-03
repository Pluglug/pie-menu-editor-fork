# Contributing to Pie Menu Editor

Thank you for your interest in contributing to PME! This document provides guidelines and setup instructions for development.

## Development Branches

| Branch | Purpose | Blender Version | Status |
|--------|---------|-----------------|--------|
| `pme2-dev` | PME2 development (new work goes here) | 5.0+ | **Active development** |
| `pme1-lts` | PME1 final archive (v1.19.2) | 4.2 LTS - 4.x | Frozen; emergency fixes only at maintainer discretion |

**Note on PME1**:

The `pme1-lts` branch exists as the preserved final state of PME1 (v1.19.2) for Blender 4.x users.
It is **not** an actively maintained LTS line—there are no planned updates.
New contributions should target `pme2-dev` unless explicitly requested by the maintainer.

## Development Setup

### Prerequisites

- Python 3.12 (matching Blender 5.0's Python version)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

### Quick Start

```bash
# Clone the repository
git clone https://github.com/Pluglug/pie-menu-editor-fork.git
cd pie-menu-editor-fork

# Switch to development branch
git checkout pme2-dev

# Create virtual environment (optional, for tooling)
uv venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install development dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Linking to Blender

Create a symbolic link from Blender's addons directory to your local repository.

> **Note**: Replace `5.0` with your actual Blender version (e.g., `5.1`, `5.2`).
> PME2 targets Blender 5.0+, so use the appropriate version directory.

**Windows (PowerShell as Admin):**
```powershell
New-Item -ItemType SymbolicLink `
  -Path "$env:APPDATA\Blender Foundation\Blender\5.0\scripts\addons\pie_menu_editor" `
  -Target "C:\path\to\pie-menu-editor-fork"
```

**Linux/macOS:**
```bash
ln -s /path/to/pie-menu-editor-fork \
  ~/.config/blender/5.0/scripts/addons/pie_menu_editor
```

## Code Quality Tools

> **Current Policy**: Ruff, Pyright, and auto-formatting are **disabled** in pre-commit hooks to preserve the original author's code style in legacy files. Only basic checks (trailing whitespace, YAML/JSON validation, etc.) are active.
>
> As the codebase is refactored and legacy files are migrated to new modules, these tools will be gradually enabled. See `.pre-commit-config.yaml` for details.

### Linting with Ruff (manual, optional)

```bash
# Check for issues (informational only)
ruff check .

# Format code (use with caution on legacy files)
ruff format .
```

### Type Checking with Pyright (manual, optional)

```bash
pyright .
```

### Pre-commit Hooks

Pre-commit runs automatically on `git commit`. Currently, only safe checks are enabled:

```bash
# Run manually
pre-commit run --all-files
```

**Active hooks**: trailing-whitespace, end-of-file-fixer, check-yaml/json/toml, detect-private-key

**Disabled hooks** (legacy preservation): ruff, ruff-format, docformatter, pycln, pyright

## Code Style

- Follow PEP 8 with 100 character line length
- Use type hints where practical
- Japanese comments are acceptable in documentation
- See `.editorconfig` for editor settings

### Blender-specific Conventions

```python
# Standard Blender namespace shortcuts
import bpy
C = bpy.context
D = bpy.data

# Blender properties use this pattern
some_prop: bpy.props.StringProperty(name="Name")  # OK

# Import from bpy.types for operators
from bpy.types import Operator
class PME_OT_example(Operator):  # OK
```

## Testing

### Manual Testing Checklist

Before submitting a PR, verify:

- [ ] Addon enables without errors in Blender
- [ ] Existing pie menus can be called
- [ ] New pie menus can be created
- [ ] Settings persist after Blender restart

### Debug Flags

Enable debug output by setting environment variables:

```bash
# Layer violation detection
DBG_DEPS=True blender

# Structured logging (NDJSON)
DBG_STRUCTURED=True blender

# Performance profiling
DBG_PROFILE=True blender
```

## Pull Request Guidelines

### Before Submitting

1. **Create an issue first** for significant changes
2. **Branch from `pme2-dev`** (not `main`)
3. **Run pre-commit** to ensure code quality
4. **Test manually** using the checklist above

### PR Title Format

```
[Category] Brief description

Examples:
[Fix] Resolve crash when creating pie menu
[Feature] Add hotkey chord support
[Refactor] Move overlay classes to infra/overlay.py
[Docs] Update CONTRIBUTING.md
```

### Commit Message Format

```
Brief summary (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Explain the problem being solved and why this approach was chosen.

Fixes #123
```

## Architecture Overview

PME2 uses a layered architecture:

```
prefs      (5) ← Addon settings, hub
operators  (4) ← Edit/search/utility operators
editors    (3) ← Mode editors (PMENU/RMENU/DIALOG etc.)
ui         (2) ← UI helpers (LayoutHelper, UIList)
infra      (1) ← Blender API wrappers (keymap, overlay)
core       (0) ← Blender-independent logic
```

**Dependency Rule**: Upper layers may import from lower layers, not vice versa.

See `CLAUDE.md` for detailed documentation.

## Getting Help

- **Questions**: Open a [Discussion](../../discussions)
- **Bugs**: Open an [Issue](../../issues)
- **Design discussions**: Check `_docs/` documentation

## License

By contributing, you agree that your contributions will be licensed under the GPL v3 license.
