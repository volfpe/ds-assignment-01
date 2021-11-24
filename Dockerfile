FROM ghcr.io/maxotta/kiv-ds-docker:v0.9.1

RUN yum -q -y install python3
RUN pip3 install fastapi uvicorn requests

COPY src/ .

HEALTHCHECK --interval=5s --start-period=120s \
    CMD /usr/bin/python3 healthcheck.py

CMD /usr/bin/python3 node.py