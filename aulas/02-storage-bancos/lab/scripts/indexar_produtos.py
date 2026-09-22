"""
Aula 2 / Atividade 3-B — Indexar os produtos da QC no Azure AI Search com semantic ranking.

NOTA: Este script usa SEMANTIC SEARCH (ranking inteligente do AI Search).
Vector search "verdadeira" requer geração de embeddings — ver Exercício 3.1.

Variáveis de ambiente necessárias:
    SEARCH_ENDPOINT       — endpoint do AI Search (terraform output -raw search_endpoint)
    STORAGE_ACCOUNT_NAME  — nome do Storage Account com produtos.csv

Dependências:
    pip install --user azure-identity azure-search-documents azure-storage-blob
"""

import csv
import os
import time

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
)
from azure.storage.blob import BlobServiceClient


INDEX_NAME = "produtos-index"
SEMANTIC_CONFIG_NAME = "produtos-semantic-config"


def main():
    endpoint = os.environ["SEARCH_ENDPOINT"]
    storage_account = os.environ["STORAGE_ACCOUNT_NAME"]
    # exclude_managed_identity_credential: evita o "Timeout waiting for token
    # from portal" do Cloud Shell — ver popular_produtos.py para o motivo.
    credential = DefaultAzureCredential(exclude_managed_identity_credential=True)

    # 1. Criar índice
    print(f"→ Criando índice '{INDEX_NAME}' em {endpoint}...")
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

    index = SearchIndex(
        name=INDEX_NAME,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(
                name="nome",
                type=SearchFieldDataType.String,
                analyzer_name="pt-br.microsoft",
            ),
            SearchableField(
                name="descricao",
                type=SearchFieldDataType.String,
                analyzer_name="pt-br.microsoft",
            ),
            SimpleField(
                name="categoria",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="preco",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True,
            ),
            SimpleField(
                name="estoque",
                type=SearchFieldDataType.Int32,
                filterable=True,
            ),
        ],
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name=SEMANTIC_CONFIG_NAME,
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="nome"),
                        content_fields=[SemanticField(field_name="descricao")],
                        keywords_fields=[SemanticField(field_name="categoria")],
                    ),
                )
            ]
        ),
    )

    try:
        index_client.delete_index(INDEX_NAME)
    except Exception:
        pass
    index_client.create_index(index)
    print("✓ Índice criado")

    # 2. Baixar CSV do Blob e indexar
    blob_client = BlobServiceClient(
        f"https://{storage_account}.blob.core.windows.net",
        credential=credential,
    )
    blob = blob_client.get_blob_client(container="catalogo", blob="produtos.csv")
    csv_content = blob.download_blob().readall().decode("utf-8")
    rows = list(csv.DictReader(csv_content.splitlines()))

    documentos = [
        {
            "id": r["id"],
            "nome": r["nome"],
            "descricao": r["descricao"],
            "categoria": r["categoria"],
            "preco": float(r["preco"]),
            "estoque": int(r["estoque"]),
        }
        for r in rows
    ]

    search_client = SearchClient(
        endpoint=endpoint,
        index_name=INDEX_NAME,
        credential=credential,
    )
    result = search_client.upload_documents(documents=documentos)
    print(f"✓ {len(result)} documentos indexados")

    # Indexação é assíncrona — aguarda alguns segundos para os documentos
    # ficarem pesquisáveis antes de demonstrar as buscas.
    time.sleep(3)

    # 3. Demonstrar buscas
    print("\n=== Busca por keyword: 'cadeira escritório' ===")
    for doc in search_client.search(search_text="cadeira escritório", top=3):
        print(f"  [{doc['@search.score']:.2f}] {doc['nome']}")

    print("\n=== Busca semântica: 'algo para trabalhar em pé' ===")
    results = search_client.search(
        search_text="algo para trabalhar em pé",
        query_type="semantic",
        semantic_configuration_name=SEMANTIC_CONFIG_NAME,
        top=3,
    )
    for doc in results:
        score = doc.get("@search.reranker_score", doc.get("@search.score"))
        print(f"  [{score:.2f}] {doc['nome']} — {doc['descricao'][:60]}...")

    print("\n=== Filtro por categoria 'moveis' + ordenação por preço ===")
    for doc in search_client.search(
        search_text="*",
        filter="categoria eq 'moveis'",
        order_by=["preco asc"],
        top=5,
    ):
        print(f"  R$ {doc['preco']:>8.2f} - {doc['nome']}")


if __name__ == "__main__":
    main()
