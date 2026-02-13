output "db_host" {
  description = "Hostname for the db"
  depends_on  = [docker_container.db]
  value       = docker_container.db.hostname
}