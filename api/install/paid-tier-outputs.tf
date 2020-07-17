# Outputs the Elastic IP address
output "redis_elastic_ip" {
  value = aws_eip.refinery_redis_elastic_ip.public_ip
}

# Outputs the Redis password
output "redis_password" {
  sensitive = true
  value     = var.redis_secrets["password"]
}

# Outputs the Redis secret prefix
output "redis_secret_prefix" {
  sensitive = true
  value     = var.redis_secrets["secret_prefix"]
}

# Outputs the public key in OpenSSH format
output "refinery_redis_ssh_key_public_key_openssh" {
  sensitive = true
  value     = tls_private_key.refinery_redis_ssh_key.public_key_openssh
}

# Outputs the public key in PEM format
output "refinery_redis_ssh_key_public_key_pem" {
  sensitive = true
  value     = tls_private_key.refinery_redis_ssh_key.public_key_pem
}

# Outputs the private key in PEM format
output "refinery_redis_ssh_key_private_key_pem" {
  sensitive = true
  value     = tls_private_key.refinery_redis_ssh_key.private_key_pem
}

# Outputs the Elastic IP allocation ID
output "redis_elastic_ip_id" {
  value = aws_eip.refinery_redis_elastic_ip.id
}

# Outputs the Redis AWS instance ID
output "redis_aws_instance_id" {
  value = aws_instance.refinery_redis_instance.id
}

# Outputs the Redis AWS instance ARN
output "redis_aws_instance_arn" {
  value = aws_instance.refinery_redis_instance.arn
}

# Outputs the Redis AWS instance security group ID
output "redis_aws_instance_security_group_arn" {
  value = aws_security_group.refinery_redis_security_group.arn
}