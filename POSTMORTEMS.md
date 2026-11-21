# Postmortems

Each mistake gets an entry with what happened, the cause label, and the process fix. The process fix (docs, specs, tests or validations) is made before the code fix.

Cause labels: spec gap, doc gap, test gap, validation gap, process gap, environment, cost or turn cap.

## Template

### YYYY-MM-DD short title

- What happened:
- Cause:
- Process fix:
- Code fix:

### 2026-11-21 kit uploaded flat

- What happened: The setup kit reached the repo as loose files in the root, with empty `download*` placeholders, so none of the paths in `CLAUDE.md` or `checks/protected_paths.txt` existed. The kit's zip held the correct layout.
- Cause: process gap. Nothing verified that the layout in the docs matched the repo.
- Process fix: `tests/test_layout.py` now fails if a required file or directory is missing or if stray files sit in the root.
- Code fix: Unpacked the zip into the real layout and removed the byte-identical flat copies.
