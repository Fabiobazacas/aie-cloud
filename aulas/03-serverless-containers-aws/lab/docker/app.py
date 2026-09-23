"""
Versão FastAPI da API de produtos QC — mesmo comportamento da Lambda v2-s3.

Empacotada num container Docker para rodar no AWS Elastic Beanstalk
(plataforma Docker de container único — não há ECS/Fargate/EKS no Learner
Lab). Autentica no S3 via a IAM Role da instância EC2 do Beanstalk
(LabInstanceProfile, anexada no Terraform) — sem credenciais no código.
"""
import csv
import io
import os

import boto3
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Quantum Commerce — Catálogo API", version="1.0")

S3_BUCKET = os.environ["S3_BUCKET_CATALOGO"]
S3_KEY    = "catalogo/produtos.csv"

_s3 = boto3.client("s3")


def carregar_produtos() -> list[dict]:
    obj = _s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
    csv_content = obj["Body"].read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(csv_content)))
    for r in rows:
        r["id"]      = int(r["id"])
        r["preco"]   = float(r["preco"])
        r["estoque"] = int(r["estoque"])
    return rows


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "qc-catalogo",
        "source": "s3",
        "runtime": "container",
    }


@app.get("/produtos")
def listar_produtos(categoria: str | None = None, nome: str | None = None):
    try:
        produtos = carregar_produtos()
    except Exception as e:
        raise HTTPException(500, detail=f"falha ao acessar S3: {e!s}")

    cat = (categoria or "").lower().strip()
    nm  = (nome or "").lower().strip()

    resultado = produtos
    if cat:
        resultado = [p for p in resultado if p["categoria"].lower() == cat]
    if nm:
        resultado = [p for p in resultado if nm in p["nome"].lower()]

    return {"total": len(resultado), "produtos": resultado}
