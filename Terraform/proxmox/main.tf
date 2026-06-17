resource "proxmox_virtual_environment_vm" "vm" {
  name      = var.vmname
  node_name = var.target_node
  vm_id     = var.vmID

  clone {
    vm_id   = var.template_vmid  # bpg requiert un ID numérique
    full    = true
  }

  agent {
    enabled = true
  }

  cpu {
    cores   = var.cores
    sockets = var.sockets
    type    = "x86-64-v3"
  }

  memory {
    dedicated = var.memory
  }

  scsi_hardware = "virtio-scsi-single"

  disk {
    datastore_id = "local-zfs"
    interface    = "scsi0"
    size         = var.disk_size
    file_format  = "raw"
  }

  network_device {
    model  = "virtio"
    bridge = "vmbr0"
  }

  operating_system {
    type = "l26"
  }

  initialization {
    ip_config {
      ipv4 {
        address = var.vmIP   # format attendu : "192.168.1.10/24"
        gateway = var.vmGW
      }
    }
    user_account {
      username = "debian"
      keys     = [var.ssh_public_key]
    }
    user_data_file_id = "local:snippets/web.yml"
  }

  boot_order       = ["scsi0"]
  reboot_on_change = true
}