#!/bin/bash

apt update
apt -y install mysql-server

mysql -u root <<- EOF
    CREATE DATABASE cct;
    CREATE USER 'cct'@'localhost' IDENTIFIED BY 'cct-secret';
    GRANT ALL PRIVILEGES ON cct.* TO 'cct'@'localhost';
    FLUSH PRIVILEGES;
EOF

curl -O https://raw.githubusercontent.com/Sesar-Lab-Teaching/Cloud-Computing-Technologies/511f3e72eb419d21cc28a09ef7896d54f5526eba/ovirt-demo-single-vm/seed.sql

mysql -u cct --password=cct-secret cct < seed.sql

sed -i 's/bind-address		= 127.0.0.1/bind-address		= 0.0.0.0/g' /etc/mysql/mysql.conf.d/mysqld.cnf
ufw allow 3306

systemctl restart mysql
