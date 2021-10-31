FROM ghcr.io/maxotta/kiv-ds-docker:v0.9.1

RUN yum -q -y install python3
RUN pip3 install fastapi uvicorn requests

COPY node.py .

CMD /usr/bin/python3 node.py
#CMD /bin/bash -c 'sleep infinity'