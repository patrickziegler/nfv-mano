FROM python:3.7.4-alpine3.10

COPY requirements.txt /tmp/requirements.txt

RUN apk add --no-cache --virtual .deps \
    gcc musl-dev linux-headers && \
    pip install -r /tmp/requirements.txt && \
    apk del .deps

WORKDIR /usr/src/app

COPY app /usr/src/app

ENTRYPOINT ["python", "echo.py"]

CMD ["--raw"]
