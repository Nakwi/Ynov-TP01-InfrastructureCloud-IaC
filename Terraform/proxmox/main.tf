resource "proxmox_vm_qemu" "vm" {

  name        = var.vmname
  target_node = var.target_node
  vmid        = var.vmID

  clone = var.template_name

  agent = 1

  cores  = var.cores
  sockets = var.sockets
  memory = var.memory

  scsihw = "virtio-scsi-single"

  cpu = "x86-64-v3"

disks {
  scsi {
    scsi0 {
      disk {
        size    = var.disk_size
        storage = "local-zfs"
      }
    }
  }
}

network {
  model  = "virtio"
  bridge = "vmbr0"
}

  os_type = "l26"   # manquant

  cicustom = "user=local:snippets/web.yml"
  
  ipconfig0 = "ip=${var.vmIP},gw=${var.vmGW}"

  sshkeys = var.ssh_public_key

  ciuser = "debian"

  boot = "order=scsi0"

  automatic_reboot = true
}