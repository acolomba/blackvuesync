---
name: pr-review-toolkit
description: Use when reviewing a pull request or local diff for comments, tests, error handling, type design, code quality, and simplification concerns.
---

# PR Review Toolkit (Codex Port)

## Overview

This skill ports Anthropic's `pr-review-toolkit` plugin into a Codex-usable project skill.
Use it to run focused or comprehensive PR review passes across six areas:

- comments
- tests
- errors
- types
- code
- simplify

## How to Use

1. Identify scope:
- unstaged local changes: `git diff`
- staged changes: `git diff --cached`
- branch delta: `git diff <base>...HEAD`

2. Choose aspects:
- all aspects: `all`
- targeted aspects: any of `comments tests errors types code simplify`

3. Run reviews:
- sequential review: run one aspect at a time (default)
- parallel review: run independent aspects together via `multi_tool_use.parallel`

4. Report findings by severity with file references.

## Aspect Mapping

- `comments` -> `agents/comment-analyzer.md`
- `tests` -> `agents/pr-test-analyzer.md`
- `errors` -> `agents/silent-failure-hunter.md`
- `types` -> `agents/type-design-analyzer.md`
- `code` -> `agents/code-reviewer.md`
- `simplify` -> `agents/code-simplifier.md`

## Recommended Order

1. `code`
2. `errors`
3. `tests`
4. `types` (when types changed)
5. `comments` (when docs/comments changed)
6. `simplify` (after functional quality checks)

## Notes

- Source copied from `anthropics/claude-code` plugin and adapted for Codex workflows.
- Claude-specific `/plugin` and `/command` syntax was translated to skill usage.
