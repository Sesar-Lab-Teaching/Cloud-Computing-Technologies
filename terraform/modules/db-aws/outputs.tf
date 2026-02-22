output "db_host" {
  description = "public IP address of the db instance"
  value       = aws_instance.db.public_ip
}