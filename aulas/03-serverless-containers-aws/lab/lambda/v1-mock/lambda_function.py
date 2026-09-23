"""
Lambda HTTP da Quantum Commerce — versão L1 (mock data).
Sem dependências externas (só stdlib), sem credenciais. Bom para validar que o
deploy via Terraform + API Gateway funciona.

No L2 vamos plugar no S3 do catálogo (criado nesta aula) via IAM Role
(LabRole) anexada à função — versão em ../v2-s3/.

Evento recebido: API Gateway HTTP API (payload format 2.0). Rota e método
chegam em event["rawPath"] / event["requestContext"]["http"]["method"];
query string em event["queryStringParameters"].
"""
import json

PRODUTOS_MOCK = [
    {"id": 1, "nome": "Cadeira Ergonômica DXRacer", "categoria": "moveis",           "preco": 1499.90},
    {"id": 2, "nome": "Notebook Dell Inspiron 15",  "categoria": "eletronicos",      "preco": 4299.00},
    {"id": 3, "nome": "Cafeteira Nespresso Mini",   "categoria": "eletrodomesticos", "preco": 499.00},
    {"id": 4, "nome": "Tênis Nike Air Zoom Pegasus","categoria": "calcados",         "preco": 799.90},
    {"id": 5, "nome": "Smartphone Galaxy S24",      "categoria": "eletronicos",      "preco": 3999.00},
]


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def listar_produtos(params: dict) -> dict:
    categoria = (params.get("categoria") or "").lower().strip()
    nome      = (params.get("nome")      or "").lower().strip()

    resultado = PRODUTOS_MOCK
    if categoria:
        resultado = [p for p in resultado if p["categoria"] == categoria]
    if nome:
        resultado = [p for p in resultado if nome in p["nome"].lower()]

    return _response(200, {"total": len(resultado), "produtos": resultado})


def health() -> dict:
    return _response(200, {"status": "ok", "service": "qc-catalogo", "source": "mock"})


def handler(event, context):
    """Entry point único — roteia por rawPath (a API Gateway HTTP API já mapeia
    GET /produtos e GET /health para esta mesma função Lambda)."""
    path = event.get("rawPath", "")
    params = event.get("queryStringParameters") or {}

    if path.endswith("/health"):
        return health()
    if path.endswith("/produtos"):
        return listar_produtos(params)

    return _response(404, {"erro": "rota não encontrada"})
