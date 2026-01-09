#!/usr/bin/env bash

/setuid.sh && su -m dashcam /blackvuesync.sh

# runs cron daemon if RUN_ONCE not set
if [[ -z $RUN_ONCE ]]; then
    exec crond -f
fi
