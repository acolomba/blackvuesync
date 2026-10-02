# Porting Metadata

- source repository: `https://github.com/anthropics/claude-code`
- source path: `plugins/pr-review-toolkit`
- source commit: `1718a574950cd8979b27b3e21f5e82760b10e8e0`
- extracted at (UTC): `2026-02-17T22:08:41Z`
- port target: project-local Codex skill at `.codex/skills/pr-review-toolkit`

## Port Notes

- retained original analyzer prompt files under `agents/`
- retained and adapted command flow in `commands/review-pr.md`
- added Codex skill entrypoint in `SKILL.md`
- translated Claude command syntax to Codex skill invocation examples
