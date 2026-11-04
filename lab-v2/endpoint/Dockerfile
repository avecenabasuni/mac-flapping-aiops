FROM python:3.12-alpine

RUN apk add --no-cache bash iproute2 iputils
COPY endpoint/send_frame.py /opt/lab/send_frame.py

CMD ["sleep", "infinity"]
