terraform {
  required_version = ">= 1.0.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Senha aleatória para o Banco de Dados e VM
resource "random_password" "password" {
  length  = 16
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# 1. Resource Group
resource "azurerm_resource_group" "rg" {
  name     = "rg-appsec-lab"
  location = "Brazil South" # Ou East US se preferir
}

# 2. Banco de Dados (Azure SQL - Free/Basic)
resource "azurerm_mssql_server" "sql_server" {
  name                         = "sqlserver-appsec-lab-${random_password.password.result}" # Nome precisa ser globalmente único
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = azurerm_resource_group.rg.location
  version                      = "12.0"
  administrator_login          = "sqladmin"
  administrator_login_password = random_password.password.result
}

resource "azurerm_mssql_database" "sql_db" {
  name      = "appdb"
  server_id = azurerm_sql_server.id # Correção de referência abaixo se necessário, ou use azurerm_mssql_server.sql_server.id
  # Para manter o custo o menor possível (ou zero se elegível para o offer gratuito da sua subscription):
  sku_name   = "S0" # S0 ou Basic são os mais baratos para SQL Tradicional. (Se sua conta tiver o Free Tier de Azure SQL, ajuste conforme a API da Azure)
  storage_account_type = "Local"
}

# Corrigindo a referência do server_id para o recurso correto acima:
# (O bloco acima usa azurerm_mssql_server.sql_server.id)

# 3. Microsserviço (Azure Container Instances - ACI)
resource "azurerm_container_group" "aci_api" {
  name                = "aci-api-appsec"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  os_type             = "Linux"

  container {
    name   = "api"
    image  = "mcr.microsoft.com/azuredocs/aci-helloworld:latest" # Imagem de exemplo leve. Depois você troca pela sua API do Docker Hub.
    cpu    = "0.5"
    memory = "1.0"

    ports {
      port     = 80
      protocol = "TCP"
    }

    environment_variables = {
      DB_SERVER = azurerm_mssql_server.sql_server.fully_qualified_domain_name
      DB_NAME   = "appdb"
    }
  }

  dns_name_label = "api-appsec-lab-${random_password.password.result}"
}

# 4. Rede para a VM Cliente (VNet + Subnet)
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-lab"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "subnet" {
  name                 = "subnet-lab"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_public_ip" "vm_pip" {
  name                = "pip-vm-cliente"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Dynamic"
}

resource "azurerm_network_interface" "nic" {
  name                = "nic-vm-cliente"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.vm_pip.id
  }
}

# 5. VM Cliente (Baratinha: Standard_B1s)
resource "azurerm_linux_virtual_machine" "vm_cliente" {
  name                = "vm-appsec-cliente"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  size                = "Standard_B1s" # VM burstable super barata (~$7/mês se ficar 24h ligada, mas no lab você só paga os minutos de uso)
  admin_username      = "azureuser"
  network_interface_ids = [
    azurerm_network_interface.nic.id,
  ]

  admin_ssh_key {
    public_username = "azureuser"
    public_key      = file("~/.ssh/id_rsa.pub") # Certifique-se de ter uma chave SSH na sua máquina, ou mude para password auth
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "18.04-LTS"
    version   = "latest"
  }
}

# Outputs úteis para você pegar os IPs e FQDNs facilmente
output "api_fqdn" {
  value = azurerm_container_group.aci_api.fqdn
}

output "vm_public_ip" {
  value = azurerm_public_ip.vm_pip.ip_address
}

output "sql_server_fqdn" {
  value = azurerm_mssql_server.sql_server.fully_qualified_domain_name
}
