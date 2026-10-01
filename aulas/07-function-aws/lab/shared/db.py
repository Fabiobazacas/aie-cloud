"""Banco vetorial: RDS PostgreSQL + pgvector (substitui o Azure AI Search).

Usado só pelos Exercícios 01 (indexar) e 02 (consultar). A senha do banco vem
do Secrets Manager (manage_master_user_password no Terraform) — nunca fica no
código nem em variável de ambiente.

Nota: não usamos o pacote `pgvector` do Python. Mandamos o vetor como texto
'[0.1,0.2,...]' com cast ::vector no SQL — uma dependência a menos para
empacotar na Lambda, e funciona mesmo antes de a extensão existir.
"""
from __future__ import annotations

import json
import os
import time

import boto3
import psycopg2
from botocore.config import Config

DIMENSAO = 768

# Timeouts curtos e sem retry: se o Secrets Manager não for alcançável da VPC
# (NAT/DNS), falha em ~10s com erro claro em vez de queimar o timeout inteiro.
_sm = boto3.client("secretsmanager", config=Config(connect_timeout=10, read_timeout=10, retries={"max_attempts": 1}))
_conn = None  # reaproveitado entre invocações num mesmo container "quente"
_schema_ok = False

SCHEMA_SQL = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    chunk_id INT,
    title TEXT,
    content TEXT NOT NULL,
    source_document TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR({DIMENSAO})
);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
"""

# Texto indexado para a busca por palavra-chave (metade "híbrida" da busca)
TSV = "to_tsvector('portuguese', coalesce(title, '') || ' ' || content)"


def conectar():
    global _conn
    if _conn is not None and _conn.closed == 0:
        return _conn
    print("[db] buscando segredo no Secrets Manager")
    t0 = time.time()
    segredo = json.loads(_sm.get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])["SecretString"])
    print(f"[db] segredo em {time.time() - t0:.1f}s — conectando em {os.environ['DB_HOST']}")
    _conn = psycopg2.connect(
        host=os.environ["DB_HOST"], dbname="ragdb",
        user=segredo["username"], password=segredo["password"],
        connect_timeout=10,
    )
    return _conn


def garantir_schema() -> None:
    """Cria extensão, tabela e índice HNSW se ainda não existirem (idempotente)."""
    global _schema_ok
    if _schema_ok:
        return
    conn = conectar()
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    conn.commit()
    _schema_ok = True


def _vetor(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in v) + "]"


def upsert_chunks(documentos: list[dict]) -> int:
    garantir_schema()
    conn = conectar()
    try:
        with conn.cursor() as cur:
            for d in documentos:
                cur.execute(
                    """
                    INSERT INTO chunks (id, chunk_id, title, content, source_document, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (id) DO UPDATE SET
                        chunk_id = EXCLUDED.chunk_id, title = EXCLUDED.title, content = EXCLUDED.content,
                        source_document = EXCLUDED.source_document, metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """,
                    (d["id"], d["chunk_id"], d["title"], d["content"], d["source_document"],
                     json.dumps(d.get("metadata") or {}), _vetor(d["embedding"])),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return len(documentos)


def _linhas_para_dicts(linhas) -> list[dict]:
    return [
        {"id": i, "chunk_id": c, "title": t, "content": txt, "source_document": s, "score": float(score)}
        for i, c, t, txt, s, score in linhas
    ]


def busca_vetorial(embedding: list[float], n: int) -> list[dict]:
    garantir_schema()
    with conectar().cursor() as cur:
        cur.execute(
            """
            SELECT id, chunk_id, title, content, source_document, 1 - (embedding <=> %s::vector) AS score
            FROM chunks ORDER BY embedding <=> %s::vector LIMIT %s
            """,
            (_vetor(embedding), _vetor(embedding), n),
        )
        return _linhas_para_dicts(cur.fetchall())


def busca_texto(consulta: str, n: int) -> list[dict]:
    garantir_schema()
    with conectar().cursor() as cur:
        cur.execute(
            f"""
            SELECT id, chunk_id, title, content, source_document,
                   ts_rank({TSV}, plainto_tsquery('portuguese', %s)) AS score
            FROM chunks WHERE {TSV} @@ plainto_tsquery('portuguese', %s)
            ORDER BY score DESC LIMIT %s
            """,
            (consulta, consulta, n),
        )
        return _linhas_para_dicts(cur.fetchall())


def busca_hibrida(consulta: str, embedding: list[float], n: int, k: int = 60) -> list[dict]:
    """Vetorial + palavra-chave combinadas por Reciprocal Rank Fusion (RRF):
    score(doc) = soma de 1/(k + posição) em cada lista. É o que o Azure AI
    Search faz por baixo dos panos na "hybrid search"."""
    listas = [busca_vetorial(embedding, n * 2), busca_texto(consulta, n * 2)]
    fundidos: dict[str, dict] = {}
    for lista in listas:
        for posicao, item in enumerate(lista, start=1):
            entrada = fundidos.setdefault(item["id"], {**item, "score": 0.0})
            entrada["score"] += 1.0 / (k + posicao)
    return sorted(fundidos.values(), key=lambda d: d["score"], reverse=True)[:n]


def listar_chunks(limite: int = 50) -> list[dict]:
    garantir_schema()
    with conectar().cursor() as cur:
        cur.execute(
            "SELECT id, chunk_id, title, source_document FROM chunks ORDER BY source_document, chunk_id LIMIT %s",
            (limite,),
        )
        return [{"id": i, "chunk_id": c, "title": t, "source_document": s} for i, c, t, s in cur.fetchall()]
