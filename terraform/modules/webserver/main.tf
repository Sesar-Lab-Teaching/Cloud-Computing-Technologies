terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
    }
  }
}

resource "docker_image" "webserver_image" {
  name = "cct-webserver:latest"
  build {
    context = "${path.root}/../webserver"
    build_args = {
      PYTHON_VERSION : "3.12"
    }
  }
  keep_locally = false
  force_remove = true
}

resource "docker_container" "webserver" {
  name     = "cct-webserver"
  hostname = "webserver"
  image    = docker_image.webserver_image.image_id
  env = [
    "MYSQL_HOST=${var.db_host}",
    "MYSQL_USER=${var.db_user}",
    "MYSQL_PASSWORD=${var.db_password}",
    "MYSQL_PORT=${var.db_port}",
    "MYSQL_DATABASE=${var.db_database}"
  ]
  ports {
    internal = 80
    external = 5000
  }
  dynamic "networks_advanced" {
    for_each = var.webserver_networks

    content {
      name = networks_advanced.value
    }
  }
}
