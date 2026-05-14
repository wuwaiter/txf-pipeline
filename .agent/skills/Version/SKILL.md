# Version Management Skill
---
name: "Project/Skill version history definition"
description: "This skill defines the version history of a project/skill, and also define version history workflow. The documentation for version history of a project/skill is under `md/Version.md`"
---


## Convention

- All markdown files (except `README.md`) live in the `md/` folder at the project root.
- `md/Version.md` records every meaningful change with a version tag and date.
- `.agent/Version/SKILLS.md` (this file) documents the versioning workflow itself.

## Version Format

```
## vX.Y.Z — YYYY-MM-DD

### Changes
- <bullet describing what changed>
```

Increment rules:
- **Patch** (Z): documentation updates, minor fixes
- **Minor** (Y): new features, structural reorganization
- **Major** (X): breaking changes, major architectural shifts

## Workflow

1. Make code/structure changes.
2. Open `md/Version.md` and prepend a new version block at the top of the history.
3. Commit all changes together.

## Current Version

v0.5.0 — 2026-05-12: Introduced `md/` directory, moved markdown files, established versioning convention.
