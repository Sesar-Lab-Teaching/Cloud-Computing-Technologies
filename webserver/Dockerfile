# syntax=docker/dockerfile:1

FROM python:3.12

RUN <<EOF
    apt-get update
    apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config jq
EOF

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD test "$(curl -f -s http://localhost/health | jq -r '.ok')" = "true" || exit 1

ENTRYPOINT [ "flask", "--app", "main.py", "run", "--port=80", "--host=0.0.0.0" ]
