FROM docker

RUN apk add --no-cache \
    python3 \
    py3-pip \
&& pip3 install --break-system-packages ansi2html

ADD docker-logs-looker.py /docker-logs-looker.py

HEALTHCHECK --interval=60s --timeout=5s --retries=3 CMD wget -q http://127.0.0.1:8080 -O /dev/null

STOPSIGNAL SIGINT

ENTRYPOINT ["python3", "/docker-logs-looker.py"]
