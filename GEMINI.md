# Antigravity Workspace Guidelines for dev-kit

## Language & Documentation Integrity
- All documentation, code comments, commit messages, and changelog entries must be written strictly in **English**, regardless of the conversation language with the user.

## Versioning & Release Conventions
Every functional change, feature, or bug fix must follow the project's established semantic versioning standard:

### 1. Version Semantics (`MAJOR.MINOR.PATCH`)
- **MAJOR (`X.0.0`)**: Breaking changes to agent protocols, directory structure, or fundamental squad orchestration workflows.
- **MINOR (`x.Y.0`)**: New specialized roles, new stack adapters, new verification tools, or backwards-compatible capabilities.
- **PATCH (`x.y.Z`)**: Bug fixes, prompt refinements, script improvements, and documentation updates.

### 2. Required Version Updates
Whenever a version is bumped, the following files must be updated together:
1. `VERSION`: Contains the raw version string (e.g. `0.1.0`).
2. `CHANGELOG.md`: Add a new release section at the top formatted as:
   ```markdown
   ## X.Y.Z – DD/MM/YYYY
   - Bullet points explaining the changes clearly and concisely.
   ```
3. `README.md`: Update the current version declaration:
   ```markdown
   Current version: **X.Y.Z** (see `CHANGELOG.md`).
   ```
4. `RUN.md`: Update version references in template examples.

### 3. Git Commit & Tagging Protocol
- **Commit format**: `vX.Y.Z: <concise description in English>` (e.g. `v0.1.0: initial release of autonomous dev-kit`).
- **Git Tag**: Tag the release with annotated tag `vX.Y.Z` (`git tag -a vX.Y.Z -m "vX.Y.Z: <summary>"`) and push tags to remote (`git push origin --tags`).
