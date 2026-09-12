terraform {
  required_version = ">= 1.0.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Variáveis para facilitar customização
variable "prefix" {
  default = "lab-docker"
}

variable "location" {
  default = "eastus" # Escolha a região de sua preferência (ex: brazilsouth)
}

# 1. Resource Group
resource "azurerm_resource_group" "rg" {
  name     = "${var.prefix}-rg"
  location = var.location
}

# 2. Rede Virtual e Subnet
resource "azurerm_virtual_network" "vnet" {
  name                = "${var.prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "subnet" {
  name                 = "${var.prefix}-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

# 3. IP Público
resource "azurerm_public_ip" "pip" {
  name                = "${var.prefix}-pip"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Dynamic"
}

# 4. Firewall (NSG) - Libera SSH e Porta 8080 para testes
resource "azurerm_network_security_group" "nsg" {
  name                = "${var.prefix}-nsg"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "App-Port"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8080"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# 5. Interface de Rede
resource "azurerm_network_interface" "nic" {
  name                = "${var.prefix}-nic"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pip.id
  }
}

resource "azurerm_network_interface_security_group_association" "nisg" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

# Script Cloud-Init para instalar Docker e Docker Compose automaticamente
locals {
  cloud_init = <<-EOF
    #cloud-config
    package_update: true
    packages:
      - apt-transport-https
      - ca-certificates
      - curl
      - gnupg
      - lsb-release
    runcmd:
      # Adicionar chave GPG oficial do Docker e repositório
      - mkdir -p /etc/apt/keyrings
      - curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
      - echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
      - apt-get update
      - apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
      - usermod -aG docker azureuser
      - mkdir -p /home/azureuser/lab
      - chown -R azureuser:azureuser /home/azureuser/lab
  EOF
}

# 6. Máquina Virtual (Standard_D2s_v3 - 2 vCPUs, 8 GB RAM)
resource "azurerm_linux_virtual_machine" "vm" {
  name                  = "${var.prefix}-vm"
  location              = azurerm_resource_group.rg.location
  resource_group_name   = azurerm_resource_group.rg.name
  size                  = "Standard_D2s_v3"
  admin_username        = "azureuser"
  network_interface_ids = [azurerm_network_interface.nic.id]
  disable_password_authentication = false
  admin_password        = "Pa$$w0rd"

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  custom_data = base64encode(local.cloud_init)
}

# Output para sabermos o IP de acesso
output "public_ip_address" {
  value = azurerm_public_ip.pip.ip_address
}

# Output para sabermos Usuario e Senha
output "user_credentials" {
  value = { 
    username = azurerm_linux_virtual_machine.vm.admin_username
    password = azurerm_linux_virtual_machine.vm.admin_password
    }
    sensitive = true
}
