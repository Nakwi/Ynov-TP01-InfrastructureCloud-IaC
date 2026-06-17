resource "proxmox_vm_qemu" "vm" {

  name        = INTERACTIF
  target_node = var.target_node
  vmid        = INTERACTIF

  clone = var.template_name

  agent = 1

  cores  = var.cores
  sockets = var.sockets
  memory = var.memory

  scsihw = "virtio-scsi-single"

  cpu {
    type = "x86-64-v3"
  }

  disk {
    slot    = "scsi0"
    size    = var.disk_size
    type    = "disk"
    storage = "local-zfs"
  }

  network {
    id     = 0
    model  = "virtio"
    bridge = "vmbr0"
  }

  os_type = "cloud-init"

  ipconfig0 = "ip=${var.ip_1},gw=${var.gateway}"

  sshkeys = var.ssh_public_key

  ciuser = "debian"

  boot = "order=scsi0"

  automatic_reboot = true
}