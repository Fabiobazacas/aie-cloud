"""Exercício 01 — Chunking semântico + indexação vetorial (Lambda, na VPC).

    POST /process   {"bucket_key": "documents/matricula.pdf"}      (async por padrão)
    GET  /health

Pipeline: PDF no S3 -> texto (PyMuPDF, ou OCR via Gemini se for escaneado)
       -> chunking semântico via LLM -> chunks.json no S3
       -> embeddings (Gemini) -> upsert no RDS PostgreSQL + pgvector.

Variáveis de ambiente (injetadas pelo Terraform): BUCKET, DB_HOST,
DB_SECRET_ARN, GEMINI_API_KEY.
"""
import hashlib
import logging

from shared import db, gemini, pdf, prompts, s3io, web

logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger(__name__)


def processar(body: dict) -> dict:
    chave = web.chave_obrigatoria(body)
    log.info("Processando s3://%s/%s", s3io.bucket(), chave)

    # 1-2. Ler PDF e extrair texto
    texto = pdf.extrair_texto(s3io.ler(chave))
    if not texto.strip():
        raise web.ErroEntrada(f"Documento vazio ou sem texto extraível: {chave}")
    log.info("Texto extraído: %d caracteres", len(texto))

    # 3. Chunking semântico via LLM
    chunks = gemini.gerar_json(
        f"Processe o seguinte documento e divida em chunks semânticos:\n\n{texto}",
        sistema=prompts.carregar("chunking_system.md"),
        temperatura=0.2,
        max_tokens=16384,
    )
    if isinstance(chunks, dict):
        chunks = chunks.get("chunks", [chunks])
    log.info("%d chunks gerados pelo LLM", len(chunks))

    # 4. Metadados
    for i, chunk in enumerate(chunks, start=1):
        chunk["source_document"] = chave
        chunk.setdefault("chunk_id", i)

    # 5. Gravar chunks.json no S3
    chunks_key = f"chunks/{s3io.nome_base(chave)}/chunks.json"
    s3io.gravar_json(chunks_key, chunks)

    # 6. Embeddings + indexação no pgvector
    vetores = gemini.embeddings([c.get("content", "") for c in chunks])
    documentos = [
        {
            "id": hashlib.md5(f"{chave}_{c['chunk_id']}".encode()).hexdigest(),
            "chunk_id": c["chunk_id"],
            "title": c.get("title", f"Chunk {i}"),
            "content": c.get("content", ""),
            "source_document": chave,
            "metadata": c.get("metadata"),
            "embedding": vetores[i - 1],
        }
        for i, c in enumerate(chunks, start=1)
    ]
    indexados = db.upsert_chunks(documentos)
    log.info("Indexação concluída: %d/%d", indexados, len(documentos))

    return {
        "status": "ok",
        "bucket_key": chave,
        "chunks_path": chunks_key,
        "total_chunks": len(chunks),
        "indexed": indexados > 0,
    }


def health(_body: dict) -> dict:
    return {"status": "ok", "service": "ex01-chunker"}


ROTAS = {
    ("POST", "/process"): (processar, True),
    ("GET", "/health"): (health, False),
}


def handler(event, context):
    return web.executar(event, context, ROTAS)
