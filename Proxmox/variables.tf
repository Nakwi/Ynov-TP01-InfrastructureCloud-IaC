variable "proxmox_endpoint" {
  description = "URL de l'API Proxmox. Exemple : https://192.168.1.10:8006/"
  type        = string
}

variable "proxmox_api_token" {
  description = "Secret du token API Proxmox, ou token complet au format terraform@pve!provider=secret"
  type        = string
  default     = null
  sensitive   = true
}

variable "proxmox_api_token_id" {
  description = "Identifiant du token API Proxmox utilise quand proxmox_api_token contient seulement le secret"
  type        = string
  default     = "terraform@pve!provider"
}

variable "proxmox_username" {
  description = "Utilisateur Proxmox avec realm, si tu n'utilises pas de token API. Exemple : root@pam"
  type        = string
  default     = null
}

variable "proxmox_password" {
  description = "Mot de passe Proxmox, si tu n'utilises pas de token API"
  type        = string
  default     = null
  sensitive   = true
}

variable "proxmox_insecure" {
  description = "Autorise le certificat TLS self-signed de Proxmox"
  type        = bool
  default     = true
}

variable "proxmox_ssh_agent" {
  description = "Utilise ssh-agent pour l'upload des snippets cloud-init"
  type        = bool
  default     = true
}

variable "proxmox_ssh_username" {
  description = "Utilisateur SSH du node Proxmox pour uploader les snippets"
  type        = string
  default     = "root"
}

variable "proxmox_ssh_password" {
  description = "Mot de passe SSH du node Proxmox, si ssh-agent n'est pas utilise"
  type        = string
  default     = null
  sensitive   = true
}

variable "proxmox_ssh_private_key_path" {
  description = "Chemin vers la cle privee SSH du node Proxmox, si ssh-agent n'est pas utilise"
  type        = string
  default     = null
}

variable "proxmox_node_name" {
  description = "Nom du node Proxmox"
  type        = string
  default     = "pve"
}

variable "project_name" {
  description = "Nom du projet utilise comme prefixe"
  type        = string
  default     = "tp-cloud"
}

variable "ssh_public_key_path" {
  description = "Chemin vers la cle SSH publique injectee dans les cloud-init"
  type        = string
  default     = "~/.ssh/tp_azure_ed25519.pub"
}

variable "network_bridge" {
  description = "Bridge Proxmox connecte aux VM"
  type        = string
  default     = "vmbr0"
}

variable "network_vlan_id" {
  description = "VLAN ID optionnel pour les interfaces reseau"
  type        = number
  default     = null
}

variable "network_firewall" {
  description = "Active le firewall Proxmox sur les interfaces VM"
  type        = bool
  default     = false
}

variable "snippets_datastore_id" {
  description = "Datastore Proxmox avec le content type Snippets active"
  type        = string
  default     = "local"
}

variable "image_datastore_id" {
  description = "Datastore Proxmox pour stocker l'image cloud telechargee"
  type        = string
  default     = "local"
}

variable "vm_datastore_id" {
  description = "Datastore Proxmox pour les disques des VM"
  type        = string
  default     = "local-lvm"
}

variable "cloud_init_datastore_id" {
  description = "Datastore Proxmox pour le disque cloud-init"
  type        = string
  default     = "local-lvm"
}

variable "cloud_image_url" {
  description = "URL de l'image cloud Debian utilisee pour creer les VM"
  type        = string
  default     = "https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2"
}

variable "cloud_image_file_name" {
  description = "Nom du fichier image cloud dans Proxmox"
  type        = string
  default     = "debian-13-genericcloud-amd64.qcow2"
}

variable "cpu_type" {
  description = "Type CPU Proxmox"
  type        = string
  default     = "x86-64-v2-AES"
}

variable "vm_started" {
  description = "Demarre les VM apres creation"
  type        = bool
  default     = true
}

variable "vm_on_boot" {
  description = "Demarre les VM au boot du node Proxmox"
  type        = bool
  default     = true
}

variable "qemu_guest_agent_enabled" {
  description = "Active l'agent QEMU cote Proxmox. Les cloud-init Proxmox installent qemu-guest-agent dans les VM"
  type        = bool
  default     = true
}

variable "web_vm_id" {
  description = "ID Proxmox de la VM web"
  type        = number
  default     = 201
}

variable "monitoring_vm_id" {
  description = "ID Proxmox de la VM monitoring"
  type        = number
  default     = 202
}

variable "web_cores" {
  description = "Nombre de cores de la VM web"
  type        = number
  default     = 2
}

variable "monitoring_cores" {
  description = "Nombre de cores de la VM monitoring"
  type        = number
  default     = 2
}

variable "web_memory" {
  description = "Memoire de la VM web en Mo"
  type        = number
  default     = 2048
}

variable "monitoring_memory" {
  description = "Memoire de la VM monitoring en Mo"
  type        = number
  default     = 2048
}

variable "web_disk_size" {
  description = "Taille du disque de la VM web en Go"
  type        = number
  default     = 20
}

variable "monitoring_disk_size" {
  description = "Taille du disque de la VM monitoring en Go"
  type        = number
  default     = 30
}

variable "web_ipv4_address" {
  description = "Adresse IPv4 CIDR de la VM web, ou dhcp"
  type        = string
  default     = "dhcp"
}

variable "monitoring_ipv4_address" {
  description = "Adresse IPv4 CIDR de la VM monitoring, ou dhcp"
  type        = string
  default     = "dhcp"
}

variable "ipv4_gateway" {
  description = "Gateway IPv4, obligatoire si une VM utilise une IP statique"
  type        = string
  default     = null
}

variable "dns_servers" {
  description = "Serveurs DNS optionnels injectes via cloud-init Proxmox"
  type        = list(string)
  default     = []
}

variable "dns_domain" {
  description = "Domaine DNS optionnel injecte via cloud-init Proxmox"
  type        = string
  default     = null
}
