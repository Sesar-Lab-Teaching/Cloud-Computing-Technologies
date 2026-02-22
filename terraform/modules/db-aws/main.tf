terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  owners = ["099720109477"] # Canonical
}

resource "aws_security_group" "db" {
  description = "Allow any host to open tcp connections to port 3306 (MySQL)"
  name        = "cct-db-sg"

  ingress {
    protocol    = "tcp"
    from_port   = 3306
    to_port     = 3306
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "db" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.large"

  associate_public_ip_address = true
  security_groups             = [aws_security_group.db.name]

  user_data = templatefile("${path.root}/files/db-user-data.tftpl", {
    user     = var.db_user,
    password = var.db_password,
    database = var.db_database
  })

  tags = {
    Name = "cct-terraform"
  }
}