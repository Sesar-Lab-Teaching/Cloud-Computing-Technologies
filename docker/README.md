# Docker

Sources:
- [Docker networking](https://labs.iximiuz.com/tutorials/container-networking-from-scratch)
- [Docker Playground](https://labs.iximiuz.com/playgrounds/docker)

---

# Deploying the reference scenario

## Docker image for Webserver

The webserver code needs to be containerized, the first step is building an image. We can do it using:

```bash
docker build -t my_image_name .
```

Or we can let Dockercompose do it:

```yaml
services:
  webserver:
    build:
      context: .
    ...
```

Without `build` instead of `image`, the image is automatically built by Dockercompose.

---

## Dockercompose

The compose file includes 3 main containers:

- The MySQL server (`db`)
- A MySQL server that is used for seeding the `db` with the actual data (`seeder`)
- The webserver (built by Dockercompose)

To run it, use:

```bash
docker compose --project-name cct up -d --build
```

Then we can see the logs for the webserver:

```bash
docker compose -p cct logs app
```

And delete the compose (together with created volumes) with:

```bash
docker compose -p cct down -v
```

### Networking

Dockercompose automatically creates a network shared between the defined services (containers). In this network, containers can communicate using their container name.

The only port we need to map is `80`, which is exposed by the webserver. On the other hand, the MySQL server must be unreachable from the outside.

### Healthcheck and Auto-healing

When the MySQL containers starts, it is not immediately ready to accept connections from the webserver. The container is marked as *healthy* when it satisfies the `healthcheck` test command, which is re-executed every `interval` seconds.

Once the MySQL container is healthy, the `seeder` container can initialize the *accounts* table and insert data into it. The `seeder` execution depends on the MySQL healthcheck:

```yaml
depends_on:
  db:
    condition: service_healthy
```

In general, health checks are important for at least 2 reasons:

- Docker can use the health check to automatically restart containers that have failed. This ensures that your application stays online and available even if individual components encounter issues. This auto-healing behavior is typical of orchestrators like Docker Swarm and K8s, but can be emulated using a custom container that periodically checks the state of target containers (`willfarrell/autoheal`)
- Container orchestration platforms like Docker Swarm and Kubernetes use health checks to determine the readiness and availability of containers. This information is used for load balancing and service discovery, ensuring that requests are routed only to healthy instances.

---

## Test the webserver

After the compose is up, send a GET request to `localhost:5000`. You should receive a web page containing the user data and the hostname of the container, which corresponds to its ContainerId.

To test the auto-healing property we have to explicitly call the API `/make-unhealthy`, which will make the healthcheck tests fail. After the configured number of times the healthcheck fail, the container transits to the unhealthy state and the auto-healing container detects it. In particular, this containers tracks the containers with the label `autoheal: true` and restarts them when its state is unhealthy.

This is an interesting example of DinD (Docker in Docker) because the Docker socket is shared between the host and the auto-healing container so that the latter can monitor the other containers through the Docker APIs.

To more easily analyze the flow, open two terminals, one that shows the healthcheck results every 5 seconds:

```bash
watch -n 5 'docker inspect cct-app-1 --format "{{json .State.Health.Log}}" | jq'
```

And another shell that shows the status of your containers in the compose:

```bash
watch -n 3 docker compose -p cct ps
```

After calling the `/make-unhealthy` endpoint, healthchecks start to fail and after 3 times (depending on the configuration), the autohealer will restart it.

---

## Pushing the webserver image

Images should never be stored only locally in a production environment, but should be available in a shared registry. In this way, any replica node can easily pull the Docker image in case of primary node failure. You can push the image on Docker Hub or in a private registry. If the image is pushed on Docker Hub, we need to tag the image as follows:

```bash
docker tag cct-app:latest maluz/webserver-cct-demo:latest
```

Then make sure you are logged in into the public registry:

```bash
docker login
```

And finally push the image:

```bash
docker push maluz/webserver-cct-demo:latest
```

The alternative is using a private registry offered by a third-party vendor or build your own:

```bash
docker run -d -p 5001:5000 --restart always --name cct-registry registry:3
```

Tag the image with the new registry endpoint prefix and push it:

```bash
docker tag maluz/webserver-cct-demo:latest localhost:5001/cct-webserver:latest
docker push localhost:5001/cct-webserver:latest
```
