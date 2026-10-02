#!/usr/bin/env bash

/setuid.sh && su -m dashcam /blackvuesync.sh
status=$?

if [[ -n $RUN_ONCE ]]; then
    exit "$status"
fi

exec crond -f
