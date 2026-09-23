"""
Lambda HTTP da Quantum Commerce — versão L2.

Lê produtos.csv do bucket S3 do catálogo (criado nesta aula) via a IAM Role
de execução da própria função (LabRole, anexada no Terraform). SEM
credenciais no código: o boto3 pega as credenciais automaticamente das
variáveis de ambiente que o runtime da Lambda injeta a partir da execution
role — mesmo princípio da Managed Identity do Azure, feito com a peça nativa
da AWS (IAM Role + boto3 default credential chain).

Variável de ambiente esperada (configurada pelo Terraform):
    S3_BUCKET_CATALOGO — nome do bucket S3 com o objeto 'catalogo/produtos.csv'
"""
import csv
import io
import json
import os

import boto3

S3_BUCKET = os.environ["S3_BUCKET_CATALOGO"]
S3_KEY    = "catalogo/produtos.csv"

_s3 = boto3.client("s3")


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def carregar_produtos() -> list[dict]:
    """Baixa produtos.csv do S3 e converte em lista de dicts."""
    obj = _s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
    csv_content = obj["Body"].read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(csv_content)))
    for r in rows:
        r["id"]      = int(r["id"])
        r["preco"]   = float(r["preco"])
        r["estoque"] = int(r["estoque"])
    return rows


def listar_produtos(params: dict) -> dict:
    try:
        produtos = carregar_produtos()
    except Exception as e:
        return _response(500, {"erro": f"falha ao acessar S3: {e!s}"})

    categoria = (params.get("categoria") or "").lower().strip()
    nome      = (params.get("nome")      or "").lower().strip()

    resultado = produtos
    if categoria:
        resultado = [p for p in resultado if p["categoria"].lower() == categoria]
    if nome:
        resultado = [p for p in resultado if nome in p["nome"].lower()]

    return _response(200, {"total": len(resultado), "produtos": resultado})


def health() -> dict:
    return _response(200, {"status": "ok", "service": "qc-catalogo", "source": "s3"})


def handler(event, context):
    path = event.get("rawPath", "")
    params = event.get("queryStringParameters") or {}

    if path.endswith("/health"):
        return health()
    if path.endswith("/produtos"):
        return listar_produtos(params)

    return _response(404, {"erro": "rota não encontrada"})
