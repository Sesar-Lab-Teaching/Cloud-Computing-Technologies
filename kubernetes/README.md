# Kubernetes

Kubernetes is a container orchestration platform that provides features for managing, scaling, and deploying containerized applications across a cluster of machines. Compared to Docker Swarm, Kubernetes offers more advanced capabilities, like automated scaling, making it suitable for larger and more complex deployments. Additionally, Kubernetes has a larger ecosystem with support for various cloud providers and extensive community contributions, making it a popular choice for managing containerized workloads at scale.

Sources:
- [Kubernetes Tutorials](https://kubernetes.io/docs/tutorials/)

---

## Setup

The easiest way to locally create a Kubernetes cluster is through [Minikube](https://minikube.sigs.k8s.io/docs/start/). For this guide, we are going to use a multi-node cluster:

```
minikube start --nodes 2 -p kube-demo
alias kubectl="minikube -p kube-demo kubectl --"
```

On system restart, you need to restart the Minikube as well, running `minikube start -p kube-demo`.

To verify that the cluster has been created:

```
minikube profile list
```

Should display a similar table:

```
|-----------|-----------|---------|--------------|------|---------|---------|-------|--------|
|  Profile  | VM Driver | Runtime |      IP      | Port | Version | Status  | Nodes | Active |
|-----------|-----------|---------|--------------|------|---------|---------|-------|--------|
| kube-demo | docker    | docker  | 192.168.49.2 | 8443 | v1.28.3 | Running |     2 |        |
|-----------|-----------|---------|--------------|------|---------|---------|-------|--------|
```

To examine the status of the cluster (and its nodes):

```
minikube status -p kube-demo
```

---

## K8S Architecture

A Kubernetes cluster consists of two types of resources:

- The Control Plane coordinates the cluster: the Control Plane coordinates all activities in your cluster, such as scheduling applications, maintaining applications' desired state, scaling applications, and rolling out new updates.
- Nodes are the workers that run applications: a node is a VM or a physical computer that serves as a worker machine in a Kubernetes cluster. Every Kubernetes Node runs at least:
    * Kubelet, a process responsible for communication between the Kubernetes control plane and the Node; it manages the Pods and the containers running on a machine.
    * A container runtime (like Docker) responsible for pulling the container image from a registry, unpacking the container, and running the application.

When you deploy applications on Kubernetes, you tell the control plane to start the application containers. The control plane schedules the containers to run on the cluster's nodes. Node-level components, such as the kubelet, communicate with the control plane using the Kubernetes API, which the control plane exposes. End users can also use the Kubernetes API directly to interact with the cluster.

---

## `kubectl`

The common format of a kubectl command is: `kubectl action resource`

This performs the specified action (like `create`, `describe` or `delete`) on the specified resource (like `node` or `deployment`). You can use `--help` after the subcommand to get additional info about possible parameters (for example: `kubectl get nodes --help`).

The most common operations can be done with the following kubectl subcommands:

- `kubectl get` - list resources
- `kubectl describe` - show detailed information about a resource
- `kubectl logs` - print the logs from a container in a pod
- `kubectl exec` - execute a command on a container in a pod (e.g. `kubectl exec -ti $POD_NAME -- bash`)

---

## Pods

A Pod is a Kubernetes abstraction that represents a group of one or more application containers (such as Docker), and some shared resources for those containers. Those resources include:

- Shared storage, as Volumes
- Networking, as a unique cluster IP address
- Information about how to run each container, such as the container image version or specific ports to use

A Pod models an application-specific "logical host" and can contain different application containers which are relatively tightly coupled. For example, a Pod might include both the container with your Node.js app as well as a different container that feeds the data to be published by the Node.js webserver. The containers in a Pod share an IP Address and port space, are always co-located and co-scheduled, and run in a shared context on the same Node.

Pods are the atomic unit on the Kubernetes platform. When we create a Deployment on Kubernetes, that Deployment creates Pods with containers inside them (as opposed to creating containers directly). Each Pod is tied to the Node where it is scheduled, and remains there until termination (according to restart policy) or deletion. In case of a Node failure, identical Pods are scheduled on other available Nodes in the cluster.

---

## Deployments

Once you have a running Kubernetes cluster, you can deploy your containerized applications on top of it. To do so, you create a Kubernetes Deployment. The Deployment instructs Kubernetes how to create and update instances of your application. Once you've created a Deployment, the Kubernetes control plane schedules the application instances included in that Deployment to run on individual Nodes in the cluster.

Once the application instances are created, a Kubernetes Deployment controller continuously monitors those instances. If the Node hosting an instance goes down or is deleted, the Deployment controller replaces the instance with an instance on another Node in the cluster. This provides a self-healing mechanism to address machine failure or maintenance.

Scaling out a Deployment will ensure new Pods are created and scheduled to Nodes with available resources. Scaling will increase the number of Pods to the new desired state. Kubernetes also supports autoscaling of Pods, but it is outside of the scope of this tutorial. Scaling to zero is also possible, and it will terminate all Pods of the specified Deployment.

Running multiple instances of an application will require a way to distribute the traffic to all of them. Scaling is accomplished by changing the number of replicas in a Deployment. Once you have multiple instances of an application running, you would be able to do Rolling updates without downtime.

### Rolling Updates

A rolling update allows a Deployment update to take place with zero downtime. It does this by incrementally replacing the current Pods with new ones. The new Pods are scheduled on Nodes with available resources, and Kubernetes waits for those new Pods to start before removing the old Pods.

Rolling updates allow the following actions:

- Promote an application from one environment to another (via container image updates)
- Rollback to previous versions
- Continuous Integration and Continuous Delivery of applications with zero downtime

---

## Service

A Service in Kubernetes is an abstraction which defines a logical set of Pods and a policy by which to access them. Services enable a loose coupling between dependent Pods. A Service is defined using YAML or JSON, like all Kubernetes object manifests. The set of Pods targeted by a Service is usually determined by a label selector.

Although each Pod has a unique IP address, those IPs are not exposed outside the cluster without a Service. Services allow your applications to receive traffic. Services can be exposed in different ways by specifying a type in the spec of the Service:

- **ClusterIP** (default) - Exposes the Service on an internal IP in the cluster. This type makes the Service only reachable from within the cluster.
- **NodePort** - Exposes the Service on the same port of each selected Node in the cluster using NAT. Makes a Service accessible from outside the cluster using `<NodeIP>:<NodePort>`. Superset of ClusterIP.
- **LoadBalancer** - Creates an external load balancer in the current cloud (if supported) and assigns a fixed, external IP to the Service. Superset of NodePort.
- **ExternalName** - Maps the Service to the contents of the externalName field (e.g. foo.bar.example.com), by returning a CNAME record with its value. No proxying of any kind is set up. This type requires v1.7 or higher of kube-dns, or CoreDNS version 0.0.8 or higher.

Services have an integrated load-balancer that will distribute network traffic to all Pods of an exposed Deployment. Services will monitor continuously the running Pods using endpoints, to ensure the traffic is sent only to available Pods.

Kubernetes automatically creates a DNS entry for each Service. The DNS name for a Service follows the format: `<service-name>.<namespace>.svc.cluster.local`. You can use this DNS name to access the Service from within the cluster.

"Normal" (not headless) Services are assigned DNS A and/or AAAA records, depending on the IP family or families of the Service, with a name of the form `<service-name>.<namespace>.svc.cluster.local`. This resolves to the cluster IP of the Service.

Headless Services (without a cluster IP) Services are also assigned DNS A and/or AAAA records, with a name of the form `<service-name>.<namespace>.svc.cluster.local`. Unlike normal Services, this resolves to the set of IPs of all of the Pods selected by the Service. Clients are expected to consume the set or else use standard round-robin selection from the set.

### Headless Service

With a Standard Service of type *ClusterIP*, the pods included in that service are reachable through a virtual IP Address within the Kubernetes cluster. Kubernetes assigns a single virtual IP address to the Service, which acts as a stable endpoint for accessing the pods. Under the hood, Kubernetes performs load balancing among the pods registered to the service, distributing incoming traffic across them evenly.

From: [What is a headless service, what does it do/accomplish, and what are some legitimate use cases for it?](https://stackoverflow.com/questions/52707840/what-is-a-headless-service-what-does-it-do-accomplish-and-what-are-some-legiti)

> Each connection to the service is forwarded to one randomly selected backing pod. But what if the client needs to connect to all of those pods? What if the backing pods themselves need to each connect to all the other backing pods. Connecting through the service clearly isn’t the way to do this. What is? 
<br /> <br /> 
For a client to connect to all pods, it needs to figure out the IP of each individual pod. One option is to have the client call the Kubernetes API server and get the list of pods and their IP addresses through an API call, but because you should always strive to keep your apps Kubernetes-agnostic, using the API server isn’t ideal.
<br /> <br /> 
Luckily, Kubernetes allows clients to discover pod IPs through DNS lookups. Usually, when you perform a DNS lookup for a service, the DNS server returns a single IP — the service’s cluster IP. But if you tell Kubernetes you don’t need a cluster IP for your service (you do this by setting the clusterIP field to None in the service specification ), the DNS server will return the pod IPs instead of the single service IP. Instead of returning a single DNS A record, the DNS server will return multiple A records for the service, each pointing to the IP of an individual pod backing the service at that moment. Clients can therefore do a simple DNS A record lookup and get the IPs of all the pods that are part of the service. The client can then use that information to connect to one, many, or all of them.
<br /> <br /> 
Setting the `clusterIP` field in a service spec to `None` makes the service headless, as Kubernetes won’t assign it a cluster IP through which clients could connect to the pods backing it.

---

## StatefulSet

StatefulSets are intended to be used with stateful applications and distributed systems. However, the administration of stateful applications and distributed systems on Kubernetes is a broad, complex topic.

StatefulSet Pods have a unique identity that consists of an ordinal, a stable network identity, and stable storage. The identity sticks to the Pod, regardless of which node it's (re)scheduled on. For a StatefulSet with N replicas, each Pod in the StatefulSet will be assigned an integer ordinal, that is unique over the Set. By default, pods will be assigned ordinals from 0 up through N-1.

Each Pod in a StatefulSet derives its hostname from the name of the StatefulSet and the ordinal of the Pod. The pattern for the constructed hostname is `$(statefulset name)-$(ordinal)`. The example above will create three Pods named web-0,web-1,web-2. A StatefulSet can use a Headless Service to control the domain of its Pods.

For each `VolumeClaimTemplate` entry defined in a StatefulSet, each Pod receives one `PersistentVolumeClaim`. If no StorageClass is specified, then the default StorageClass will be used. When a Pod is (re)scheduled onto a node, its volumeMounts mount the PersistentVolumes associated with its PersistentVolume Claims. Note that, the PersistentVolumes associated with the Pods' PersistentVolume Claims are not deleted when the Pods, or StatefulSet are deleted. This must be done manually.

In summary, StatefulSets offer additional features and guarantees that are specifically tailored to the requirements of stateful applications like databases, particularly in terms of pod initialization, network identity, persistent storage, and service discovery.

### Storage with PersistentVolumeClaim

When using volumeClaimTemplates in a StatefulSet, you do not need to create Persistent Volumes (PVs) manually. Kubernetes will automatically create PVCs (Persistent Volume Claims) based on the templates defined in the StatefulSet, and the PVCs will dynamically bind to available PVs.

Under the hood, Kubernetes uses dynamic provisioning to create PVs based on the storage class specified in the PVC template. The storage class determines how the underlying storage is provisioned (e.g., on-premises storage, cloud storage, etc.).

---

## ConfigMaps and Secrets

Configurations and secrets are managed in a similar way to how Docker Swarm handles them. With Kubernetes you create resources of type `ConfigMap` and `Secret` for configurations and secrets, respectively. They contain a list of properties (that are encrypted on transmission in case of secrets) that can be referenced from other resources, for example for environment variables.

---

## Scenario Deployment

To locally create a K8s cluster, install Minikube and follow the [Setup](#setup).

Then push the webserver image to a public registry (or use the `maluz/webserver-cct-demo:1.0`) so that each node can easily pull the image.

To deploy the bank scenario, run:

```
kubectl apply -f deploy
```

It will apply all the configuration files it finds in the current folder.