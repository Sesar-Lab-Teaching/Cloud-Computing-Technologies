# Openstack Guide for single VM

---

### Sources:

- https://ubuntu.com/openstack/install#single-multi-large-cluster
- https://discourse.ubuntu.com/t/single-node-guided/35765
- Install on single VM: https://docs.openstack.org/devstack/latest/guides/single-vm.html
- See doc for devstack in the latest stable release: https://opendev.org/openstack/devstack/src/branch/stable/2025.2/doc/source
- For Networking: https://docs.openstack.org/devstack/latest/guides/neutron.html

---

The Openstack deployment we show is Devstack, probably the simplest way to approach Openstack for the first time. Nonetheless, it includes the most important Openstack features and support several different environments (dedicated hardware, VM, multi-node). The installation can be extended through plugins as explained [here](https://docs.openstack.org/devstack/2025.2/plugins.html).

## Install Devstack

The `autoinstall` script to initialize a server image with devstack is available in this folder (`user-data.yaml`)

**Important**:

- clone the Devstack repo by specifying a stable release. See the available branches [here](https://opendev.org/openstack/devstack/branches).

    ```bash
    git clone https://opendev.org/openstack/devstack --depth=1 --branch stable/2025.2
    ```
- the installation of devstack might break your connectivity and apply some significant changes to the system. You should probably create a snapshot of your machine before running the installation script (`stack.sh`), and write the logs in a file.

    ```bash
    ./stack.sh |& tee ../stack.logs
    ```

### Uninstall Devstack

Run `devstack/unstack.sh` (or `devstack/clean.sh` for a full uninstall).

---

## Usage

From now on, always login with the *stack* user (`sudo -u stack -i`) to run Openstack commands. you can access Horizon (the Web UI Dashboard of Openstack) from `http://${HOST_IP}/dashboard`.

**username**: admin        # "demo", or any other user created

**password**: the password you have specified in `local.conf`

To access Openstack from the console, you first need to configure it with the right env variables:

```bash
# source devstack/openrc {username} {project_name}
source devstack/openrc admin demo
```

Every Openstack command has the form:

```bash
openstack {service_id} {operation} [-c column_to_show] [-f formatting_option]
```

For more information on the available services and operations, use the help command: `openstack help {service_id} [{operation}]`. The second method to call Openstack APIs is through HTTP APIs:

```bash
OS_TOKEN=$(openstack token issue -c id -f value)
curl -X GET -H "X-Auth-Token: $OS_TOKEN" http://...
```

---

## Images with Glance

Each server needs a base image, i.e. the OS running in the server. Glance is the Openstack service that manages these images. We can see the available ones with:

```
openstack image list
```

Since the only image available by default with devstack is cirrOS, devised for test purposes, we need to import a new image, such as Ubuntu, in particular the 
[cloud image](https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img) 

```bash
# from the home directory of stack user
mkdir -p custom/images
cd custom/images
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

openstack image create "Ubuntu-24.04" \
   --file noble-server-cloudimg-amd64.img \
   --disk-format qcow2 \
   --container-format bare \
   --public
```

The same can be done from the Horizon dashboard (*Compute* -> *Images* -> *Create Image*), or HTTP APIs.

---

## SSH Key pair

To access the Nova servers using SSH, we need to create a key pair, composed of a public and a private key:

```bash
mkdir -p ~/custom/ssh-keys

# private key generation
openssl genrsa -out ~/custom/ssh-keys/demo-key.pem 2048
chmod 600 ~/custom/ssh-keys/demo-key.pem

# public key generation
openssl rsa -in ~/custom/ssh-keys/demo-key.pem -pubout -out ~/custom/ssh-keys/demo-key.pub
ssh-keygen -i -m PKCS8 -f ~/custom/ssh-keys/demo-key.pub
```

And fill the property `keypair_public_key` in `stacks/envs/demo_env.yaml` with the retrieved public key in `ssh-rsa AAAAB3Nza...` format.

---

## Deploying the scenario with Heat

Resource creation can be automated using CLI or HTTP APIs. However, their deployment is not efficient and difficult to manage. Instead, we can use Heat templates to easily manage and provision the environment. Heat is a service that allows the full automation of the entire stack (group of resources) using a Yaml document. In this description file, each resource has a type and a list of properties, along with many other custom features that make template writing production-oriented (parameters, outputs, environments, custom resources, intrinsic functions, etc).

Stacks for the reference scenario are located in `stacks/` folder. First, clone the repo inside the VM:

```bash
git clone https://github.com/Sesar-Lab-Teaching/Cloud-Computing-Technologies.git --depth=1 --sparse cct-repo
git sparse-checkout set iaas-openstack/
cd iaas-openstack
```

Heat templates can be validated with:

```bash
openstack orchestration template validate -e stacks/envs/demo_env.yaml -t ./stacks/demo.yaml
```

But we will only create the root stack (remove `--dry-run` to deploy):

```bash
openstack stack create -t ./stacks/demo.yaml -e ./stacks/envs/demo_env.yaml --wait --dry-run demo_cct
```

To monitor the state of the stack deployment and see the outputs when it is ready:

```bash
# to see the entire history of events (CREATE_IN_PROGRESS, FAILED, COMPLETE, etc) 
# related to the resources created by the stack
openstack stack event list demo_cct
# to retrieve the current stack status 
openstack stack show -f value -c stack_status demo_cct
```

To delete the stack:

```bash
openstack stack delete demo_cct
```

---

## Access the Webserver

Now the webserver is available and a shell can be opened through horizon, APIs, or SSH:

```bash
# assuming 172.24.4.100 is the chosen Floating IP address
ssh -i ~/custom/ssh-keys/demo-key.pem ubuntu@172.24.4.100
```

From the Devstack host, the index page of the webserver can be retrieved by issuing an HTTP request to `172.24.4.100:5000`:

```bash
curl http://172.24.4.100:5000
```

We should see the user accounts, which serves as a proof that the webserver correctly queried the db instance. 

### (Devstack only)

If the public network is virtual and not directly attached to the host physical interface, a Nova server IP address cannot be reached from the outside. However, we can create some Firewall rules that forward traffic coming from a certain port on the host to the web server VM in Devstack.

```bash
# replace $HOST_IP with the IP address you use to access the host VM
sudo iptables -t nat -A PREROUTING -p tcp -d "$HOST_IP" --dport 5000 -j DNAT --to-destination 172.24.4.100:5000
sudo iptables -t nat -A POSTROUTING -p tcp -d 172.24.4.100 --dport 5000 -j MASQUERADE
```

---

# Deploying the scenario with CLI commands (Deprecated)

⚠️⚠️⚠️ The remaining of this page will not be maintained. Some files/configurations might be different from the one specified with Heat.

The following sections describe how to use Openstack APIs to deploy the scenario, along with some theoretical aspects.

## Security Groups

Before creating a new instance, we need to define the security group. The default security group, which is automatically assigned to any instance if not specified otherwise, applies the following rules:

- Egress traffic: no limit
- Ingress traffic from IP addresses in the same secutiry group: no limit
- Ingress traffic from any other IP address: blocked

To list the rules of the default security group:

```bash
openstack security group rule list default -f yaml --long
```

There are 2 egress rules, that allow traffic to any IP/port/protocol, and 2 ingress rules that allow traffic to any IP/port/protocol limited to the `default` security group. Basically, the only permitted inbound traffic must come from an IP in the default security group. 

Now we create a security group that allows ICMP traffic enable SSH connections (port 22):

```bash
openstack security group create demo_secgroup
openstack security group rule create --dst-port 22 --protocol tcp demo_secgroup
openstack security group rule create --protocol icmp demo_secgroup
```

And the security groups specific for the web server and db:

```bash
# this sec group is not necessary because the default sec group already allows incoming connections which have a source inside the default sec group.
openstack security group create demo_mysql_secgroup
openstack security group rule create --dst-port 3306 --protocol tcp demo_mysql_secgroup
openstack security group create demo_webserver_secgroup
openstack security group rule create --dst-port 5000 --protocol tcp demo_webserver_secgroup
```

---

## SSH Key pair

To access the Nova servers using SSH, we need a keypair. The public key is automatically managed by Openstack, but we need to safely store the private key:

```bash
mkdir -p ~/custom/ssh-keys
openstack keypair create demo_key > ~/custom/ssh-keys/demo-key.pem
chmod 600 ~/custom/ssh-keys/demo-key.pem
```

Retrieve the generated public key with

```bash
openstack keypair show --public-key demo_key
```

---

## Networking with Neutron

Our scenario needs 2 networks:
- `public` - the gateway to the internet
- `demo_private` - private network connected to the public through a router. It hosts the database (inaccessible by the users) and the webapp, which must be accessible to the final user

Each network contains 1 or more subnets, which are used to allocate IP addresses when new ports (interfaces to other network component, such as routers) are created on a network.
The `public` network is generally available from Devstack start up. To create the `demo_private` network and subnet (`192.168.1.0/24`):

```bash
openstack network create demo_private
openstack subnet create demo_subnet \
    --network demo_private \
    --dns-nameserver 8.8.8.8 \
    --subnet-range 192.168.1.0/24
```

Then, this network must be linked to the `public` network through a router:

```bash
openstack router create demo_router
openstack router set demo_router --external-gateway public
openstack router add subnet demo_router demo_subnet
```

Finally, we can create the ports in the `demo_network` link the future guest instances (the webserver and the database) to fixed ip addresses.

```bash
WEBSERVER_IP=192.168.1.3
MYSQL_IP=192.168.1.4

openstack port create --network demo_private --fixed-ip subnet=demo_subnet,ip-address=$WEBSERVER_IP port_webserver
openstack port create --network demo_private --fixed-ip subnet=demo_subnet,ip-address=$MYSQL_IP port_mysql
```

---

## Cloud-init & Metadata server

Cloud-init is a widely adopted tool that automates the initial setup of cloud instances. On first boot, it processes user data, which is basically a declarative configuration file that initializes the instance by installing packages, setting up SSH keys, and applying any necessary customizations. This automation is especially useful with OpenStack, as it simplifies and accelerates instance provisioning while ensuring consistent configurations across deployments.

We have to specify 2 different cloud-init scripts, one for the web server and the other for the sql db. First create in the host the folder that will contain the scripts:

```bash
mkdir -p ~/custom/cloud-init
```

Now copy the `sqldb/provision-db.yaml` in `~/custom/cloud-init/db.yaml`, and `webserver/provision-webserver.yaml` in `~/custom/cloud-init/webserver.yaml`. These files contain the additional packages to install and the one-time commands to run (see `runcmd` property). They are specified using the `--user-data` option during instance creation.

Another interesting feature typically offered by cloud platforms is the metadata server, a special web service that supplies instance-specific information to virtual machines at runtime. It is usually accessible via a link-local address (e.g. `169.254.169.254`) and it delivers data such as instance identity, network configuration, and user data.

OpenStack uses DNAT to route packets from instances to the OpenStack metadata service. Applications running inside of instances access the OpenStack metadata service by making HTTP GET requests to a web server with IP address `169.254.169.254`. In an OpenStack deployment, there is no host with this IP address. Instead, OpenStack uses DNAT to change the destination IP of these packets so they reach the network interface that a metadata service is listening on.

User data includes the possibility of writing/reading custom properties. While building the webserver instance, we will specify the database ip as custom property (`--property`) so that it does not have to be hard-coded inside the cloud-init file. This is especially useful to parameterize the creation of a new instance with any number of properties, like db name, user and password for a db creation.

The cloud-init package can query the metadata APIs or be configured with a config drive with the option `--config-drive=true` in the server creation.

---

## Computing with Nova

Now the setup is ready to launch the actual instances. To establish the amount of resources an instance has (Storage size, Ram, CPUs), we can set the **flavor**. First create the **db** instance:

```bash
openstack server create \
    --image debian-12-genericcloud-amd64-20250316-2053 \
    --flavor d3 \
    --port port_mysql \
    --key-name demo_key \
    --user-data ~/custom/cloud-init/db.yaml \
    demo_db_instance
openstack server add security group demo_db_instance demo_secgroup
```

When the db instance is ready, we can launch the **webserver**, which will connect to the db to show the results:

```bash
DB_IP_ADDRESS="$(openstack port show port_mysql -f json | jq -r '.fixed_ips[0].ip_address')"
openstack server create \
    --image debian-12-genericcloud-amd64-20250316-2053 \
    --flavor d3 \
    --port port_webserver \
    --property db_ip=$DB_IP_ADDRESS \
    --key-name demo_key \
    --user-data ~/custom/cloud-init/webserver.yaml \
    demo_webserver_instance
openstack server add security group demo_db_instance demo_secgroup
openstack server add security group demo_db_instance demo_webserver_secgroup
```

To verify whether the instance is active, run `openstack server show testinstance1 -c status`.

We can also see logs from the server using

```bash
openstack console log show demo_webserver_instance
```

To open a VNC connection, run:

```bash
openstack console url show demo_webserver_instance
```

All these operations are available from the Horizon dashboard, in the *Compute* -> *Instances* section.

To stop the instance:

```bash
openstack server stop demo_webserver_instance
```

---

## Floating IPs

The webserver can access the outside world thanks to SNAT performed by gateway routers. The opposite is not possible unless you create a Floating IPs: they are IPs taken from the `public` subnet pool and assigned to guest instances. When a Floating IP is assigned, Openstack enables One-to-one NAT, maintaining a one-to-one mapping between private IP addresses and public IP addresses. 

From the console, you should first check whether there is any available Floating IP that is not associated yet:

```bash
openstack floating ip list
```

Then, you can create a floating IP and associate it with an existing port by running:

```bash
FLOATING_IP=172.24.4.198
openstack floating ip create \
    --floating-ip-address 172.24.4.198 \
    --port port_webserver \
    public
```

Instead, if you do not want to associate it to a specific port, you can omit the `--port` parameter and associate it with a server instance by running:

```bash
openstack server add floating ip testinstance1 172.24.4.198
```

Now your instance is available from the outside with SSH:

```bash
ssh -i ~/custom/ssh-keys/demo-key.pem debian@172.24.4.198
```

The index page of the webserver can be retrieved by issuing an HTTP request to `172.24.4.198` from the host:

```
curl http://172.24.4.198:5000
```

We should see the user accounts, which serves as a proof that the webserver correctly queried the mysql instance. 

### (Devstack only)
To expose the 5000 port on the host and see the web page, create an iptable rule:

```bash
sudo iptables -t nat -A PREROUTING -p tcp -d ${HOST_IP} --dport 5000 -j DNAT --to-destination 172.24.4.198:5000
sudo iptables -t nat -A POSTROUTING -p tcp -d 172.24.4.198 --dport 5000 -j MASQUERADE
```

---

## Creating new Images from servers

If you want to replicate a server, you could snapshot it into a new image:

```
openstack server image create server_name --name new_image_name
```

With `openstack image list` you will see a new image with status `saving`. Once it transitions to `active` the image is ready to be used for a new server.

---

## Volumes with Cinder

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

### Booting from a volume

After creating a volume from an image, you can attach this volume (instead of an image) to a `server create` command:

```
openstack server create --volume {volume_name} ...
```

In this way the server has no ephemeral storage at all. one advantage is that the servers need less storage, and the instance storage is centralized in a storage system. To avoid the creation of a new volume, we can directly run:

```
openstack server create --image {image_name} --boot-from-volume {size} ...
```

---

### Snapshots & Backups

Snapshot is a useful feature to create reproducible "snapshot" of our volume at a certain point in time. We can then revert the volume to a previous snapshot or create a volume from it. More here:

```
openstack help snapshot
```

backups is another service provided by Openstack and allows the duplication of a volume on several possible storage systems (swift, NFS; Google Cloud Storage, ...). It is also possible to create incremental backups. More here:

```
openstack help volume backup
```

