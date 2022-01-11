FROM alpine:3.15.0
LABEL maintainer="Alessandro Colomba https://github.com/acolomba"

RUN apk add --update bash python3 shadow tzdata \
    && rm -rf /var/cache/apk/* \
    && useradd -UMr dashcam

COPY COPYING /
COPY setuid.sh /setuid.sh
COPY entrypoint.sh /entrypoint.sh
COPY crontab /var/spool/cron/crontabs/dashcam

ENV ADDRESS="" \
    PUID="" \
    PGID="" \
    KEEP="" \
    GROUPING="" \
    PRIORITY="" \
    MAX_USED_DISK="" \
    TIMEOUT="" \
    VERBOSE=0 \
    QUIET="" \
    CRON=1 \
    DRY_RUN="" \
    RUN_ONCE=""

COPY --chown=dashcam blackvuesync.sh /blackvuesync.sh
RUN chmod +x /blackvuesync.sh

COPY --chown=dashcam blackvuesync.py /blackvuesync.py

ENTRYPOINT [ "/entrypoint.sh"]
