"""Roteamento HTTP (API Gateway HTTP API, payload 2.0) + modo assíncrono.

Por que existe o modo assíncrono: a API Gateway corta qualquer requisição em
30s, mas pipelines com LLM (imagem generativa, 3D) demoram mais. Com
`"async": true` no body a função:
  1. grava jobs/<id>.json = {"status": "running"} no S3,
  2. se auto-invoca com InvocationType=Event (a Lambda aguenta até 15 min),
  3. responde 202 imediatamente com o job_id.
Quando termina, a invocação assíncrona sobrescreve jobs/<id>.json com
{"status": "ok", "resultado": ...} ou {"status": "erro", "erro": ...}.
"""
from __future__ import annotations

import json
import traceback
import urllib.parse
import uuid
from typing import Callable

import boto3

from . import s3io


class ErroEntrada(Exception):
    """Requisição inválida — vira HTTP 400 (ou o status informado)."""

    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.status = status


def resposta(status: int, corpo: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(corpo, ensure_ascii=False),
    }


def chave_obrigatoria(body: dict, campo: str = "bucket_key") -> str:
    valor = (body.get(campo) or "").strip()
    if not valor:
        raise ErroEntrada(f"'{campo}' é obrigatório (ex.: \"documents/arquivo.pdf\")")
    return valor


def _rodar_job(job_id: str, funcao: Callable, body: dict) -> None:
    try:
        resultado = funcao(body)
        s3io.gravar_json(f"jobs/{job_id}.json", {"status": "ok", "resultado": resultado})
    except Exception as erro:  # noqa: BLE001 — o job precisa registrar QUALQUER falha
        traceback.print_exc()
        s3io.gravar_json(f"jobs/{job_id}.json", {"status": "erro", "erro": str(erro)})


def executar(event, context, rotas: dict, rota_s3: tuple | None = None):
    """rotas: {(METODO, "/caminho"): (funcao(body) -> dict, assincrono_por_padrao)}.

    rota_s3: rota a executar quando o evento vem de uma S3 Event Notification
    (a Lambda é o "Blob Trigger" desta aula)."""
    # 1) Invocação assíncrona iniciada por esta própria função
    if "__job__" in event:
        funcao, _ = rotas[(event["metodo"], event["caminho"])]
        _rodar_job(event["__job__"], funcao, event["body"])
        return None

    # 2) Evento do S3 (upload de arquivo)
    registros = event.get("Records") or []
    if registros and registros[0].get("eventSource") == "aws:s3" and rota_s3:
        funcao, _ = rotas[rota_s3]
        for registro in registros:
            chave = urllib.parse.unquote_plus(registro["s3"]["object"]["key"])
            _rodar_job(f"s3-{uuid.uuid4().hex[:8]}", funcao, {"bucket_key": chave})
        return None

    # 3) Requisição HTTP
    http = event.get("requestContext", {}).get("http", {})
    metodo, caminho = http.get("method", "GET"), (event.get("rawPath") or "/").rstrip("/") or "/"
    rota = rotas.get((metodo, caminho))
    if rota is None:
        return resposta(404, {"erro": f"rota não encontrada: {metodo} {caminho}"})
    funcao, async_padrao = rota

    try:
        body = json.loads(event.get("body") or "{}") if metodo == "POST" else (event.get("queryStringParameters") or {})
        if not isinstance(body, dict):
            raise ErroEntrada("O body deve ser um objeto JSON")

        quer_async = body.get("async", async_padrao)
        if str(quer_async).lower() in ("true", "1"):
            job_id = uuid.uuid4().hex[:12]
            s3io.gravar_json(f"jobs/{job_id}.json", {"status": "running"})
            boto3.client("lambda").invoke(
                FunctionName=context.function_name,
                InvocationType="Event",
                Payload=json.dumps({"__job__": job_id, "metodo": metodo, "caminho": caminho, "body": body}).encode(),
            )
            return resposta(202, {
                "status": "accepted",
                "job_id": job_id,
                "consultar": f"aws s3 cp s3://{s3io.bucket()}/jobs/{job_id}.json -",
            })

        return resposta(200, funcao(body))
    except ErroEntrada as erro:
        return resposta(erro.status, {"erro": str(erro)})
    except Exception as erro:  # noqa: BLE001 — resposta de erro genérica é intencional
        traceback.print_exc()
        return resposta(500, {"erro": str(erro)})
