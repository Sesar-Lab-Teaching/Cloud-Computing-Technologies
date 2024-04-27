# Docker Swarm

Docker Swarm enables the management and scaling of containerized applications across multiple nodes in a cluster. This guide shows how to setup a simple Docker swarm to deploy our scenario. We propose two different ways to replicate it:

- [Play with Docker](https://labs.play-with-docker.com/)
- Using VMs on your host

---

## Setup

### Play with Docker

It is a very straightforward method to test docker swarm commands because you can easily create multiple nodes and connect them. Create 3 node using the *Add new instance* button.

In the following sections, each docker command(s) will be associated to a node where the command must be executed. For example, when node is `manager1`, then run the command on the node we recognize as manager.

### Create VMs with Vagrant

[Download and install Vagrant](https://developer.hashicorp.com/vagrant/downloads), next run this:

```
cd vagrant_setup
vagrant up
```

You will end up with three different nodes: the manager `m1` and two workers `w1` and `w2`. Then, create 3 `docker contexts` to easily connect to these virtual machines without SSHing every time:

```
mkdir -p ~/.ssh/config.d

# If you already include `config.d`, then skip the `sed` command
sed -i "1 i \Include config.d/*\n" ~/.ssh/config

vagrant ssh-config m1 w1 w2 > ~/.ssh/config.d/swarm_config
for vm in m1 w1 w2; do
  docker context create \
    --docker "host=ssh://$vm" \
    $vm
done
```

Docker contexts are convenient to send `docker` commands to remote hosts (or local VMs in this case). In the following sections, each docker command(s) will be associated to a node where the command must be executed. For example, when node is `worker1`, then change the context with:

```
docker context use w1
```

---

## Swarm Init

Initially, the swarm mode is disabled. To enable it, we need to add the current node to the swarm cluster. The first added node automatically becomes a manager:

```
# manager1
docker swarm init
```

This command might return the following error:

```
Error response from daemon: could not choose an IP address to advertise since this system has multiple addresses on different interfaces (10.0.2.15 on eth0 and 192.168.56.201 on eth1) - specify one with --advertise-addr
```

If the node has multiple network interfaces, then we need to specify which one `docker swarm` is going to use (for the Vagrant setup, use the IP associated with the Host-only adapter): `docker swarm init --advertise-addr 192.168.56.201`.

---

## Swarm Join

Now that we have a cluster (with a single manager), retrieve the token to add other nodes either as manager or as workers:

- **Manager**:
    ```
    # manager1
    MANAGER_TOKEN="$(docker swarm join-token manager -q)"
    ```
- **Worker**:
    ```
    # manager1
    WORKER_TOKEN="$(docker swarm join-token worker -q)"
    ```

Now the worker nodes can join the cluster using the token:

```
# manager1
MANAGER_ENDPOINT="$(docker node inspect self --format '{{ .ManagerStatus.Addr }}')"

# worker1 & worker2
docker swarm join --token "$WORKER_TOKEN" "$MANAGER_ENDPOINT"
```