#!/usr/bin/env bash
set -euo pipefail

args=("${ADDRESS}" --destination /recordings)

# keep option if KEEP set
[[ -n "${KEEP:-}" ]] && args+=(--keep "$KEEP")

# grouping option if GROUPING set
[[ -n "${GROUPING:-}" ]] && args+=(--grouping "$GROUPING")

# download priority option if PRIORITY set
[[ -n "${PRIORITY:-}" ]] && args+=(--priority "$PRIORITY")

# disk usage option if MAX_USED_DISK set
[[ -n "${MAX_USED_DISK:-}" ]] && args+=(--max-used-disk "$MAX_USED_DISK")

# timeout if TIMEOUT set
[[ -n "${TIMEOUT:-}" ]] && args+=(--timeout "$TIMEOUT")

# as many verbose options as the value in VERBOSE
if [[ -n "${VERBOSE:-}" && "$VERBOSE" -gt 0 ]]; then
    for _ in $(seq 1 "$VERBOSE"); do args+=(--verbose); done
fi

# quiet option if QUIET set to anything
[[ -n "${QUIET:-}" ]] && args+=(--quiet)

# cron option if CRON set to anything
[[ -n "${CRON:-}" ]] && args+=(--cron)

# dry-run option if DRY_RUN set to anything
[[ -n "${DRY_RUN:-}" ]] && args+=(--dry-run)

# retry-failed-after option if RETRY_FAILED_AFTER set
[[ -n "${RETRY_FAILED_AFTER:-}" ]] && args+=(--retry-failed-after "$RETRY_FAILED_AFTER")

# skip-metadata option if SKIP_METADATA set
[[ -n "${SKIP_METADATA:-}" ]] && args+=(--skip-metadata "$SKIP_METADATA")

# include option if INCLUDE set
[[ -n "${INCLUDE:-}" ]] && args+=(--include "$INCLUDE")

# exclude option if EXCLUDE set
[[ -n "${EXCLUDE:-}" ]] && args+=(--exclude "$EXCLUDE")

# session key option if AFFINITY_KEY set
[[ -n "${AFFINITY_KEY:-}" ]] && args+=(--affinity-key "$AFFINITY_KEY")

/blackvuesync.py "${args[@]}"
