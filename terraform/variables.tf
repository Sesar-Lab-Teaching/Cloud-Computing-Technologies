variable "db_image" {
  default     = "mysql:8.4.0"
  description = "The Docker image to use for the DB container"
  type        = string
  validation {
    condition     = can(regex("^[a-zA-Z0-9/\\-\\.]+:[a-zA-Z0-9/\\-\\.]+$", var.db_image))
    error_message = "Docker image format must be \"repository:version\""
  }
}

variable "db_user" {
  description = "the user created in the db"
  type        = string
}

variable "db_password" {
  description = "the password for the db user"
  type        = string
  sensitive   = true
}

variable "db_root_password" {
  description = "the root password of the db"
  type        = string
  sensitive   = true
}

variable "db_database" {
  description = "the default database name created in the db"
  type        = string
}