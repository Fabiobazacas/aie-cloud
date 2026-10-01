"""Exercício 03 — Reconhecimento de entidades (NER) + DynamoDB.

    POST /ner   {"bucket_key": "documents/matricula.pdf"}      (async por padrão)

Pipeline: PDF no S3 -> texto (OCR via Gemini se escaneado) -> extração de
entidades via LLM -> entities.json no S3 -> item no DynamoDB.

DynamoDB substitui o Cosmos DB: a "partition key" /documentName vira a hash
key `documentName`, e o `id` (uuid) vira a range key.

Variáveis de ambiente: BUCKET, GEMINI_API_KEY, DDB_ENTITIES_TABLE.
"""
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

from shared import gemini, pdf, prompts, s3io, web

logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger(__name__)

_tabela = None


def tabela():
    global _tabela
    if _tabela is None:
        _tabela = boto3.resource("dynamodb").Table(os.environ["DDB_ENTITIES_TABLE"])
    return _tabela


def processar(body: dict) -> dict:
    chave = web.chave_obrigatoria(body)
    log.info("NER em s3://%s/%s", s3io.bucket(), chave)

    texto = pdf.extrair_texto(s3io.ler(chave))
    if not texto.strip():
        raise web.ErroEntrada(f"Documento vazio: {chave}")
    log.info("Texto extraído: %d caracteres", len(texto))

    entidades = gemini.gerar_json(
        f"Extraia todas as entidades do seguinte documento:\n\n{texto}",
        sistema=prompts.carregar("ner_system.md"),
        temperatura=0.1,
        max_tokens=8192,
    )
    agora = datetime.now(timezone.utc).isoformat()
    entidades["_metadata"] = {"source_document": chave, "processed_at": agora, "model": gemini.MODELO_TEXTO}

    base = s3io.nome_base(chave)
    entities_key = f"entities/{base}/entities.json"
    s3io.gravar_json(entities_key, entidades)

    item_id = str(uuid.uuid4())
    # DynamoDB não aceita float — parse_float=Decimal converte valores/áreas do JSON.
    item = json.loads(
        json.dumps({
            "documentName": base,
            "id": item_id,
            "sourceFile": chave,
            "extractedAt": agora,
            "entities": entidades,
        }),
        parse_float=Decimal,
    )
    tabela().put_item(Item=item)
    log.info("DynamoDB: %s (documentName=%s, id=%s)", tabela().name, base, item_id)

    return {"status": "ok", "bucket_key": chave, "entities_path": entities_key, "dynamodb_id": item_id}


ROTAS = {("POST", "/ner"): (processar, True)}


def handler(event, context):
    return web.executar(event, context, ROTAS)
