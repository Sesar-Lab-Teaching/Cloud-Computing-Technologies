#!/bin/bash
apt-get update

# TODO: verify whether it is possible to integrate venv
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.11

apt -y install jq
apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config python3-pip

python3.11 -m venv venv

pip install -r <(curl https://raw.githubusercontent.com/Sesar-Lab-Teaching/Cloud-Computing-Technologies/ 511f3e72eb419d21cc28a09ef7896d54f5526eba/ovirt-demo-single-vm/requirements.txt)

# some dependencies might be modified
# pip install -r <(curl https://raw.githubusercontent.com/Sesar-Lab-Teaching/Cloud-Computing-Technologies/511f3e72eb419d21cc28a09ef7896d54f5526eba/ovirt-demo-single-vm/requirements.txt | \
#     sed -e 's/mysqlclient==2.2.4/mysqlclient==2.1.1/g' -e 's/Flask-MySQLdb==2.0.0/Flask-MySQLdb==1.0.1/g')
    
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
