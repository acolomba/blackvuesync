#!/usr/bin/env bash

case "${CAMERA_API-auto}" in
    auto|legacy|modern) ;;
    *) echo "Invalid CAMERA_API: expected auto, legacy or modern" >&2; exit 2 ;;
esac

/setuid.sh && su -m dashcam /blackvuesync.sh
status=$?

if [[ -n $RUN_ONCE ]]; then
    exit "$status"
fi

exec crond -f
