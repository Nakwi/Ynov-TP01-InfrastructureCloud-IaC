variable "pm_api_url" {
  type = string
}
variable "pm_api_token_id" {
  type = string
  sensitive = true
}
variable "pm_api_token_secret" {
  type = string
  sensitive = true
}

variable "target_node" {
  default = "pve03"
}

variable "template_name" {
  default = "ynov-debian13-template"
}

variable "cores" {
  default = 2
}

variable "sockets" {
  default = 1
}

variable "memory" {
  default = 2048
}

variable "disk_size" {
  default = "32G"
}

variable "ip_1" {
  default = "192.168.10.64/24"
}

variable "ip_2" {
  default = "192.168.10.65/24"
}

variable "gateway" {
  default = "192.168.10.254"
}

variable "ssh_public_key" {
  type = string
}