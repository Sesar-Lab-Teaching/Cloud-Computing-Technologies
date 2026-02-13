# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}

RUN <<EOF
    apt-get update
    apt-get install -y jq
    pip install pip-tools
EOF

WORKDIR /app

COPY ./requirements.in /app/requirements.in
RUN pip-compile requirements.in && pip-sync

COPY . /app

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD test "$(curl -f -s http://localhost/health | jq -r '.ok')" = "true" || exit 1

ENTRYPOINT [ "flask", "--app", "main.py", "run", "--port=80", "--host=0.0.0.0" ]
