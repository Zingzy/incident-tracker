terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# Credentials come from the normal AWS CLI chain. Every taggable resource gets these tags.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "incident-tracker"
      ManagedBy = "terraform"
    }
  }
}
