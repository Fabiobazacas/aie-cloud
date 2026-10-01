"""Leitura/escrita no bucket S3 da aula (substitui o Azure Blob Storage).

Convenção de prefixos (o equivalente aos "containers" do laboratório original):
    documents/  audios/  images/  images-3d/     <- entradas
    chunks/  entities/  transcriptions/  campaigns/  models3d/  jobs/   <- saídas
"""
from __future__ import annotations

import json
import os

import boto3

_s3 = boto3.client("s3")


def bucket() -> str:
    return os.environ["BUCKET"]


def ler(chave: str) -> bytes:
    return _s3.get_object(Bucket=bucket(), Key=chave)["Body"].read()


def gravar(chave: str, dados: bytes, content_type: str | None = None) -> str:
    extra = {"ContentType": content_type} if content_type else {}
    _s3.put_object(Bucket=bucket(), Key=chave, Body=dados, **extra)
    return f"s3://{bucket()}/{chave}"


def gravar_json(chave: str, objeto) -> str:
    return gravar(chave, json.dumps(objeto, ensure_ascii=False, indent=2).encode("utf-8"), "application/json")


def url_assinada(chave: str, expira_segundos: int = 3600) -> str:
    """Equivalente ao SAS URL do Azure. Só funciona enquanto a sessão do
    Learner Lab (credenciais temporárias da LabRole) estiver ativa."""
    return _s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket(), "Key": chave}, ExpiresIn=expira_segundos
    )


def nome_base(chave: str) -> str:
    """'documents/matricula.pdf' -> 'matricula'"""
    return os.path.splitext(os.path.basename(chave))[0]
