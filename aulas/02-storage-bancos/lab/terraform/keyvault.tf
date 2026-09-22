# Concede ao usuário autenticado permissão de plano de dados do Key Vault
# (secrets + certificates) ANTES do vault existir, no escopo do Resource Group.
# Motivo: com enable_rbac_authorization = true, a própria criação do vault já
# dispara uma leitura de "contatos de certificado" (GetCertificateContacts) no
# plano de dados. "Owner"/"Contributor" NÃO cobrem isso — Key Vault RBAC exige
# uma role de dados própria (dataActions), e o Azure não concede nenhuma por
# padrão. Sem essa permissão já propagada, essa leitura falha de forma 100%
# reprodutível com "context deadline exceeded" logo na criação do vault.
# Por isso a role é atribuída no RG (independente do vault) e o vault só é
# criado depois do time_sleep abaixo — nunca no próprio Key Vault, o que
# criaria uma dependência circular (a role precisaria do vault pronto, e o
# vault precisaria da role já propagada).
resource "azurerm_role_assignment" "kv_admin" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Aguarda a role propagar antes de criar o vault (evita o context deadline
# exceeded no GetCertificateContacts) e antes de criar os segredos (evita 403).
resource "time_sleep" "wait_rbac" {
  depends_on      = [azurerm_role_assignment.kv_admin]
  create_duration = "60s"
}

# Key Vault — guarda a connection string do SQL como segredo
resource "azurerm_key_vault" "qc" {
  name                       = "kv-qc-${random_string.sufixo.result}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  tags                       = local.tags
  depends_on                 = [time_sleep.wait_rbac]
}

# Connection string do Azure SQL como segredo no Vault
resource "azurerm_key_vault_secret" "sql_connection" {
  name         = "sql-connection-string"
  key_vault_id = azurerm_key_vault.qc.id
  # Sintaxe do ODBC Driver 18 (pyodbc no Cloud Shell), NÃO a do .NET/SqlClient:
  #   Uid/Pwd            (não "User ID"/"Password")
  #   Encrypt=yes/no     (não true/false)
  #   TrustServerCertificate=no
  # Com a sintaxe .NET o ODBC falha ("Invalid value ... 'Encrypt'" / login inválido).
  value        = "Server=tcp:${azurerm_mssql_server.qc.fully_qualified_domain_name},1433;Database=${azurerm_mssql_database.qc.name};Uid=sqladminqc;Pwd=${var.sql_admin_password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
  content_type = "connection-string"
  depends_on   = [time_sleep.wait_rbac]
}

# Chave primária do Cosmos como segredo. O Cloud Shell NÃO consegue emitir token
# AAD para a audience de data-plane do Cosmos (AudienceNotSupported), então o
# script autentica por key — lida daqui, sem hardcode (mesmo padrão do SQL).
resource "azurerm_key_vault_secret" "cosmos_key" {
  name         = "cosmos-primary-key"
  key_vault_id = azurerm_key_vault.qc.id
  value        = azurerm_cosmosdb_account.qc.primary_key
  content_type = "cosmos-key"
  depends_on   = [time_sleep.wait_rbac]
}
