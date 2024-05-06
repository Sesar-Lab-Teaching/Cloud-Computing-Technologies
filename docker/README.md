# Docker

Docker allows us to replicate the scenario without Virtual machines or leveraging PaaS environments.

---

## Docker image for Webserver

The webserver code needs to be containerized, the first step is building an image. We can do it using:

```
docker build -t my_image_name .
```

Or we can let Dockercompose do it:

```
services:
  webserver:
    build:
      context: .
    ...
```

Without `build` instead of `image`, the image is automatically built by Dockercompose.

---

## Dockercompose

The compose file includes 3 containers:

- The MySQL server (`db`)
- A MySQL server that is used for seeding the `db` with the actual data (`seeder`)
- The webserver (built by Dockercompose)

To run it, use:

```
docker compose up -d # add `--build` to recreate the webserver image
```

### Networking

Dockercompose automatically creates a network shared between the defined services (containers). In this network, containers can communicate using their container name.

The only port we need to map is `5000`, which is exposed by the webserver. On the other hand, the MySQL server must be unreachable from the outside.

### Healthcheck and dependencies

When the MySQL containers starts, it is not immediately ready to accept connections from the webserver. The container is marked as *healthy* when it satisfies the `healthcheck`: for at most 6 times, the `test` command pings the MySQL server for a SQL connection until it receives a successful response. The timeout for each ping is 5 seconds and the delay between 2 consecutive pings is 3 seconds.

Once the MySQL container is healthy, the `seeder` container can initialize the *accounts* table and insert data into it. The `seeder` execution depends on the MySQL thanks to this statement:

```
depends_on:
  db:
    condition: service_healthy
```

In general, health checks are important for at least 2 reasons:

- Docker can use the health check to automatically restart containers that have failed. This ensures that your application stays online and available even if individual components encounter issues.
- Container orchestration platforms like Docker Swarm and Kubernetes use health checks to determine the readiness and availability of containers. This information is used for load balancing and service discovery, ensuring that requests are routed only to healthy instances.

---

## Test the webserver

Send a GET request to `localhost:5000` and you should receive the users data.

To destroy the compose containers, run

```
docker compose down
```
