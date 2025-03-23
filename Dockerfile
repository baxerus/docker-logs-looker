FROM docker

LABEL org.opencontainers.image.url=https://github.com/baxerus/docker-logs-looker

RUN apk add --no-cache \
    python3 \
    py3-pip \
&& pip3 install --root-user-action=ignore --break-system-packages ansi2html

HEALTHCHECK --interval=60s --timeout=5s --retries=3 CMD wget -q http://localhost:8080/?HEALTHCHECK -O /dev/null

STOPSIGNAL SIGINT

ADD docker-logs-looker.py /docker-logs-looker.py

ENTRYPOINT ["python3", "/docker-logs-looker.py"]
