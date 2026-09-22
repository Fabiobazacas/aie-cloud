"""
Aula 2 / Atividade 2 — Popular T_PRODUTOS no Azure SQL Database.

O script demonstra como NÃO hardcodar segredos:
1. Lê a connection string do Azure Key Vault (não do código).
2. Lê os produtos de um CSV no Blob Storage.
3. Cria a tabela T_PRODUTOS no Azure SQL e insere os 20 produtos.

Autenticação: DefaultAzureCredential (usa a identidade do Cloud Shell).

Variáveis de ambiente necessárias:
    KEY_VAULT_NAME           — nome do Key Vault
    STORAGE_ACCOUNT_NAME     — nome do Storage Account com o CSV

Dependências:
    pip install --user pyodbc azure-identity azure-keyvault-secrets azure-storage-blob
"""

import csv
import os
import sys

import pyodbc
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient


def main():
    kv_name = os.environ["KEY_VAULT_NAME"]
    storage_account = os.environ["STORAGE_ACCOUNT_NAME"]

    # exclude_managed_identity_credential: no Cloud Shell, a var de ambiente que
    # sinaliza Managed Identity aponta pro "token broker" do próprio Cloud Shell,
    # que não responde como MI de verdade — DefaultAzureCredential trava nela com
    # "Timeout waiting for token from portal" e NÃO cai para AzureCliCredential
    # (que é o que realmente funciona, via `az login`). Excluir força esse fallback.
    credential = DefaultAzureCredential(exclude_managed_identity_credential=True)

    # 1. Ler connection string do Key Vault
    print(f"→ Lendo connection string de {kv_name}...")
    kv_client = SecretClient(
        vault_url=f"https://{kv_name}.vault.azure.net",
        credential=credential,
    )
    secret = kv_client.get_secret("sql-connection-string")
    conn_str = secret.value
    print("✓ Connection string obtida (não vamos imprimi-la)")

    # 2. Baixar CSV do Blob Storage
    print(f"→ Baixando produtos.csv de {storage_account}/catalogo...")
    blob_client = BlobServiceClient(
        f"https://{storage_account}.blob.core.windows.net",
        credential=credential,
    )
    blob = blob_client.get_blob_client(container="catalogo", blob="produtos.csv")
    csv_content = blob.download_blob().readall().decode("utf-8")
    rows = list(csv.DictReader(csv_content.splitlines()))
    print(f"✓ {len(rows)} produtos lidos do Blob")

    # 3. Conectar no Azure SQL via pyodbc
    print("→ Conectando no Azure SQL...")
    driver = "{ODBC Driver 18 for SQL Server}"
    conn_str_with_driver = f"Driver={driver};{conn_str}"

    with pyodbc.connect(conn_str_with_driver, autocommit=False) as conn:
        cursor = conn.cursor()

        # 4. Criar tabela (drop se existir, para idempotência do lab)
        cursor.execute("""
            IF OBJECT_ID('dbo.T_PRODUTOS','U') IS NOT NULL
                DROP TABLE dbo.T_PRODUTOS;
            CREATE TABLE dbo.T_PRODUTOS (
                id          INT PRIMARY KEY,
                nome        NVARCHAR(200) NOT NULL,
                descricao   NVARCHAR(1000),
                categoria   NVARCHAR(100),
                preco       DECIMAL(10,2),
                estoque     INT
            );
        """)
        conn.commit()
        print("✓ Tabela T_PRODUTOS criada")

        # 5. Inserir produtos
        for r in rows:
            cursor.execute(
                "INSERT INTO dbo.T_PRODUTOS VALUES (?, ?, ?, ?, ?, ?)",
                int(r["id"]),
                r["nome"],
                r["descricao"],
                r["categoria"],
                float(r["preco"]),
                int(r["estoque"]),
            )
        conn.commit()
        print(f"✓ {len(rows)} produtos inseridos")

        # 6. Verificar
        cursor.execute("SELECT COUNT(*) FROM dbo.T_PRODUTOS")
        total = cursor.fetchone()[0]
        cursor.execute(
            "SELECT TOP 3 id, nome, preco FROM dbo.T_PRODUTOS ORDER BY preco DESC"
        )
        top = cursor.fetchall()

    print("\n=== Resultado ===")
    print(f"Total de produtos: {total}")
    print("Top 3 mais caros:")
    for row in top:
        print(f"  #{row.id} - {row.nome} - R$ {row.preco}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Erro: {e}", file=sys.stderr)
        sys.exit(1)
