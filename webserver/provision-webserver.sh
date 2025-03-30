#!/bin/bash
apt update

add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.11 python3.11-venv python3.11-dev default-libmysqlclient-dev build-essential pkg-config jq

curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

python3.11 -m venv venv

source venv/bin/activate

curl -O https://raw.githubusercontent.com/Sesar-Lab-Teaching/Cloud-Computing-Technologies/511f3e72eb419d21cc28a09ef7896d54f5526eba/ovirt-demo-single-vm/requirements.txt

pip install -r requirements.txt
    
curl -O https://raw.githubusercontent.com/Sesar-Lab-Teaching/Cloud-Computing-Technologies/511f3e72eb419d21cc28a09ef7896d54f5526eba/ovirt-demo-single-vm/main.py

curl -O http://169.254.169.254/openstack/latest/meta_data.json
DB_IP_ADDRESS=$(jq -r .meta.db_ip meta_data.json)

echo "MYSQL_HOST=$DB_IP_ADDRESS
MYSQL_ROOT_PASSWORD=root
MYSQL_USER=cct
MYSQL_PASSWORD=cct-secret
MYSQL_DATABASE=cct
MYSQL_PORT=3306" > .env
    
flask --app main.py run --host=0.0.0.0 &
