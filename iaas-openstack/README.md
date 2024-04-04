# Openstack Guide for single VM with Ovirt

---

### Sources:

- https://ubuntu.com/openstack/install#single-multi-large-cluster
- https://discourse.ubuntu.com/t/single-node-guided/35765
- https://docs.openstack.org/devstack/latest/guides/single-vm.html
- https://ubuntu.com/tutorials/install-openstack-on-your-workstation-and-launch-your-first-instance#2-install-openstack

---

## ⚠️⚠️⚠️Important ⚠️⚠️⚠️

When you create the VM for Openstack, read the [requirements](https://ubuntu.com/openstack/install)

---

There are multiple ways to install Openstack in a single node, we describe the procedure for both devstack and microstack.

## Install Devstack

Once the VM is ready, create a new user:

```
sudo useradd -s /bin/bash -d /opt/stack -m stack
sudo chmod +x /opt/stack
echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/stack
```

Everytime you need to operate with Openstack, login with this user (**TODO**: automate this step):

```
sudo -u stack -i
```

Then install the Openstack components. **Important**: make sure the master points to a stable release, otherwise clone a previous commit.

```
git clone https://git.openstack.org/openstack-dev/devstack

cd devstack

echo '[[local|localrc]]' > local.conf
echo "ADMIN_PASSWORD=openstackcct" >> local.conf
echo "DATABASE_PASSWORD=\$ADMIN_PASSWORD" >> local.conf
echo "RABBIT_PASSWORD=\$ADMIN_PASSWORD" >> local.conf
echo "SERVICE_PASSWORD=\$ADMIN_PASSWORD" >> local.conf
echo -e "\n## Neutron options" >> local.conf
echo "Q_ML2_PLUGIN_EXT_DRIVERS=dns,port_security,qos" >> local.conf
```

\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*
### Extra

The general guide suggests to use the config template in samples/local.conf, but the single-VM configuration does not need all of them, which is why we preferred to stick with the minimal configurationa
```
cp samples/local.conf local.conf

sed -i -E -e 's/ADMIN_PASSWORD=nomoresecret/ADMIN_PASSWORD=openstackcct/g' \
    -e 's/DATABASE_PASSWORD=.*$/DATABASE_PASSWORD=\$ADMIN_PASSWORD/g' \
    -e 's/RABBIT_PASSWORD=.*$/RABBIT_PASSWORD=\$ADMIN_PASSWORD/g' local.conf
```
\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*

Then you can start Openstack (requires 15 mins at least)

```
./stack.sh
```

### Uninstall Devstack

```
cd devstack
./clean.sh
# clean folders of devstack
```

## Install Microstack

```
sudo snap install openstack --channel 2023.1
sunbeam prepare-node-script | bash -x && newgrp snap_daemon
IP_ADDRESS=#... put the ip address detected by your virtual engine
sudo sed -i -e 's/127.0.1.1 openstackcct/$IP_ADDRESS openstackcct/g' /etc/hosts
sunbeam cluster bootstrap --accept-defaults
sunbeam configure --accept-defaults --openrc demo-openrc
# ... TODO
```

### To uninstall Microstack

```
sudo snap remove --purge microk8s 
sudo snap remove --purge juju 
sudo snap remove --purge openstack
sudo snap remove --purge openstack-hypervisor
sudo /usr/sbin/remove-juju-services
sudo rm -rf /var/lib/juju
rm -rf ~/.local/share/juju
rm -rf ~/snap/openstack
rm -rf ~/snap/openstack-hypervisor
rm -rf ~/snap/microstack/
rm -rf ~/snap/juju/
rm -rf ~/snap/microk8s/
sudo init 6
```

---

## Usage

From now on, always login with the "stack" user (`sudo -u stack -i`) to run Openstack commands.
you can access horizon (the Web UI Dashboard) from `http://172.20.28.108/dashboard/project`.

username: admin        # "demo", or any other user created

password: openstackcct

To access Openstack from the console, you first need to configure it with the right env variables:

```
# source devstack/openrc {username} {project_name}
source devstack/openrc admin admin
```

Every Openstack command has the form:

```
openstack {service_id} {operation} [-c column_to_show] [-f formatting_option]
```

For more information on the available services and operations, use the help command: `openstack help {service_id} [{operation}]

---

# Images with Glance

Each server needs an image, basically an OS that hosts the server. Glance is the Openstack service that manages these images. We can see the available ones with:

```
openstack image list
```

Since the only one available with devstack is cirrOS, we may beed to import a new image, like Ubuntu, but the image optimized for the cloud usage. First, download the image of the latest stable release (as of March 2024 is [22.04](https://cloud-images.ubuntu.com/jammy/current/)). The image format should be `.img`, for instance `jammy-server-cloudimg-amd64.img`:

```
openstack image create --min-disk 5 --min-ram 1024 --file path_to_img_file.img --public ubuntu-22.04LTS-server-cloudimg-amd64
```

The same can be done on the Horizon dashboard: *Compute* -> *Images* -> *Create Image*.

---

# Computing with Nova

To create a new server, you need:

 - An image (`openstack image list`)
 - A flavor, which describes the requirements of the server (`openstack flavor list`)
 - The network to which it should be attached (`openstack network list`)
 - The server instance id

To run a cirros server, connected to the private network with the minimum requirements:

```
openstack server create --image cirros-0.6.2-x86_64-disk --flavor 1 --network private testinstance1
```

To verify whether the instance is active, run `openstack server show testinstance1 -c status`. Other fields to check are `addresses`. 

We can also see logs from the server using

```
openstack console log show testinstance1
```

but we can also open a VNC connection with:

```
openstack console url show testinstance1
```

All these operations are available from the Horizon dashboard, in the *Compute* -> *Instances* section.

To stop the instance:

```
openstack server stop testinstance1
```

---

## Networking

The created instance has some limitations:

- it cannot be accessed from the outside because a security group is blocking all incoming traffic. The firewall blocks any Port, which is why we need to punch a hole to permit SSH/TCP/UDP/... access.
- the IP is on an internal network, out of range from the outside world. To access it, we need to assign it a Floating IP

### Security group

The default security group, which is automatically assigned to any instance follows the below rules:

- Egress traffic: no limit
- Ingress traffic from IP addresses in the same secutiry group: no limit
- Ingress traffic from any other IP address: blocked

To list the rules of the default security group:

```
openstack security group rule list default -f yaml --long
```

There are 2 egress rules, that allow traffic to any IP/port/protocol, and 2 ingress rules that allow traffic to any IP/port/protocol limited to a certain security group (`Remote Security Group`), i.e. the default security group. Basically, the only permitted inbound traffic must come from an IP in the default security group. 

To create a new security group:

```
openstack security group create testgroup1
```

The newly security group configuration allows any type of egress traffic, but no ingress traffic.
The following rules allows ICMP traffic and TCP traffic coming from port 22 (SSH):

```
openstack security group rule create --dst-port 22 --protocol tcp testgroup1
openstack security group rule create --protocol icmp testgroup1
```

Finally, you can attach this group to an existing server with

```
openstack server add security group testinstance1 testgroup1
```

### Floating IP

The server can access the outside world thanks to SNAT, that allows packets to flow from the internal network to the external network. We can do the opposite by creating a Floating IP, which belongs to the address range of the external network. Any packet sent to this IP address is redirected to the router connecting the internal and external networks, which is configured to perform DNAT: the Floating IP of the external network is converted to the Fixed IP of the internal network.

From the console, you should first check whether there is any available Floating IP that is not associated yet:

```
openstack floating ip list
```

Then, you can create a floating IP with:

```
openstack floating ip create public
```

Where `public` is the external network Id. Finally, you can associate it with the server instance with:

```
openstack server add floating ip testinstance1 {floating_ip}
```

---

After configuring the security group and the floating IP, we can connect to the server using the floating IP. SSH is for now the only allowed connection type, so:

```
ssh cirros@{floating_IP}
```

And use the default password (`gocubsgo`) to access it. At this point, you can also enable the public key access. Actually, we could have done that using the Keypair service of Openstack, but can only be done at server creation.

---

## Provisioning the servers

A first type of configuration is the keypair attachment when the server is created. We can do much more by leveraging the metadata service provided by Nova. This service is available within any instance at `http://169.254.169.254` and is used to personalize the instance creation in many ways:

```
openstack server create --property db_ip=10.10.10.3 # ...
```

is a first example that shows how to pass information at startup. Another scenario consists of provisioning the instance with a startup script:

```
openstack server create --user-data SCRIPT
```

An alternative to the startup script is the cloud-config file that describes the expected outcome of the instance initialization.

The install script can also read the properties passed using the metadata APIs:

```
#!/bin/bash
curl -O 169.254.169.254/openstack/latest/meta_data.json
db_ip=$(jq -r .meta.db_ip meta_data.json)

# ... remaining of install script 
```

This is especially useful to parameterize the creation of a new server. Any number of properties can be specified, like db name, user and password for a db creation. The web server needs the db IP address, which can be passed with the key-value metadata.

The cloud-init package can query the metadata APIs or be configured with a config drive with the option `--config-drive=true` in the server creation.



---

## Creating new Images from servers

If you want to replicate a server, you could snapshot it into a new image:

```
openstack server image create server_name --name new_image_name
```

With `openstack image list` you will see a new image with status `saving`. Once it transitions to `active` the image is ready to be used for a new server.

---

# Networking with Neutron

The core concept of Neutron are ports and subnets, anything else is considered extensions (routers, firewall, VPN). For instance, a router is connected to a network (subnet) via a port, which has a `port_id`.

Now we want to create a frontend network connected to the public network and a backend network exclusively connected to the front end. This configuration offers a better protection of the backend components (database), keeping only the frontend components (web server) accessible to the internet.

To create a new network with a subnet:

```
openstack network create frontend
openstack subnet create frontend-subnet --network frontend --subnet-range 10.1.1.0/24
openstack network create backend
openstack subnet create backend-subnet --network backend --subnet-range 10.2.2.0/24
```

Then we have to attach a router to the frontend subnet and to the public network (as external gateway, where SNAT is configured):

```
openstack router create front-pub-router
openstack router add subnet front-pub-router frontend-subnet
openstack router set --external-gateway public front-pub-router
```

For the backend network, the procedure is similar, except for the external gateway, which must not be configured.

```
openstack router create back-front-router
openstack router add subnet back-front-router backend-subnet
```

To connect the router to the second subnet we cannot do the same because the router would try to take over the same IP address already allocated by the `front-pub-router`. The solution is to create another port and attach the router to that port rather than the subnet

```
openstack port create frontend-port --network frontend
openstack router add port back-front-router frontend-port
```

Looking at the created ports for the backend network, with `openstack port list --network backend -f yaml --long` we can see that 2 ports have been allocated in the subnet:

- The port for the router
- The port for the DHCP server (created automatically)

---

## DHCP configurations

servers need internet access, provided by the front-pub-router through SNAT, and domain resolution. The web server also needs to know how to reach the backend network. There are 2 solutions:

### DNS configurations on servers

Both servers needs initialization of the `/etc/resolv.conf` file.
For the web server, the content of that file is:

```
10.2.2.0/24 via 10.1.1.110
```

Where `10.1.1.110` is the port IP connecting the frontend router to the backend router.

### DNS configurations on the subnet

The other possible solution is to attach a dns directly to the subnet:

```
openstack subnet set frontend-subnet --dns-nameserver 1.1.1.1 --host-route destination=10.2.2.0/24,gateway=10.1.1.110
```

After a `openstack subnet show frontend-subnet`, the fields `dns_nameservers` and `host_routes` are filled with this information, which is passed on to the server instances via DHCP each time it boots up. On server creation, cloud-init takes care of modifying the `/etc/resolv.conf` based on the DHCP configuration.

---

# Volumes with Cinder

Volumes are extremely useful to persist servers data and backups. There are several ways to create a volume:

- Empty volume:
    ```
    openstack volume create --size 1 volume_name
    ```
- Volume from image. This type of volume can be used to boot servers:
    ```
    openstack volume create --size 1 --image {image_ref} volume_name
    ```
- Volume from another volume. This is used to copy an existing volume:
    ```
    openstack volume create --source {volume_ref} volume_name
    ```
- From snapshot, which is the content of a volume frozen at an earlier point in time:
    ```
    openstack volume create --snapshot {snapshot_ref} volume_name
    ```

Volumes can be attached to multiple servers and can be bootable. To attach a volume to an already running server:

```
openstack server add volume {server_name} {volume_name}
```

Instead, to create a server with a volume attached from the beginning:

```
openstack server create --block-device-mapping DEVICE={volume_name} ...
```

To check the mount point in the server, the `attachments` field in `openstack volume show {volume_name}` includes this information.

## Booting  from a volume

**TODO**

---

# Deployment of the scenario

Now that we have configured the network, we can deploy the db and web server. For the db:

```
openstack server create --image ubuntu-22.04LTS-server-cloudimg-amd64 --flavor 2 --network backend mysqlinstance1
```

**TODO**






