output "resource_group_name" {
  description = "Nom du groupe de ressources"
  value       = azurerm_resource_group.main.name
}

output "web_public_ip" {
  description = "IP publique de la VM web"
  value       = azurerm_public_ip.web.ip_address
}

output "monitoring_public_ip" {
  description = "IP publique de la VM monitoring"
  value       = azurerm_public_ip.monitoring.ip_address
}

output "ssh_web" {
  description = "Commande SSH pour la VM web"
  value       = "ssh -i ~/.ssh/tp_azure_ed25519 ${var.admin_username}@${azurerm_public_ip.web.ip_address}"
}

output "ssh_monitoring" {
  description = "Commande SSH pour la VM monitoring"
  value       = "ssh -i ~/.ssh/tp_azure_ed25519 ${var.admin_username}@${azurerm_public_ip.monitoring.ip_address}"
}

output "web_url" {
  description = "URL du futur site web"
  value       = "http://${azurerm_public_ip.web.ip_address}"
}

output "uptime_kuma_url" {
  description = "URL future d'Uptime Kuma"
  value       = "http://${azurerm_public_ip.monitoring.ip_address}:3001"
}