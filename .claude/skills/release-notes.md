# PME-F Release Notes Skill

Write release notes for Pie Menu Editor Fork releases following the established style.

## Style Guidelines

### Structure (Required Sections)

1. **## What's Changed** - Main changes grouped by category
   - Use `### Category Name` for groupings (e.g., "Side Areas & Screen Layout", "CHORDS & Key Handling")
   - Each change is a bullet point with **bold key phrase** and technical explanation
   - Include "why" not just "what" was changed

2. **## How to Update (Blender X.X+)** - Installation instructions
   - Step-by-step numbered list
   - Include backup reminders
   - Note if restart is required

3. **## Documentation** - Link to PME Docs

4. **## Community** - Links to BlenderArtists and GitHub Discussions

5. **## Support the Project** - Ko-fi button and brief message

### Formatting Conventions

- Use technical but accessible language
- Include Blender version compatibility notes where relevant
- For bug fixes, describe the symptom that was fixed
- For new features, describe the user benefit
- Reference issue numbers with `#XX` format when applicable

### Category Examples

Good category names:
- "Side Areas & Screen Layout"
- "CHORDS & Key Handling"
- "Blender X.X Compatibility"
- "Custom Icons, Toolbar & Panels"
- "Preferences & Properties"
- "Development Infrastructure"
- "Release Packaging"

### Example Entry Style

```markdown
### Side Areas & Screen Layout

- Fix **side area width clamping** to prevent layout corruption when toggling areas with extreme widths.
- Improve **main/side View3D pair detection** for side area toggle:
  - Prioritize the current area when resolving the main area.
  - Allow closing the side area from the side context when adjacent to the configured main area.
```

### Footer Sections Template

```markdown
## How to Update (Blender 4.2+)

1. **Back up your settings** using the **Export** button in PME preferences.
2. Download the latest **.zip** file from this release.
3. Open Blender → **Edit > Preferences**.
4. Go to **Add-ons**, click the **…** menu → **Install from Disk…**.
5. Select the downloaded **.zip** file and install it.
6. **Restart Blender** (required).

## Documentation

Visit [PME Docs](https://pluglug.github.io/pme-docs/) for guides and tutorials.

## Community

Join discussions on [BlenderArtists Forum](http://blenderartists.org/forum/showthread.php?392910) or use GitHub [Discussions](../../discussions).

## Support the Project

If PME-F has improved your Blender workflow, consider supporting development.

Your support helps maintain compatibility with new Blender versions and implement community-requested features.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Pluglug)
```

## Gathering Information

When writing release notes, gather:

1. **Commits between tags**: `git log vPREV..vNEW --oneline`
2. **Detailed commit messages**: `git log vPREV..vNEW --pretty=format:"%s%n%b"`
3. **Related PRs**: `gh pr list --state merged --base main`
4. **Previous release style**: `gh release view vPREV`

## Key Principles

1. **User-focused**: Explain impact on user workflow
2. **Technical accuracy**: Include API names, version numbers
3. **Grouped logically**: Related changes together
4. **Gratitude**: Thank contributors when applicable
5. **Actionable**: Clear update instructions
