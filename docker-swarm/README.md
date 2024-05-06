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
# manager
docker service create \
    --constraint node.role==manager \
    ...
```

Once you have created a service with a published port, it is available on all the nodes in the swarm (even if that node does not have a task belonging to the service). For example, if you are running a service for a web app that exposes the port 8080 and is currently running on `worker1`, you can access it from `worker2` and `manager1` too (on port 8080). This feature is called *Ingress Swarm Load Balancer*, as traffic comes into your cluster, you can hit any node, but it will be balanced to wherever the service is running at. The first network that the internet traffic encounters is the Ingress network, where the Load Balancer distributes the load. Ingress network is meant for published ports, not for general communication between services.

---

## Docker Stack

Just like a container can be defined inside a Docker-compose, a service can be defined in a Docker stack. Conceptually a Docker-compose file and a Docker-stack file has the same structure, although Docker stack has additional features. The main difference between them is networking: Docker-compose sets up a bridge network, while Docker stack creates an overlay network.

To create a new stack:

```
docker stack deploy -c stack_file.yml stack_name
```

To get the current stack status:

```
docker stack ps stack_name
```

To update the deployment after you change the `stack_file.yml`, just re-run `docker stack deploy` with the same parameters. If you want to deploy twice the stack, you just need to use two different stack names.

If we drain one node (`docker node update --availability=drain`), there is a reconciliation process: the tasks in that node are shut down and restored (recreated) in a different node. This happens automatically because Docker Swarm monitors the desired state represented in the stack file and updates the deployment when the current state is different from the desired one.

When we create a stack, a default network is created for communication between containers. So, to sum up, each node has 3 network interfaces:

- One for the public IP address
- One Virtual interface that is mapped to an IP in the Ingress network
- One Virtual interface that is mapped to an IP in the service network

Each service also has a Virtual IP associated, which we should use instead of the node IPs. Docker Swarm allows us to make a request to a service using a Virtual hostname (which is the service name by default) instead of the Virtual IP.

To delete a stack:

```
docker stack rm stack_name
```

---

## Volumes, Configs, and Secrets

Configs and secrets are special types of volumes. As for [secrets](https://docs.docker.com/engine/swarm/secrets/):

> In terms of Docker Swarm services, a secret is a blob of data, such as a password, SSH private key, SSL certificate, or another piece of data that should not be transmitted over a network or stored unencrypted in a Dockerfile or in your application's source code. You can use Docker secrets to centrally manage this data and securely transmit it to only those containers that need access to it. Secrets are encrypted during transit and at rest in a Docker swarm. A given secret is only accessible to those services which have been granted explicit access to it, and only while those service tasks are running.

> When you grant a newly-created or running service access to a secret, the decrypted secret is mounted into the container in an in-memory filesystem. The location of the mount point within the container defaults to `/run/secrets/<secret_name>` in Linux containers, or `C:\ProgramData\Docker\secrets` in Windows containers. You can also specify a custom location.

Regarding [configs]():

> Docker swarm service configs allow you to store non-sensitive information, such as configuration files, outside a service's image or running containers. This allows you to keep your images as generic as possible, without the need to bind-mount configuration files into the containers or use environment variables.

> Configs operate in a similar way to secrets, except that they are not encrypted at rest and are mounted directly into the container's filesystem without the use of RAM disks. Configs can be added or removed from a service at any time, and services can share a config.

---

## Volumes

Docker Swarm manages volumes in a distributed manner, ensuring that a single named volume is accessible to all replicas of a service, regardless of the node they are running on. This allows for data consistency and ensures that all replicas can access the same data volume, regardless of their location in the cluster.

Therefore, when you deploy a service with replicated mode and specify a named volume, Docker Swarm creates the volume once and makes it available to all replicas, allowing them to share data using that volume.

---

## Deploying the Bank Scenario

For the Bank scenario, we need 1 MySQL container and 2 instances (replicas) of the WebServer. First, we need to copy on the manager node the following files:

- `.dockerignore`
- `docker-compose.yml`
- `Dockerfile`
- `main.py`
- `mysql_pwd.secret`
- `requirements.txt`
- `seed.sql`

If you are using Vagrant, you just need to copy them in the same folder where the `Vagrantfile` is placed; that folder is mounted on the `/vagrant` folder in the guest machine. With Play with Docker, you may need to copy them using `sftp` for example (or just copy & paste the content file by file).

The `docker-compose.yml` file contains the necessary instructions to provision the containers (including the replicas). A docker compose file for `docker stack` usually includes a further command: the `deploy`. It accepts a map with the configurations for the replica, deployment mode, restart policy, etc.

Since you cannot create on-the-fly images in the Docker-compose file (so the web application image must be available on a Docker registry), we need to create a local Docker registry in the manager node and push the image to it:

```
# manager
cd /vagrant/deploy # cd on the folder where you have copied the files
MANAGER_IP="$(docker node inspect self --format '{{ .Status.Addr }}')"
docker run -d -p 5001:5000 --restart always --name registry registry:2
docker build -t bank-app:1.0 -t "$MANAGER_IP:5001/bank-app:1.0" .
```

Before pushing the image, we need to mark the manager registry as an unsafe registry due to the absence of HTTPS support:

```
# only workers
MANAGER_IP="$(docker info -f '{{ (index .Swarm.RemoteManagers 0).Addr }}' | cut -d':' -f1)"

# managers and workers (all nodes)
echo """{
    \"insecure-registries\" : [ \"$MANAGER_IP:5001\" ]
}""" | sudo tee /etc/docker/daemon.json

sudo systemctl restart docker # or follow this for play with docker: https://stackoverflow.com/questions/55983977/how-to-restart-play-with-docker-docker-daemon
```

Now we can push the image:

```
docker push "$MANAGER_IP:5001/bank-app:1.0"
```

Before deploying the stack, we need to configure all the nodes with the `.env` file.

Next create a stack with:

```
# manager
REGISTRY_IP="$MANAGER_IP" REGISTRY_PORT=5001 docker stack deploy -c docker-compose.yml bank
```

The services should be up and running, test it by invoking the webserver endpoint `http://{ANY_IP_IN_THE_CLUSTER}:5000`. The *Hostname* field in the HTML page should change on every page reload: this is the effect of the Swarm Load balancer that applies a round robin policy on the nodes hosting the webserver tasks.

### Scaling the Web server

To scale the webserver, we just need to update the `docker-compose.yml` file and run the same `docker stack deploy` command and specify the **same** stack name. In this way, Docker Swarm recognizes that you want to update the deploy and creates a new instance of the webserver container on one of the available nodes.