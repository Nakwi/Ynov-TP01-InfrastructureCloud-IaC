variable "pm_api_url" {
  default = "pve03.nemealan.fr"
}
variable "pm_api_token_id" {}
variable "pm_api_token_secret" {}

variable "target_node" {
  default = "pve03"
}

variable "vm_name" {
  default = "ynov-cloud-vm01"
}

variable "vm_id" {
  default = 200
}

variable "template_name" {
  default = "ynov-debian13-template"
}

variable "cores" {
  default = 2
}

variable "memory" {
  default = 2048
}

variable "disk_size" {
  default = "32G"
}

variable "ip_address" {
  default = "192.168.10.100/24"
}

variable "gateway" {
  default = "192.168.10.254"
}

variable "ssh_public_key" {
  default = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFAG3iBJV8oS0IipL3EfRGrysOU0Iyauc0LBmkZAlBmQ"
}