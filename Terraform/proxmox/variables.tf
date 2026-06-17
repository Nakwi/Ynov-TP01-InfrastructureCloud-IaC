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
f
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

variable "ssh_public_key" {
  type = string
}