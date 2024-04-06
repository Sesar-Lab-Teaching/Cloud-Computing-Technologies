#!/bin/bash

wget https://dev.mysql.com/get/mysql-apt-config_0.8.29-1_all.deb
apt install ./mysql-apt-config_0.8.29-1_all.deb

apt update
apt install mysql-server
systemctl enable mysql
