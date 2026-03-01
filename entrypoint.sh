#!/usr/bin/env bash

/setuid.sh && su -m dashcam -c /blackvuesync.sh
bvs_exit=$?

# runs cron daemon if RUN_ONCE not set
if [[ -z ${RUN_ONCE:-} ]]; then
    exec crond -f
fi

exit $bvs_exit
