#!/bin/bash

apt-get update
apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config

python -m venv venv

source venv/bin/activate

pip install -r requirements.txt

flask --app main.py run --host=0.0.0.0 &