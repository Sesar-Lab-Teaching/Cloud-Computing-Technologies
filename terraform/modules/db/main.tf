terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
    }
  }
}

data "docker_registry_image" "db" {
  name = var.db_image
}

resource "docker_image" "db" {
  name          = data.docker_registry_image.db.name
  pull_triggers = [data.docker_registry_image.db.sha256_digest]
}

resource "docker_volume" "db_data" {
  name = "mysql_data"
}

resource "docker_container" "db" {
  name     = "cct-db"
  hostname = "db"
  image    = docker_image.db.image_id
  env = [
    "MYSQL_USER=${var.db_user}",
    "MYSQL_PASSWORD=${var.db_password}",
    "MYSQL_ROOT_PASSWORD=${var.db_root_password}",
    "MYSQL_DATABASE=${var.db_database}"
  ]
  healthcheck {
    test         = ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "-u", "${var.db_user}", "--password=${var.db_password}"]
    interval     = "3s"
    timeout      = "5s"
    retries      = 8
    start_period = "5s"
  }
  volumes {
    volume_name    = "mysql_data"
    container_path = "/var/lib/mysql"
  }
  dynamic "networks_advanced" {
    for_each = var.db_networks

    content {
      name = networks_advanced.value
    }
  }
}

resource "docker_container" "db_seeder" {
  name     = "cct-db-seeder"
  hostname = "db-seeder"
  image    = docker_image.db.image_id
  env = [
    "MYSQL_HOST=db",
    "MYSQL_USER=${var.db_user}",
    "MYSQL_PASSWORD=${var.db_password}",
    "MYSQL_DATABASE=${var.db_database}"
  ]
  restart    = "on-failure"
  depends_on = [resource.docker_container.db]
  entrypoint = [
    "bash",
    "-c",
    "mysql --host=$MYSQL_HOST -u $MYSQL_USER --password=\"$MYSQL_PASSWORD\" -D $MYSQL_DATABASE -e 'source /seed.sql'"
  ]
  volumes {
    container_path = "/seed.sql"
    host_path      = "${abspath(path.root)}/../sqldb/seed.sql"
    read_only      = true
  }
  dynamic "networks_advanced" {
    for_each = var.db_networks

    content {
      name = networks_advanced.value
    }
  }
}