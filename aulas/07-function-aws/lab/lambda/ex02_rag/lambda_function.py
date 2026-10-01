"""Exercício 02 — RAG (pergunta -> resposta fundamentada nos documentos). Lambda na VPC.

    POST /rag/query   {"question": "Quem é o proprietário do imóvel?"}
    GET  /rag/chunks  (lista os chunks indexados — útil para depurar)

Pré-requisito: Exercício 01 executado (chunks no pgvector).

Pipeline: embedding da pergunta -> busca híbrida (vetorial + palavra-chave,
fundidas por RRF) no pgvector -> top N chunks + pergunta -> LLM com o prompt
de RAG -> resposta com fontes.

Variáveis de ambiente: DB_HOST, DB_SECRET_ARN, GEMINI_API_KEY, RAG_TOP_N (opcional).
"""
import json
import logging
import os

from shared import db, gemini, prompts, web

logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger(__name__)

TOP_N = int(os.environ.get("RAG_TOP_N", "5"))


def consultar(body: dict) -> dict:
    pergunta = (body.get("question") or "").strip()
    if not pergunta:
        raise web.ErroEntrada("Campo 'question' é obrigatório. Envie: {\"question\": \"sua pergunta\"}")
    log.info("Pergunta: %s", pergunta)

    # 1-2. Embedding da pergunta e busca dos chunks relevantes
    embedding = gemini.embeddings([pergunta], tipo="RETRIEVAL_QUERY")[0]
    encontrados = db.busca_hibrida(pergunta, embedding, TOP_N)

    if not encontrados:
        return {
            "answer": "Não há documentos indexados na base de conhecimento. Execute o Exercício 01 primeiro.",
            "confidence": "low",
            "sources": [],
            "found_in_context": False,
            "chunks_found": 0,
        }

    # 3. Montar o contexto com os chunks
    contexto = "\n\n---\n\n".join(
        f"[CHUNK {c['chunk_id']} - {c.get('title') or 'Sem título'}]\n{c['content']}" for c in encontrados
    )
    mensagem = (
        f"## Contexto (chunks recuperados da base de conhecimento):\n\n{contexto}\n\n---\n\n"
        f"## Pergunta do usuário:\n{pergunta}"
    )

    # 4. LLM com o prompt de RAG
    texto = gemini.gerar(
        mensagem, sistema=prompts.carregar("rag_system.md"), temperatura=0.1, json_mode=True, max_tokens=4096
    )
    try:
        resultado = gemini.extrair_json(texto)
    except json.JSONDecodeError:
        resultado = {"answer": texto, "confidence": "medium", "sources": [], "found_in_context": True}

    # 5. Metadados da busca
    resultado["chunks_found"] = len(encontrados)
    resultado["chunks_scores"] = [
        {"chunk_id": c["chunk_id"], "title": c["title"], "score": round(c["score"], 4)} for c in encontrados
    ]
    return resultado


def listar(_params: dict) -> dict:
    chunks = db.listar_chunks()
    return {"total": len(chunks), "chunks": chunks}


ROTAS = {
    ("POST", "/rag/query"): (consultar, False),
    ("GET", "/rag/chunks"): (listar, False),
}


def handler(event, context):
    return web.executar(event, context, ROTAS)
