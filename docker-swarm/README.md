# Docker Swarm

Docker Swarm enables the management and scaling of containerized applications across multiple nodes in a cluster. This guide shows how to setup a simple Docker swarm to deploy our scenario. We propose two different ways to replicate it:

- [Play with Docker](https://labs.play-with-docker.com/)
- Using VMs on your host

---

## Setup

### Play with Docker

It is a very straightforward method to test docker swarm commands because you can easily create multiple nodes and connect them. Create 3 node using the *Add new instance* button, or start from a template by choosing from the list of available templates.

You can also ssh into the docker containers provided by Play with Docker, copying the content of the SSH field in the container description.

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

To check whether the nodes have been correctly added, run:

```
# manager
docker node ls
```

Or run the container with image `dockersamples/visualizer` to see the current status of a docker swarm from Web UI:

```
# manager
docker service create \
    --name=viz \
    --publish=8080:8080/tcp \
    --constraint=node.role==manager \
    --mount=type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
    dockersamples/visualizer
```

Then open the browser at: `http://{MANAGER_VM_IP}:8080`.

If we join a new manager node, it is added as *Reachable*, whereas the first one's status is *Leader*. If the leader node becomes unavailable, the other maangers are eligible for the election as the new leader.

---

## Promotion and Demotion

Nodes can be promoted to managers, or demoted to workers. To promote a worker to manager:

```
# manager
docker node promote w1
```

To demote a manager to worker:

```
# manager
docker node demote your_manager_node
```

To check the current role of a node, run `docker node inspect node_name`.

---

## Container vs Service vs Task

Before using services, it is important to understand the [difference between containers, services, and tasks](https://docs.docker.com/engine/swarm/how-swarm-mode-works/services/):

> When you deploy the **service** to the swarm, the swarm manager accepts your service definition as the desired state for the service. Then it schedules the service on nodes in the swarm as one or more replica tasks. The tasks run independently of each other on nodes in the swarm.

> A **container** is an isolated process. In the Swarm mode model, each task invokes exactly one container. A task is analogous to a "slot" where the scheduler places a container. Once the container is live, the scheduler recognizes that the task is in a running state. If the container fails health checks or terminates, the task terminates.

> A **task** is the atomic unit of scheduling within a swarm. When you declare a desired service state by creating or updating a service, the orchestrator realizes the desired state by scheduling tasks. For instance, you define a service that instructs the orchestrator to keep three instances of an HTTP listener running at all times. The orchestrator responds by creating three tasks. Each task is a slot that the scheduler fills by spawning a container. The container is the instantiation of the task. If an HTTP listener task subsequently fails its health check or crashes, the orchestrator creates a new replica task that spawns a new container.

> A task is a one-directional mechanism. It progresses monotonically through a series of states: assigned, prepared, running, etc. If the task fails, the orchestrator removes the task and its container and then creates a new task to replace it according to the desired state specified by the service.

> The underlying logic of Docker's Swarm mode is a general purpose scheduler and orchestrator. **The service and task abstractions themselves are unaware of the containers they implement**. Hypothetically, you could implement other types of tasks such as virtual machine tasks or non-containerized process tasks. The scheduler and orchestrator are agnostic about the type of the task. However, the current version of Docker only supports container tasks.

---

## Service

To create a new service:

```
docker service create [OPTIONS] IMAGE [COMMAND] [ARG...]
```

The options and structure of a service creation is very similar to the run of a Docker container. You can configure port mapping,volumes, network, etc.

A service will be deployed on one of your node, either a manager or a worker. To find out where it is deployed now and in the past:

```
docker service ps your_service
```

If you service is replicated, then each replica name is prepended by `.{replica_id}`. For example, if there are 3 replicas for a task called `example`, then the replica names are `example.1`, `example.2`, and `example.3`. If you want to redeploy it without any changes:

```
docker service update --force your_service
```

You can still list containers running on a node with `docker container ps` and the name of each container has the following format: `{task_name}.{task_id}`

We can set some constraints on the node where tasks run, like the node role:

```
docker service create \
    --constraint node.role==manager \
    ...
```

---


