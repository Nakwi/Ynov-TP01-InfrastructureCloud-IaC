output "vm_ids" {
  description = "IDs Proxmox des VM"
  value = {
    for role, vm in proxmox_virtual_environment_vm.vm :
    role => vm.vm_id
  }
}

output "configured_ipv4_addresses" {
  description = "Adresses IPv4 configurees via cloud-init Proxmox"
  value = {
    web        = var.web_ipv4_address
    monitoring = var.monitoring_ipv4_address
  }
}

output "cloud_init_snippets" {
  description = "Snippets cloud-init uploades dans Proxmox"
  value = {
    for role, snippet in proxmox_virtual_environment_file.cloud_init :
    role => snippet.id
  }
}

output "guest_agent_ipv4_addresses" {
  description = "Adresses IPv4 remontees par QEMU Guest Agent quand il est disponible"
  value = {
    for role, vm in proxmox_virtual_environment_vm.vm :
    role => vm.ipv4_addresses
  }
}

output "ssh_web" {
  description = "Commande SSH pour la VM web"
  value       = local.vm_hosts.web == null ? "DHCP actif: recupere l'IP de ${proxmox_virtual_environment_vm.vm["web"].name} dans Proxmox, puis ssh -i ${trimsuffix(var.ssh_public_key_path, ".pub")} ${local.admin_user}@<ip>" : "ssh -i ${trimsuffix(var.ssh_public_key_path, ".pub")} ${local.admin_user}@${local.vm_hosts.web}"
}

output "ssh_monitoring" {
  description = "Commande SSH pour la VM monitoring"
  value       = local.vm_hosts.monitoring == null ? "DHCP actif: recupere l'IP de ${proxmox_virtual_environment_vm.vm["monitoring"].name} dans Proxmox, puis ssh -i ${trimsuffix(var.ssh_public_key_path, ".pub")} ${local.admin_user}@<ip>" : "ssh -i ${trimsuffix(var.ssh_public_key_path, ".pub")} ${local.admin_user}@${local.vm_hosts.monitoring}"
}

output "web_url" {
  description = "URL du futur site web"
  value       = local.vm_hosts.web == null ? "DHCP actif: recupere l'IP de ${proxmox_virtual_environment_vm.vm["web"].name} dans Proxmox" : "http://${local.vm_hosts.web}"
}

output "uptime_kuma_url" {
  description = "URL future d'Uptime Kuma"
  value       = local.vm_hosts.monitoring == null ? "DHCP actif: recupere l'IP de ${proxmox_virtual_environment_vm.vm["monitoring"].name} dans Proxmox" : "http://${local.vm_hosts.monitoring}:3001"
}
