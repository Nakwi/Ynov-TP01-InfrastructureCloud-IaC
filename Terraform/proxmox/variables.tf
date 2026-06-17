variable "pm_api_url" {}
variable "pm_api_token_id" {}
variable "pm_api_token_secret" {}

variable "target_node" {
  default = "pve"
}

variable "vm_name" {
  default = "terraform-vm"
}

variable "vm_id" {
  default = 200
}

variable "template_name" {
  default = "ubuntu-24.04-template"
}

variable "cores" {
  default = 2
}

variable "memory" {
  default = 4096
}

variable "disk_size" {
  default = "32G"
}

variable "ip_address" {
  default = "192.168.1.100/24"
}

variable "gateway" {
  default = "192.168.1.1"
}

variable "ssh_public_key" {}