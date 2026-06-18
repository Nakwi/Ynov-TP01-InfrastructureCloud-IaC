resource "proxmox_virtual_environment_file" "cloud_init" {
  content_type = "snippets"
  datastore_id = "local"
  node_name    = var.target_node

  source_file {
    path = "./cloud-init/web.yaml"
  }
}

resource "proxmox_virtual_environment_vm" "vm" {
  name      = var.vmname # Nom de la nouvelle VM
  node_name = var.target_node # Noeud de destination de la VM
  vm_id     = var.vmID # ID de la nouvelle VM

  clone {
    vm_id   = 8004 #ID de la template
    full    = true # Type de clone
    datastore_id = "local-zfs"  # force la destination du clone
  }

  agent {
    enabled = true # QEMU Guest agent
  }

  cpu {
    cores   = var.cores
    sockets = var.sockets
    type    = "x86-64-v3"
  }

  memory {
    dedicated = var.memory
    floating  = var.memory
  }

  scsi_hardware = "virtio-scsi-single"

  disk {
    datastore_id = "local-zfs"
    interface    = "scsi0"
    size         = var.disk_size
    file_format  = "raw"
  }

  efi_disk {
  datastore_id = "local-zfs"
  file_format  = "raw"
  type         = "4m"
}

  network_device {
    model  = "virtio"
    bridge = "vmbr0"
  }

  operating_system {
    type = "l26"
  }

  initialization {
    datastore_id = "local-zfs"
    ip_config {
      ipv4 {
        address = var.vmIP   # format attendu : "192.168.1.10/24"
        gateway = var.vmGW
      }
    }
  }

  boot_order = ["scsi0"]
  bios = "ovmf"
  machine = "q35"
}