# Specs

Specs are Patrick's. Each file describes one piece of work: what it should do, who it is for, how to tell it works, and what is out of scope.

## The rule

Files whose names start with `draft-` are ignored by the night loop. Patrick promotes a spec by renaming it, for example from `draft-initial-build.md` to `initial-build.md`. Only promoted specs are picked up.

Agents never write a finished spec on Patrick's behalf. An agent may add questions to the open questions section of a draft, but the decisions are Patrick's.

## Writing a spec

Copy `SPEC_TEMPLATE.md`. Specs can stay small because `Docs/` carries system knowledge. Describe the feature and its edge cases, and name an acceptance test with a known right answer wherever one exists.
