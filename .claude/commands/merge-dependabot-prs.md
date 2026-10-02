---
description: Drive every open Dependabot PR to main, one at a time -- sync from main via GitHub, wait for its checks (fixing failures until green), squash-merge, wait for CI on main, then move to the next PR. Invoke manually.
argument-hint: "[PR number] (defaults to every open Dependabot PR, oldest first)"
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Grep, Glob, Agent
---

# Merge Dependabot PRs

Land the routine dependency-bump PRs Dependabot opens against this repo, one at a time, without a human doing the sync/wait/fix/merge loop by hand. Each PR goes through the same four phases before moving to the next.

## Phase 0 -- Build the queue

`gh pr list --search "author:app/dependabot" --state open --json number,title,headRefName,isDraft`.

`$ARGUMENTS`, if it names a PR number, restricts the queue to that one PR; otherwise process every open Dependabot PR, lowest PR number (oldest) first. Skip drafts. If the queue is empty, say so and stop.

Re-derive this list at the start of every iteration, not just once -- merging one PR can cause Dependabot or GitHub to close, rebase, or update others (e.g. two PRs touching the same lockfile), and a stale in-memory list can point at a PR that no longer needs handling.

## Phase 1 -- Sync from main (GitHub-side)

`gh pr update-branch <PR#>`. This merges `main` into the PR branch server-side and is a no-op if already up to date. Never pass `--rebase` -- this project's convention is merge, not rebase, and rewriting history on a bot-owned branch fights Dependabot's own next push. If it reports a conflict, `gh pr checkout <PR#>`, `git merge main` locally, resolve, push -- still no rebase.

## Phase 2 -- Wait for checks; fix on failure

1. Run `gh pr checks <PR#> --watch` to wait until all checks complete. Then run `gh pr checks <PR#> --json name,bucket,workflow,link`, even if the watch command reports failed checks.
2. If everything is `pass` or `skipping` (SonarCloud is expected to skip on Dependabot PRs -- no secrets access -- that's not a failure), go to Phase 3.
3. On any `fail`:
   - `gh pr checkout <PR#>`.
   - Find the failing run (`gh run list --branch <headRefName> --limit 5`, or the check's `link`) and read it: `gh run view <run-id> --log-failed`.
   - Diagnose the real cause -- usually the bump changed an API, a type, or tripped a lint rule. Fix the code, not the pin: don't quietly hold the dependency back to dodge the failure. If a genuine fix isn't mechanical, stop and report this PR instead of merging a workaround.
   - Before committing: `scripts/check.sh`, then `pre-commit run --all-files` -- fix, restage, re-run until clean. Never `--no-verify`.
   - Commit (Conventional Commits) and push to the PR branch.
   - Back to step 1.
4. Cap at 4 fix rounds. If a round doesn't shrink the failing-check count, or a fix reappears, stop, leave this PR unmerged, and move to the next one in the queue.

For a nontrivial fix, delegate the diagnose-and-fix work to a subagent (Task tool) so its transcript doesn't balloon this orchestrating conversation across a multi-PR run.

## Phase 3 -- Squash-merge

`gh pr merge <PR#> --squash --delete-branch`. This repo only allows squash merges and doesn't auto-delete branches on merge (`delete_branch_on_merge: false`) -- `--delete-branch` cleans up; Dependabot recreates the branch fresh on its next check-in. Capture the merge commit SHA (`gh pr view <PR#> --json mergeCommit`).

## Phase 4 -- Wait for CI on main

`git checkout main && git pull`. Then `gh run list --commit <merge-sha> --json databaseId,workflowName,conclusion,status` and `gh run watch <id> --exit-status` on each run until all complete.

If anything on main fails after the merge, stop the whole run and report -- don't merge the next PR on top of a red main. A post-merge failure (versus a pre-merge PR-branch failure in Phase 2) means something interacted unexpectedly and needs a closer look before continuing.

## Loop

Back to Phase 0. Continue until the queue is empty or a Phase 4 failure stops the run.

## Guards

- **Autonomous but bounded.** No stopping to ask per PR -- that's the point. The fix-round cap and the stop-on-red-main rule are the real safety net, same posture as `/babysit-pr`.
- **Never bypass hooks or checks.** No `--no-verify`, no disabling a check, no won't-fix flip to force a merge through.
- **Fix the code, not the pin.** A bump's whole point is to land; don't revert the version change to make CI pass.
- **Never rebase, never rewrite history.** Sync and conflict resolution are always a merge.
- **Stop on red main.** One Phase 4 failure halts the run rather than compounding it.

## Finish

Report per PR: merged / parked-with-reason, what fixes were needed (if any), and the final state of main's CI. Name anything left unmerged and why.
