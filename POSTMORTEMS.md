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

### 2026-11-24 annotation format check accepted a float version

- What happened: `annotations_from_json` compared `format` with `!=` and excluded `bool` separately. In Python `1.0 == 1`, so `{"format": 1.0}` was accepted, against the strict-reading rule in `Docs/overview.md`. The architect caught it in diff review.
- Cause: test gap. The wrong-type cases were tested for annotation fields but not for the top-level `format`, and the two checks were written two different ways.
- Process fix: the format test now covers `2, 1.0, True, "1", None`. The rule is now written down here: any strict check of a JSON number uses an exact type test (`type(x) is int`), never `==` or `isinstance`, because `bool` is an `int` and `1.0 == 1`.
- Code fix: the format check uses `type(version) is not int`, matching the per-field check.
