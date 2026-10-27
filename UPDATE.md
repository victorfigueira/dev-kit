# Updating dev-kit from the agent chat

Follow these steps when the user asks to check for or install a kit update. When `RUN.md` calls these steps before a task, "stop" means stop the update check and carry on with the task. Never touch `dev/`.

Source: `https://raw.githubusercontent.com/victorfigueira/dev-kit/main/`.

1. **Check.** Run `python3 dev-kit/tools/updater.py check --json`. It reports the installed version (`current_version`), the latest one (`latest_version`), whether an update exists (`update_available`), whether the major version changes (`major_change`) and the changelog entries newer than the installed version (`changelog`). If Python is missing, read `dev-kit/VERSION` and `curl -fsSL <source>VERSION` instead, and fetch `<source>CHANGELOG.md` for step 3.
2. **Compare.** If `offline` is true, tell the user the check could not reach GitHub and stop. If `update_available` is false, say "dev-kit <version> is up to date" and stop.
3. **Show what is new.** Summarise the `changelog` entries in the user's language (maximum 10 lines). If `major_change` is true, say so: a major version can change the workflow or the files in `dev/`.
4. **Ask for confirmation** before installing. Do not continue without a clear yes.
5. **Install.** From the project root, run `python3 dev-kit/tools/updater.py update`. It replaces the kit files in `dev-kit/`, refreshes the kit's own adapters and leaves `dev/` untouched. It refuses to run inside the dev-kit source repository itself.
6. **Report** in at most 5 lines: old and new version, and whether the IDE window needs reloading (yes if the installer printed any installed adapters).
