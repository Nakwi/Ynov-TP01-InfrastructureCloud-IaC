variable "subscription_id" {
  description = "ID de l'abonnement Azure"
  type        = string
}

variable "project_name" {
  description = "Nom du projet utilise comme prefixe"
  type        = string
  default     = "tp-cloud"
}

variable "location" {
  description = "Region Azure"
  type        = string
  default     = "spaincentral"
}

variable "admin_username" {
  description = "Utilisateur administrateur des VM"
  type        = string
  default     = "admincloud"
}

variable "ssh_public_key_path" {
  description = "Chemin vers la cle SSH publique"
  type        = string
  default     = "~/.ssh/tp_azure_ed25519.pub"
}

variable "admin_ip_cidr" {
  description = "Ton IP publique autorisee en SSH. Exemple : 1.2.3.4/32"
  type        = string
}

variable "web_vm_size" {
  description = "Taille de la VM web"
  type        = string
  default     = "Standard_B2ats_v2"
}

variable "monitoring_vm_size" {
  description = "Taille de la VM monitoring"
  type        = string
  default     = "Standard_B2ats_v2"
}