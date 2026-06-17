# Connexion a Proxmox

terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.109"
    }
  }
}

provider "proxmox" {
  endpoint  = var.pm_api_url        # ex: "https://192.168.1.10:8006/"
  api_token = "${var.pm_api_token_id}=${var.pm_api_token_secret}"
  insecure  = true
}