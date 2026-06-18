locals {
  proxmox_api_token = var.proxmox_api_token == null ? null : (
    can(regex("^[^@\\s]+@[A-Za-z0-9_-]+![^=\\s]+=", var.proxmox_api_token))
    ? var.proxmox_api_token
    : "${var.proxmox_api_token_id}=${var.proxmox_api_token}"
  )
}

provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = local.proxmox_api_token
  username  = var.proxmox_username
  password  = var.proxmox_password
  insecure  = var.proxmox_insecure

  ssh {
    agent       = var.proxmox_ssh_agent
    username    = var.proxmox_ssh_username
    password    = var.proxmox_ssh_password
    private_key = var.proxmox_ssh_private_key_path == null ? null : file(pathexpand(var.proxmox_ssh_private_key_path))
  }
}
