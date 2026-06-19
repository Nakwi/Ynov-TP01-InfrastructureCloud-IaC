locals {
  prefix = var.project_name

  tags = {
    project = var.project_name
    managed = "terraform"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "${local.prefix}-rg"
  location = var.location

  tags = local.tags
}

resource "azurerm_virtual_network" "main" {
  name                = "${local.prefix}-vnet"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.10.0.0/16"]

  tags = local.tags
}

resource "azurerm_subnet" "main" {
  name                 = "${local.prefix}-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.10.1.0/24"]
}

resource "azurerm_network_security_group" "web" {
  name                = "${local.prefix}-web-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "Allow-SSH-From-Admin"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.admin_ip_cidr
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Allow-HTTP-Public"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = local.tags
}

resource "azurerm_network_security_group" "monitoring" {
  name                = "${local.prefix}-monitoring-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "Allow-SSH-From-Admin"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.admin_ip_cidr
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Allow-Uptime-Kuma-From-Admin"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3001"
    source_address_prefix      = var.admin_ip_cidr
    destination_address_prefix = "*"
  }

  tags = local.tags
}

resource "azurerm_public_ip" "web" {
  name                = "${local.prefix}-web-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = local.tags
}

resource "azurerm_public_ip" "monitoring" {
  name                = "${local.prefix}-monitoring-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = local.tags
}

resource "azurerm_network_interface" "web" {
  name                = "${local.prefix}-web-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.main.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.web.id
  }

  tags = local.tags
}

resource "azurerm_network_interface" "monitoring" {
  name                = "${local.prefix}-monitoring-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.main.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.monitoring.id
  }

  tags = local.tags
}

resource "azurerm_network_interface_security_group_association" "web" {
  network_interface_id      = azurerm_network_interface.web.id
  network_security_group_id = azurerm_network_security_group.web.id
}

resource "azurerm_network_interface_security_group_association" "monitoring" {
  network_interface_id      = azurerm_network_interface.monitoring.id
  network_security_group_id = azurerm_network_security_group.monitoring.id
}

resource "azurerm_linux_virtual_machine" "web" {
  name                = "${local.prefix}-web-vm"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  size                = var.web_vm_size
  admin_username      = var.admin_username

  custom_data = base64encode(templatefile("${path.module}/cloud-init-web.yml", {
    ssh_public_key = file(pathexpand(var.ssh_public_key_path))
  }))

  disable_password_authentication = true

  network_interface_ids = [
    azurerm_network_interface.web.id
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
  }

  os_disk {
    name                 = "${local.prefix}-web-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Debian"
    offer     = "debian-13"
    sku       = "13-gen2"
    version   = "latest"
  }

  tags = merge(local.tags, {
    role = "web"
  })
}

resource "azurerm_linux_virtual_machine" "monitoring" {
  name                = "${local.prefix}-monitoring-vm"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  size                = var.monitoring_vm_size
  admin_username      = var.admin_username

  custom_data = base64encode(templatefile("${path.module}/cloud-init-monitoring.yml", {
    ssh_public_key = file(pathexpand(var.ssh_public_key_path))
  }))

  disable_password_authentication = true

  network_interface_ids = [
    azurerm_network_interface.monitoring.id
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
  }

  os_disk {
    name                 = "${local.prefix}-monitoring-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Debian"
    offer     = "debian-13"
    sku       = "13-gen2"
    version   = "latest"
  }

  tags = merge(local.tags, {
    role = "monitoring"
  })
}