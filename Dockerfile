FROM docker

RUN apk add --no-cache \
    python3 \
    py3-pip \
&& pip3 install --break-system-packages ansi2html

ADD docker-logs-looker.py /docker-logs-looker.py

STOPSIGNAL SIGINT

ENTRYPOINT ["python3", "/docker-logs-looker.py"]
