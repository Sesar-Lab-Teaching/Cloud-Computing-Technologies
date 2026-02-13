terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
    }
  }
}

provider "docker" {}

resource "docker_network" "network" {
  name = "cct-network"
}

module "db" {
  source = "./modules/db"

  db_user          = var.db_user
  db_password      = var.db_password
  db_root_password = var.db_root_password
  db_database      = var.db_database
  db_image         = var.db_image
  db_networks      = [docker_network.network.name]
}

module "webserver" {
  source = "./modules/webserver"

  db_host            = module.db.db_host
  db_port            = 3306
  db_user            = var.db_user
  db_password        = var.db_password
  db_database        = var.db_database
  webserver_networks = [docker_network.network.name]
}