---
paths:
  - "CHANGELOG.md"
---

# CHANGELOG entries

One entry per pull request, written for the reader, 40 words or fewer per bullet.

## Before you write

Load the `simple-english` skill in Plain mode and the `humanizer` skill. Apply both to every line you add or change, then run their self-checks. In particular: no `-ing` clause hanging off a comma, no `should`, `would`, `could`, or `may`, no semicolon, and no dash between two statements.

## Shape

- Put the entry under `## [Unreleased]`, newest first. A release moves the section under `## [x.y.z] - YYYY-MM-DD`.
- One top-level bullet per pull request. Its last token is the PR number in parentheses, after the final period: `... at spawn. (#138)`.
- One change: one line. Several changes in one PR: a top line that stands on its own, then one detail per sub-bullet, indented two spaces. No third level. The PR number stays on the top line only.
- A PR of many small, unrelated fixes gets one line that names the areas.
- A PR with no user-visible change gets one brief, general line that names the area: `Internal: the test suite now runs in a hermetic home directory. (#196)`. Dependency bumps are the exception and get no entry.

## Wording

- Lead with what changed for the reader, not with the mechanism.
- Write one sentence. Add a second only if the reader must do something. Keep each sentence to 25 words or fewer.
- Use active voice and a simple tense. Name the symptom, not the investigation.
- Keep code, flags, file names, and output tokens verbatim, in backticks.
- Put rationale, internals, and rejected alternatives in the commit body or the PR, never here.

## Credits and references

- Thank everyone who is not the maintainer. The clause sits before the PR number.
  - PR author: `Thanks to @contributor. (#152)`
  - Issue reporter: `Thanks to @reporter, who reported #179. (#188)`
  - Feature request: `Thanks to @requester, who requested this in #21. (#60)`
  - Both: `Thanks to @contributor, who reported #140 and wrote the fix. (#141)`
- Every closed issue appears exactly once, on the entry for the PR that closed it. The PR body's `Closes #N` line or the closing comment names that PR.
- Contributors add their own credit line.

## Do not

- Do not explain what the old code did internally.
- Do not list what remains unimplemented. That belongs in an issue.
- Do not spread one change across several bullets, and do not split one PR across several top-level entries.
- Do not commit without `pre-commit run --files CHANGELOG.md` (mdformat and markdownlint).

## Examples

Too long, at 86 words:

> The `retryDelay` option is now read as seconds, which is what the README documents and what users write. The client consumed the bare number as milliseconds, so a `retryDelay: 5` -- five seconds by the documentation -- retried after 5 ms and used up every attempt before the server could recover. Every configured delay was a thousand times shorter than written, and a request that failed that way reported only the last error, with nothing to say the retries were wasted. Thanks to @contributor for the contribution (#42).

Better, at 33 words, with the PR's other changes nested under it:

> - `retryDelay` now reads as seconds, as the README says. It read as milliseconds before, so every retry fired a thousand times early and gave up before the server recovered. Thanks to @contributor. (#42)
>   - The delay now doubles after each attempt, up to 60 s.
>   - A `retryDelay` that is not a number falls back to 1 s instead of failing at startup.
