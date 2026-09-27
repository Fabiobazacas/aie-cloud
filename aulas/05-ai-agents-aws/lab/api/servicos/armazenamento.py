"""Camada de armazenamento: arquivo local (padrão, custo zero) ou S3.

Troca via variável de ambiente `ARMAZENAMENTO=s3` + `BUCKET_DEVA=<nome-do-bucket>`.
Local é o padrão de sala de aula — nenhuma chamada AWS acontece nesse modo.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

DADOS_DIR = Path(__file__).resolve().parent.parent.parent / "dados"


def _modo_s3() -> bool:
    return os.environ.get("ARMAZENAMENTO") == "s3"


def _bucket() -> str:
    bucket = os.environ.get("BUCKET_DEVA")
    if not bucket:
        raise RuntimeError("ARMAZENAMENTO=s3 exige BUCKET_DEVA definido")
    return bucket


def ler_texto(caminho: str, padrao: str = "") -> str:
    if _modo_s3():
        import boto3
        from botocore.exceptions import ClientError

        s3 = boto3.client("s3")
        try:
            obj = s3.get_object(Bucket=_bucket(), Key=caminho)
            return obj["Body"].read().decode("utf-8")
        except ClientError as erro:
            if erro.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return padrao
            raise
    arquivo = DADOS_DIR / caminho
    if not arquivo.exists():
        return padrao
    return arquivo.read_text(encoding="utf-8")


def escrever_texto(caminho: str, conteudo: str) -> None:
    if _modo_s3():
        import boto3

        boto3.client("s3").put_object(Bucket=_bucket(), Key=caminho, Body=conteudo.encode("utf-8"))
        return
    arquivo = DADOS_DIR / caminho
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(conteudo, encoding="utf-8")


def ler_json(caminho: str, padrao):
    bruto = ler_texto(caminho, "")
    if not bruto.strip():
        return padrao
    return json.loads(bruto)


def escrever_json(caminho: str, dado) -> None:
    escrever_texto(caminho, json.dumps(dado, ensure_ascii=False, indent=2))
