#!/usr/bin/env bash
set -euo pipefail

set -- "${ADDRESS}" --destination /recordings

# keep option if KEEP set
[ -n "${KEEP:-}" ] && set -- "$@" --keep "$KEEP"

# grouping option if GROUPING set
[ -n "${GROUPING:-}" ] && set -- "$@" --grouping "$GROUPING"

# download priority option if PRIORITY set
[ -n "${PRIORITY:-}" ] && set -- "$@" --priority "$PRIORITY"

# disk usage option if MAX_USED_DISK set
[ -n "${MAX_USED_DISK:-}" ] && set -- "$@" --max-used-disk "$MAX_USED_DISK"

# timeout if TIMEOUT set
[ -n "${TIMEOUT:-}" ] && set -- "$@" --timeout "$TIMEOUT"

# as many verbose options as the value in VERBOSE
if [ -n "${VERBOSE:-}" ] && [ "$VERBOSE" -gt 0 ]; then
    i=0; while [ "$i" -lt "$VERBOSE" ]; do set -- "$@" --verbose; i=$((i + 1)); done
fi

# quiet option if QUIET set to anything
[ -n "${QUIET:-}" ] && set -- "$@" --quiet

# cron option if CRON set to anything
[ -n "${CRON:-}" ] && set -- "$@" --cron

# dry-run option if DRY_RUN set to anything
[ -n "${DRY_RUN:-}" ] && set -- "$@" --dry-run

# retry-failed-after option if RETRY_FAILED_AFTER set
[ -n "${RETRY_FAILED_AFTER:-}" ] && set -- "$@" --retry-failed-after "$RETRY_FAILED_AFTER"

# skip-metadata option if SKIP_METADATA set
[ -n "${SKIP_METADATA:-}" ] && set -- "$@" --skip-metadata "$SKIP_METADATA"

# include option if INCLUDE set
[ -n "${INCLUDE:-}" ] && set -- "$@" --include "$INCLUDE"

# exclude option if EXCLUDE set
[ -n "${EXCLUDE:-}" ] && set -- "$@" --exclude "$EXCLUDE"

# session key option if AFFINITY_KEY set
[ -n "${AFFINITY_KEY:-}" ] && set -- "$@" --affinity-key "$AFFINITY_KEY"

/blackvuesync.py "$@"
