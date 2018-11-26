FROM alpine:3.6
LABEL maintainer="Alessandro Colomba https://github.com/acolomba"

ADD blackvuesync.sh /blackvuesync.sh
ADD blackvuesync.py /blackvuesync.py
ADD crontab /var/spool/cron/crontabs/root

ENV ADDRESS="" \
    KEEP="" \
    MAX_USED_DISK="" \
    VERBOSE=0 \
    QUIET="" \
    CRON=1 \
    DRY_RUN="" \
    RUN_ONCE=""

RUN apk add --update python3 bash tzdata && \
    rm -rf /var/cache/apk/* && \
    chmod +x /blackvuesync.sh

CMD /blackvuesync.sh && \
    test -z "$RUN_ONCE" && crond -f
