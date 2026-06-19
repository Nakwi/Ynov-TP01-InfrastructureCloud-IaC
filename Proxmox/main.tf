locals {
  # Prefixe commun utilise pour nommer les ressources Proxmox.
  prefix = var.project_name

  # Utilisateur cree dans les VM par cloud-init.
  admin_user = "admincloud"

  # Cle SSH publique injectee dans les deux VM.
  ssh_public_key = trimspace(file(pathexpand(var.ssh_public_key_path)))

  # Definition des deux VM du projet.
  # Le for_each plus bas reutilise cette map pour eviter de dupliquer tout le code.
  vm_definitions = {
    web = {
      name            = "${local.prefix}-web"
      vm_id           = var.web_vm_id
      cloud_init_file = "cloud-init-web.yml"
      snippet_name    = "${local.prefix}-web-cloud-init.yml"
      ipv4_address    = var.web_ipv4_address
      cores           = var.web_cores
      memory          = var.web_memory
      disk_size       = var.web_disk_size
    }

    monitoring = {
      name            = "${local.prefix}-monitoring"
      vm_id           = var.monitoring_vm_id
      cloud_init_file = "cloud-init-monitoring.yml"
      snippet_name    = "${local.prefix}-monitoring-cloud-init.yml"
      ipv4_address    = var.monitoring_ipv4_address
      cores           = var.monitoring_cores
      memory          = var.monitoring_memory
      disk_size       = var.monitoring_disk_size
    }
  }

  # Si l'IP est en DHCP, on ne connait pas l'adresse a l'avance.
  # Si l'IP est statique, on retire le /24 pour afficher une commande SSH propre.
  vm_hosts = {
    for role, vm in local.vm_definitions :
    role => vm.ipv4_address == "dhcp" ? null : split("/", vm.ipv4_address)[0]
  }
}

# Telecharge l'image Debian cloud dans le datastore Proxmox.
# Cette image sert de base pour creer les disques des VM.
resource "proxmox_download_file" "debian_cloud_image" {
  content_type        = "import"
  datastore_id        = var.image_datastore_id
  node_name           = var.proxmox_node_name
  url                 = var.cloud_image_url
  file_name           = var.cloud_image_file_name
  overwrite_unmanaged = true
}

# Envoie les fichiers cloud-init dans le datastore Proxmox.
# Terraform cree un snippet pour la VM web et un autre pour la VM monitoring.
resource "proxmox_virtual_environment_file" "cloud_init" {
  for_each = local.vm_definitions

  content_type = "snippets"
  datastore_id = var.snippets_datastore_id
  node_name    = var.proxmox_node_name

  source_raw {
    # templatefile remplace ${ssh_public_key} dans le fichier cloud-init.
    data = templatefile("${path.module}/${each.value.cloud_init_file}", {
      ssh_public_key = local.ssh_public_key
    })

    file_name = each.value.snippet_name
  }
}

# Cree les deux VM Proxmox a partir de la map local.vm_definitions.
# Une seule ressource Terraform gere donc web et monitoring.
resource "proxmox_virtual_environment_vm" "vm" {
  for_each = local.vm_definitions

  name        = each.value.name
  description = "Managed by Terraform"
  tags        = ["terraform", each.key]

  node_name       = var.proxmox_node_name
  vm_id           = each.value.vm_id
  started         = var.vm_started
  on_boot         = var.vm_on_boot
  stop_on_destroy = true
  scsi_hardware   = "virtio-scsi-single"

  agent {
    # Active le QEMU Guest Agent cote configuration Proxmox.
    # Le paquet est installe dans les VM via les fichiers cloud-init.
    enabled = var.qemu_guest_agent_enabled
  }

  cpu {
    cores = each.value.cores
    type  = var.cpu_type
  }

  memory {
    dedicated = each.value.memory
  }

  disk {
    # Le disque de chaque VM est cree depuis l'image Debian telechargee plus haut.
    datastore_id = var.vm_datastore_id
    import_from  = proxmox_download_file.debian_cloud_image.id
    interface    = "scsi0"
    iothread     = true
    discard      = "on"
    size         = each.value.disk_size
  }

  initialization {
    # Datastore qui stocke le disque cloud-init attache a la VM.
    datastore_id = var.cloud_init_datastore_id

    # Bloc DNS optionnel.
    # Il est cree seulement si dns_servers ou dns_domain sont renseignes.
    dynamic "dns" {
      for_each = length(var.dns_servers) > 0 || var.dns_domain != null ? [1] : []

      content {
        domain  = var.dns_domain
        servers = var.dns_servers
      }
    }

    # Configuration IP envoyee a cloud-init.
    # Par defaut, les deux VM sont en DHCP.
    ip_config {
      ipv4 {
        address = each.value.ipv4_address
        gateway = each.value.ipv4_address == "dhcp" ? null : var.ipv4_gateway
      }
    }

    # Lie la VM au snippet cloud-init correspondant.
    user_data_file_id = proxmox_virtual_environment_file.cloud_init[each.key].id
  }

  network_device {
    # Carte reseau virtuelle branchee sur le bridge Proxmox.
    bridge   = var.network_bridge
    firewall = var.network_firewall
    model    = "virtio"
    vlan_id  = var.network_vlan_id
  }

  operating_system {
    # l26 = Linux 2.6+ dans Proxmox.
    type = "l26"
  }

  # Console serie utile avec les images cloud.
  serial_device {}

  lifecycle {
    precondition {
      # Si on configure une IP statique, il faut aussi definir une gateway.
      condition     = each.value.ipv4_address == "dhcp" || var.ipv4_gateway != null
      error_message = "Definis ipv4_gateway quand une VM utilise une IP statique."
    }
  }
}
