variable "db_user" {
  description = "the user created in the db"
  type        = string
}

variable "db_password" {
  description = "the password for the db user"
  type        = string
  sensitive   = true
}

variable "db_database" {
  description = "the default database name created in the db"
  type        = string
}