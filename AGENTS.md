# AGENTS.md

ユーザーには日本語で回答してください。

This file is the entry point for coding agents working in this repo.
Follow it before making changes.

Required reading (in order):
- `CLAUDE.md`
- `.claude/rules/architecture.md`
- `.claude/rules/bpy_imports.md`
- `.claude/rules/compatibility.md`
- `.claude/rules/json_schema_v2.md`
- `.claude/rules/milestones.md`
- `.claude/rules/testing.md`

If anything here conflicts with the docs above, the docs above win.

Quick guardrails (non-exhaustive):
- Preserve behavior and user-visible formats unless explicitly requested.
- Respect layer direction: prefs > operators > editors > ui > infra > core.
  No lower -> higher imports; core has no Blender deps.
- Do not import prefs from lower layers; use `addon.get_prefs()`.
- Blender 5.0+ only; keep PME 1.19.x JSON/backup import compatibility.
- Avoid changes in sensitive runtime/keymap/modal/prefs schema areas unless asked.

Testing (minimum):
- Enable addon in Blender 5.0+ with no errors.
- Preferences panel opens.
- Pie menu invocation works.
- Settings persist after Blender restart.

More docs:
- `_docs/` for design, analysis, and guides (see `CLAUDE.md`).
