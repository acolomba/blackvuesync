---
description: "Comprehensive PR review using specialized analyzers"
argument-hint: "[review-aspects] [parallel]"
---

# Comprehensive PR Review

Run a comprehensive pull request or local diff review using multiple specialized analyzers, each focused on a specific quality dimension.

Review aspects: `comments tests errors types code simplify all`.

## Workflow

1. Determine scope:
- local unstaged diff: `git diff`
- staged diff: `git diff --cached`
- branch diff: `git diff <base>...HEAD`

2. Determine applicable aspects:
- always: `code`
- when tests changed: `tests`
- when docs/comments changed: `comments`
- when error paths changed: `errors`
- when type models changed: `types`
- final polish: `simplify`

3. Run analyzers:
- sequential by default
- use parallel only when aspects are independent

4. Aggregate and report:
- critical issues (must fix)
- important issues (should fix)
- suggestions (nice to have)
- strengths

## Usage Examples

Full review:
`pr-review-toolkit review-pr all`

Targeted review:
`pr-review-toolkit review-pr tests errors`

Parallel review:
`pr-review-toolkit review-pr all parallel`

## Output Shape

```markdown
# PR Review Summary

## Critical Issues (X found)
- [analyzer]: Issue description [file:line]

## Important Issues (X found)
- [analyzer]: Issue description [file:line]

## Suggestions (X found)
- [analyzer]: Suggestion [file:line]

## Strengths
- What is well done

## Recommended Action
1. Fix critical issues first
2. Address important issues
3. Consider suggestions
4. Re-run targeted review after fixes
```
