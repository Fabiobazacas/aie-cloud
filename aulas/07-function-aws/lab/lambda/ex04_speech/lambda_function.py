"""Exercício 04 — Transcrição de voz + avaliação de atendimento.

    POST /transcribe   {"bucket_key": "audios/test_audio.wav"}

Pipeline: áudio no S3 -> transcrição (Gemini, entrada de áudio nativa)
       -> avaliação do atendimento via LLM -> item no DynamoDB + JSON no S3.

O Gemini recebe o áudio inline (base64). Limite da requisição: ~20 MB, ou
seja, ~14 MB de áudio. Para arquivos maiores, veja o Exercício 4.3.

Variáveis de ambiente: BUCKET, GEMINI_API_KEY, DDB_TRANSCRIPTIONS_TABLE.
"""
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

from shared import gemini, prompts, s3io, web

logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger(__name__)

MIME_POR_EXTENSAO = {
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".aiff": "audio/aiff",
}
LIMITE_BYTES = 14 * 1024 * 1024

PROMPT_TRANSCRICAO = (
    "Transcreva fielmente o áudio em português do Brasil. Se houver mais de um falante, "
    "inicie cada fala com o rótulo 'Atendente:' ou 'Cliente:'. Não resuma, não comente — "
    "devolva apenas a transcrição."
)

_tabela = None


def tabela():
    global _tabela
    if _tabela is None:
        _tabela = boto3.resource("dynamodb").Table(os.environ["DDB_TRANSCRIPTIONS_TABLE"])
    return _tabela


def transcrever(audio: bytes, mime: str) -> str:
    return gemini.gerar([gemini.parte_arquivo(audio, mime), PROMPT_TRANSCRICAO], temperatura=0, max_tokens=8192)


def processar(body: dict) -> dict:
    chave = web.chave_obrigatoria(body)
    extensao = os.path.splitext(chave)[1].lower()
    if extensao not in MIME_POR_EXTENSAO:
        raise web.ErroEntrada(f"Formato '{extensao}' não suportado. Use: {', '.join(MIME_POR_EXTENSAO)}")

    audio = s3io.ler(chave)
    log.info("Áudio carregado: %d bytes", len(audio))
    if len(audio) > LIMITE_BYTES:
        raise web.ErroEntrada(f"Áudio de {len(audio) / 1e6:.1f} MB passa do limite de ~14 MB para envio inline ao Gemini")

    transcricao = transcrever(audio, MIME_POR_EXTENSAO[extensao])
    if not transcricao.strip():
        transcricao = "[sem transcrição disponível]"
    log.info("Transcrição: %d caracteres", len(transcricao))

    texto = gemini.gerar(
        f"Analise a seguinte transcrição de atendimento:\n\n{transcricao}",
        sistema=prompts.carregar("transcription_eval.md"),
        temperatura=0.2,
        json_mode=True,
        max_tokens=4096,
    )
    try:
        analise = gemini.extrair_json(texto)
    except json.JSONDecodeError as erro:
        analise = {"raw_response": texto, "parse_error": str(erro)}

    base = s3io.nome_base(chave)
    agora = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid.uuid4())
    item = json.loads(
        json.dumps({
            "audioFileName": base,
            "id": item_id,
            "sourceFile": chave,
            "processedAt": agora,
            "transcription": transcricao,
            "analysis": analise,
        }),
        parse_float=Decimal,
    )
    tabela().put_item(Item=item)

    analysis_key = f"transcriptions/{base}/analysis.json"
    s3io.gravar_json(analysis_key, {"transcription": transcricao, "analysis": analise, "processed_at": agora})

    return {
        "status": "ok",
        "bucket_key": chave,
        "audioFileName": base,
        "transcription": transcricao[:200],
        "analysis_path": analysis_key,
        "dynamodb_id": item_id,
    }


ROTAS = {("POST", "/transcribe"): (processar, False)}


def handler(event, context):
    return web.executar(event, context, ROTAS)
