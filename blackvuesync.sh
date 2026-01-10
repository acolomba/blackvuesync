#!/usr/bin/env bash
# shellcheck disable=SC2086
set -euo pipefail

# keep option set if KEEP set
keep=${KEEP:+--keep $KEEP}

# grouping option if GROUPING set
grouping=${GROUPING:+--grouping $GROUPING}

# download priority option set if PRIORITY set
priority=${PRIORITY:+--priority $PRIORITY}

# disk usage option set if USAGE set
disk_usage=${MAX_USED_DISK:+--max-used-disk $MAX_USED_DISK}

# timeout set if TIMEOUT set
timeout=${TIMEOUT:+--timeout $TIMEOUT}

# as many verbose options as the value in VERBOSE
verbose=${VERBOSE:+$(if [[ $VERBOSE -gt 0 ]]; then for _ in $(seq 1 $VERBOSE); do echo --verbose; done; fi)}

# quiet option if QUIET set to anything
quiet="${QUIET:+--quiet}"

# cron option if CRON set to anything
cron="${CRON:+--cron}"

# dry-run option if DRY_RUN set to anything
dry_run="${DRY_RUN:+--dry-run}"

# session key option if AFFINITY_KEY set
affinity_key="${AFFINITY_KEY:+--affinity-key $AFFINITY_KEY}"

/blackvuesync.py ${ADDRESS} --destination /recordings ${keep} ${grouping} ${priority} ${disk_usage} ${timeout} ${verbose} \
    ${quiet} ${cron} ${dry_run} ${affinity_key}
