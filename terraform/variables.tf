variable "aws_region" {
  description = "Region for every resource."
  type        = string
  default     = "ap-south-1"
}

variable "prefix" {
  description = "Name prefix for every resource."
  type        = string
  default     = "incident-tracker"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.21.0.0/16"
}

variable "azs" {
  description = "Two availability zones, one public and one private subnet in each."
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

variable "kubernetes_version" {
  description = "EKS control plane version."
  type        = string
  default     = "1.37"
}

variable "node_instance_type" {
  description = "Instance type for the managed node group."
  type        = string
  default     = "t3.small"
}

variable "node_count" {
  description = "Desired, minimum and maximum size of the node group."
  type        = object({ desired = number, min = number, max = number })
  default     = { desired = 1, min = 1, max = 2 }
}

variable "admin_cidr" {
  description = "Only this range may reach the EKS public API endpoint, for example your own IP as x.x.x.x/32."
  type        = string
}
