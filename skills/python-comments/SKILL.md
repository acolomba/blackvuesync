---
name: python-comments
description: Comment, docstring, and test-name policy for Python -- lowercase third-person prose that describes what and why, cites durable spec IDs, never planning artifacts. Apply when writing or changing comments, docstrings, or test names in any .py file.
---

# Python comment policy

Comments, docstrings, and test names describe **what the code does** and, when non-obvious, **why**. They do not record which GSD milestone, phase, plan, wave, or task produced the code. Git history owns process history.

## Form

- Docstrings and comments are lowercase: `"""returns the order total."""`, `# retries once on a timeout`. `TODO` stays uppercase, and names keep their casing: `# reads pyproject.toml`, `# OrderStore raises on a missing id`.
- Write in the third person, because a comment describes: `"""installs the hooks."""`, not `"""install the hooks."""`. Avoid the imperative.
- Keep comments concise and non-obvious. Do not explain what every Python programmer knows.

## Forbidden in comments, docstrings, and test names

- `Phase NN`, `Plan NN`, `Plan NN-NN`, `Wave N`, `Task N` references to GSD planning steps.

- `milestone vX.Y`, `vX.Y milestone`, and UAT-decision parentheticals such as `(v1.12 milestone UAT decision 2026-06-11)`.

- Parentheticals like `(Phase 56 review)`, `(Phase 54 frozen)`, `(Phase 55 Plan 01)`.

- Bare `Pitfall N` and `Pattern N` references (where N is a single digit) that cite per-phase RESEARCH.md numbered hazard lists. Per-phase numbering restarts per RESEARCH document, so the same `Pitfall N` token means different things in different files, the earliest source docs no longer exist, and the underlying hazards are gate-enforced by tests. Drop the token and let the surrounding comment's rationale (or surviving requirement/decision IDs) carry the anchor. Phase-qualified forms (`Pitfall NN-N`, `RESEARCH Pitfall N`) are already covered by the planning-artifact clause above.

- Any other phrasing whose only purpose is to record which planning artifact authored the line.

- Narration of code that no longer exists. A comment describes the code as it stands, not the shape it replaced. Git history owns the diff, so drop `the former X`, `X used to ...`, `X no longer ...`, `Pre-fix, X ...`, `replacing the former X`, `byte-identical to the former X`, and `superseding the former X`.

  Where the removed shape carried the rationale, restate the rationale as a present-tense fact about the current code. A claim of the form "this is byte-identical to what came before" is not a fact about the current code at all -- the gate that pins the bytes is, so name the gate or say nothing.

Forbidden -> Allowed:

```text
# the D-03 stamps map `failed` rows to `error`, exactly the rows the former
# status-based counter matched, so the count is byte-identical.
```

becomes

```text
# the D-03 stamps map `failed` rows to `error`.
```

```text
# ATTR-09: the former "not in manifest" lied that the plugin was gone from
# the manifest; "source mismatch" is the truthful existing member.
```

becomes

```text
# ATTR-09: a content/ownership mismatch is not a manifest absence, so the
# truthful member is "source mismatch" and not "not in manifest".
```

## Prose

- One idea per sentence. Short sentences, active voice, present tense.
- Say what the code does, not how good it is: no `robust`, `seamless`, `comprehensive`, `crucial`.
- No `not X but Y` or `not just X, it's Y` framing. State Y.
- No padding a list to three items. List what exists.
- No hedges (`essentially`, `simply`, `basically`) and no chatbot register (`note that`, `it's worth noting`).
- Use the domain word the code uses. Define a term at first use only when a reader of this file could not infer it.

## Allowed (and encouraged) as traceability anchors

- Decision IDs: `D-01`, `D-21`, `D-54-01`, `D-15-11`, `D-17.1-01`, etc.
- Requirement and finding IDs such as `REQ-NN`, `UAT-NN`, `SC-N`, `NFR-N`. In a test name they read in snake case: `test_prl_10_...`.
- GitHub issue/PR references like `#2916`.

These anchors link the code to a specification row, not to a planning step.

## Domain language is not GSD history

Words like `phase` that name domain concepts in the code itself are **not** GSD references and must be preserved unchanged. Examples:

- A two-phase commit narration (`# phase 2: removes old target files ...`).
- Fixture strings such as `"update phase 3 failed"`.
- Version pins inside URLs such as `#v1.0`.

## Examples

Forbidden -> Allowed:

```text
# Phase 56 Plan 01 Task 2 -- shared edge-handler helpers ...
```

becomes

```text
# shared edge-handler helpers ...
```

```text
# WB-01 / Phase 56 Plan 02: extracts `--local` BEFORE positional parsing
```

becomes

```text
# WB-01: extracts `--local` BEFORE positional parsing
```

```text
def test_phase_8_prl_10_replace_prepared_skills_can_roll_back() -> None:
```

becomes

```text
def test_prl_10_replace_prepared_skills_can_roll_back() -> None:
```

Forbidden -> Allowed:

```text
# WB-01 / Pitfall 2: target-path selection happens ONCE
```

becomes

```text
# WB-01: target-path selection happens ONCE
```

```text
def test_pitfall_9_load_state_on_missing_state_json_returns_default_state() -> None:
```

becomes

```text
def test_load_state_on_missing_state_json_returns_default_state() -> None:
```
