#!/usr/bin/env bash

/setuid.sh && su -m dashcam /blackvuesync.sh
status=$?

# exits with the sync status if RUN_ONCE set, otherwise runs the cron daemon
if [[ -n $RUN_ONCE ]]; then
    exit "$status"
fi

exec crond -f
