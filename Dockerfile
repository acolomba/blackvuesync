FROM alpine:3.9
LABEL maintainer="Alessandro Colomba https://github.com/acolomba"

ADD blackvuesync.sh /blackvuesync.sh
ADD blackvuesync.py /blackvuesync.py
ADD setuid.sh /setuid.sh
ADD crontab /var/spool/cron/crontabs/dashcam

ENV ADDRESS="" \
    PUID="" \
    PGID="" \
    KEEP="" \
    MAX_USED_DISK="" \
    VERBOSE=0 \
    QUIET="" \
    CRON=1 \
    DRY_RUN="" \
    RUN_ONCE=""

RUN apk add --update bash python3 shadow tzdata \
    && rm -rf /var/cache/apk/* \
    && useradd -UMr dashcam \
    && chmod +x /blackvuesync.sh

CMD /setuid.sh && su -m dashcam /blackvuesync.sh \
    && test -z "$RUN_ONCE" && crond -f
