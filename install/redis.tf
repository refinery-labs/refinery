resource "tls_private_key" "refinery_redis_ssh_key" {
	algorithm = "RSA"
	rsa_bits  = 4096
}

resource "aws_key_pair" "refinery_redis_generate_ssh_key" {
	key_name   = "${var.ssh_key_name}"
	public_key = "${tls_private_key.refinery_redis_ssh_key.public_key_openssh}"
}

/*
	Firewall rules for the Refinery redis instance
*/
resource "aws_security_group" "refinery_redis_security_group" {
	name = "refinery_redis_security_group"
	description = "The security group for Refinerys redis instance."

    /*
    	Allow inbound TCP on port 6379 (redis)
    	
    	Lambda's have no concept of IP so there's no IP
    	whitelisting we can do here - the security is enabled
    	at the redis AUTH layer.
    */
    ingress {
        from_port = 6379
        to_port = 6379
        protocol = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }
    
    ingress {
        from_port = 22
        to_port = 22
        protocol = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }
    
    # Allow all outbound
    egress {
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }
}

/*
	We allocate an Elastic IP for the redis EC2 instance
	so that later on we can migrate to a new instance by
	just moving the IP address. This is likely to happen
	in the case of a user needing a larger redis instance
	with more memory, etc.
*/
resource "aws_eip" "refinery_redis_elastic_ip" {
	vpc = true
}

data "template_file" "docker_compose_yaml" {
	template = "${file("./redis-instance-config/docker-compose.yml")}"
	
	vars {
		password = "${var.redis_secrets["password"]}"
	}
}

data "template_file" "redis_conf" {
	template = "${file("./redis-instance-config/redis.conf")}"
	
	vars {
		secret_prefix = "${var.redis_secrets["secret_prefix"]}"
	}
}

resource "aws_instance" "refinery_redis_instance" {
	# The connection block tells our provisioner how to
	# communicate with the resource (instance)
	connection {
		# The default username for our AMI
		user = "ubuntu"
		
		# The path to your keyfile
		private_key = "${tls_private_key.refinery_redis_ssh_key.private_key_pem}"
	}
	
	instance_type = "t2.nano"
	
	# Pull the AMI ID from the config
	# The variables tf has all the AMIs for each region already mapped
	ami = "${lookup(var.regional_amis, var.region)}"
	
	key_name = "${var.ssh_key_name}"
	
	security_groups = ["${aws_security_group.refinery_redis_security_group.name}"]

	# Copy over some Docker files
	provisioner "file" {
		source = "./redis-instance-config/redis-docker"
		destination = "/home/ubuntu/"
	}
	
	# Write docker-compose.yml configuration
	provisioner "file" {
		content = "${data.template_file.docker_compose_yaml.rendered}"
		destination = "/home/ubuntu/redis-docker/docker-compose.yml"
	}
	
	# Write redis.conf configuration
	provisioner "file" {
		content = "${data.template_file.redis_conf.rendered}"
		destination = "/home/ubuntu/redis-docker/redis.conf"
	}

	# Copy over installer script
	provisioner "file" {
		source = "./redis-instance-config/setup-redis-instance.sh"
		destination = "/tmp/setup-redis-instance.sh"
	}
	
	# Run install script
	provisioner "remote-exec" {
		inline = [
			"sudo chmod +x /home/ubuntu/redis-docker/docker-entrypoint.sh",
			"sudo chmod +x /tmp/setup-redis-instance.sh",
			"sudo /tmp/setup-redis-instance.sh"
		]
	}
	
	depends_on = [
		"aws_eip.refinery_redis_elastic_ip",
		"aws_security_group.refinery_redis_security_group",
		"aws_key_pair.refinery_redis_generate_ssh_key"
	]
}

/*
	Associates the Elastic IP with the instance
*/
resource "aws_eip_association" "refinery_redis_elastic_ip_association" {
	instance_id   = "${aws_instance.refinery_redis_instance.id}"
	allocation_id = "${aws_eip.refinery_redis_elastic_ip.id}"
}