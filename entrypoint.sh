#!/usr/bin/env bash

/setuid.sh \
&& su -m dashcam /blackvuesync.sh \
&& [[ -z $RUN_ONCE ]] \
&& crond -f
