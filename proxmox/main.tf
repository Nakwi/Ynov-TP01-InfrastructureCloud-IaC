resource "proxmox_vm_qemu" "vm" {

  name        = var.vm_name
  target_node = var.target_node
  vmid        = var.vm_id

  clone = var.template_name

  agent = 1

  cores  = var.cores
  sockets = 1
  memory = var.memory

  scsihw = "virtio-scsi-single"

  cpu {
    type = "host"
  }

  disk {
    slot    = "scsi0"
    size    = var.disk_size
    type    = "disk"
    storage = "local-lvm"
  }

  network {
    id     = 0
    model  = "virtio"
    bridge = "vmbr0"
  }

  os_type = "cloud-init"

  ipconfig0 = "ip=${var.ip_address},gw=${var.gateway}"

  sshkeys = var.ssh_public_key

  ciuser = "ubuntu"

  boot = "order=scsi0"

  automatic_reboot = true
}