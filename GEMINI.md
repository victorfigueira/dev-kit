# Antigravity Workspace Guidelines for dev-kit

## Language & Documentation Integrity
- All documentation, code comments, commit messages, and changelog entries must be written strictly in **English**, regardless of the conversation language with the user.

## Versioning & Release Conventions
Every functional change, feature, or bug fix must follow the project's established semantic versioning standard (`MAJOR.MINOR.PATCH`):

### 1. Version Semantics (`MAJOR.MINOR.PATCH`)

| Level | When to Increment | Project Impact | Practical Examples |
| :---: | :--- | :--- | :--- |
| **`MAJOR`**<br>`(X.0.0)` | **Breaking Changes**<br>• Breaking modifications to agent protocols or output formats.<br>• Structural directory reorganization.<br>• Incompatible changes to `PLAN.md` or `PULL_REQUEST.md` schemas. | Requires downstream client projects to update their workflows or configuration. | • Major rewrite of orchestrator dispatch model.<br>• Incompatible changes in `test_runner.py` CLI interface. |
| **`MINOR`**<br>`(x.Y.0)` | **New Backwards-Compatible Capabilities**<br>• New specialized developer roles (e.g. `devops.md`, `security-engineer.md`).<br>• New environment adapters (e.g. Copilot, Windsurf).<br>• New tools, CLI commands, or stack detectors. | Expands capabilities without breaking existing projects or commands. | • Adding a new `database-engineer` or `cloud-infra` role.<br>• Adding automated PR generation tools. |
| **`PATCH`**<br>`(x.y.Z)` | **Bug Fixes, Refinements & Documentation**<br>• Bug fixes in scripts or templates.<br>• Prompt refinements to prevent unwanted agent behavior.<br>• Documentation updates, diagrams, and README improvements. | Zero risk; seamless improvements for existing users. | • Fixing regex matching in `test_runner.py`.<br>• Updating `README.md` diagrams or guides. |

### 2. Required Synchronized File Updates
Whenever a version is bumped, the following 5 files must be updated together in the same commit:
1. `VERSION`: Contains the raw version string (e.g. `0.1.0`).
2. `CHANGELOG.md`: Add a new release section at the top formatted as:
   ```markdown
   ## X.Y.Z – DD/MM/YYYY
   - Bullet points explaining the changes clearly and concisely.
   ```
3. `README.md`: Update the current version declaration on line 3:
   ```markdown
   Current version: **X.Y.Z** (see `CHANGELOG.md`).
   ```
   and update example pins like `DEV_KIT_REF=vX.Y.Z`.
4. `RUN.md`: Update version references in template examples.
5. `docs/GUIDE.md`: Update version references in installation pins if applicable.

### 3. Git Commit & Tagging Protocol
- **Commit format**: `vX.Y.Z: <concise description in English>` (e.g. `v0.1.0: initial release of autonomous dev-kit`).
- **Git Tag**: Tag the release with an annotated tag `vX.Y.Z`:
  ```bash
  git tag -a vX.Y.Z -m "vX.Y.Z: <summary>"
  ```
- **Push to Remote**: Always push commits and tags together:
  ```bash
  git push origin main && git push origin --tags
  ```
