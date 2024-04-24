FROM python:3.11

RUN <<EOF
    apt-get update
    apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config
EOF

COPY . .

RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT [ "flask", "--app", "main.py", "run", "--host=0.0.0.0" ]
