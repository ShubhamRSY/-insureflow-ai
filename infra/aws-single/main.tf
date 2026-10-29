# One small EC2 server running the whole app with Docker Compose
# (api + Postgres + Redis + Caddy for HTTPS). Sized for the AWS free-plan credits.
# ponytail: single server, no failover or managed backups; infra/aws/ is the full setup for a paid pilot.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

variable "region" {
  default = "us-east-2" # the AWS org only allows EC2 in us-east-2
}

variable "instance_type" {
  default = "t3.small" # 2 vCPU, 2 GB (+2 GB swap). About $15/month.
}

variable "ssh_public_key" {
  description = "Public key for SSH (contents of ~/.ssh/rytera_aws.pub)"
}

variable "ssh_cidr" {
  description = "Allow SSH from this address (e.g. 203.0.113.7/32). Empty = SSH closed; use Systems Manager."
  default     = ""
}

provider "aws" {
  region = var.region
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

resource "aws_key_pair" "deploy" {
  key_name   = "rytera-single"
  public_key = var.ssh_public_key
}

resource "aws_security_group" "web" {
  name        = "rytera-single"
  description = "Rytera single server: web open, SSH from one address"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  dynamic "ingress" {
    for_each = var.ssh_cidr == "" ? [] : [var.ssh_cidr]
    content {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.deploy.key_name
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  metadata_options {
    http_tokens = "required"
    # 2 hops so the app's Docker containers can use the instance role too.
    http_put_response_hop_limit = 2
  }

  user_data = <<-EOF
    #!/bin/bash
    set -e
    fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    apt-get update
    apt-get install -y docker.io docker-compose-v2
    usermod -aG docker ubuntu
    systemctl enable --now docker
  EOF

  tags = { Name = "rytera-single" }
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
}

output "ip" {
  value = aws_eip.app.public_ip
}

output "url" {
  value = "https://${replace(aws_eip.app.public_ip, ".", "-")}.sslip.io"
}
