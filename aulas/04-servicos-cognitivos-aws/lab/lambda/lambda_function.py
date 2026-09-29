"""Lambda de RAG da Quantum Commerce — aula 4 (AWS + Google Gemini).

Rotas (API Gateway HTTP API, payload format 2.0):
    GET  /health
    GET  /setup-db
    GET  /status
    GET  /transcrever?bucket_key=<pdf no bucket de documentos>
    GET  /indexar?bucket_key=<mesmo pdf, já transcrito por /transcrever>
    POST /perguntar {"pergunta": "..."}

Variáveis de ambiente (injetadas pelo Terraform — nunca hardcoded aqui):
    DOCS_BUCKET     — bucket S3 com os PDFs de teste
    DB_HOST         — endpoint do RDS
    DB_SECRET_ARN   — ARN do secret do Secrets Manager (usuário/senha do RDS)
    GEMINI_API_KEY  — chave do grupo (aistudio.google.com/apikey)

Sem credenciais no código: o acesso a S3/Secrets Manager vem do LabRole
(execution role da própria função); a única chave de verdade (Gemini, que é
uma API externa) chega como variável de ambiente, nunca escrita aqui.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request

import boto3
import fitz  # PyMuPDF
import psycopg2
from botocore.config import Config
from pgvector.psycopg2 import register_vector

DOCS_BUCKET = os.environ["DOCS_BUCKET"]
DB_HOST = os.environ["DB_HOST"]
DB_SECRET_ARN = os.environ["DB_SECRET_ARN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# Histórico real desta aula: gemini-2.0-flash -> 404 (aposentado);
# gemini-flash-latest e o gemini-3.8-flash indicado no erro -> 503 "high
# demand" (o alias sem sufixo -lite concentra tráfego de quem não fixa
# versão). gemini-flash-lite-latest respondeu 200 num teste real. Se
# isso mudar de novo: `curl "https://generativelanguage.googleapis.com/
# v1beta/models?key=$GEMINI_API_KEY"` lista o que está disponível/ativo
# pra sua chave agora.
MODEL_TEXTO = "gemini-flash-lite-latest"
# text-embedding-004 também aposentou (404 real: "not found ... or is not
# supported for embedContent"). gemini-embedding-001 é o substituto — mas
# por padrão devolve vetores maiores; outputDimensionality=768 no corpo do
# request (ver gerar_embedding) pede explicitamente o tamanho que bate com
# a coluna embedding VECTOR(768) já provisionada, sem precisar migrar o
# schema. Confirmado com teste real: 768 valores exatos.
MODEL_EMBED = "gemini-embedding-001"
DIMENSAO_EMBEDDING = 768
TAMANHO_CHUNK = 500
SOBREPOSICAO_CHUNK = 50
TOP_K = 5

_s3 = boto3.client("s3")
# connect/read_timeout curtos e sem retry: se o Secrets Manager não for
# alcançável daqui (NAT/DNS/SG), falha em ~10s com um erro claro em vez de
# consumir os 30s inteiros do timeout da Lambda em silêncio.
_sm = boto3.client("secretsmanager", config=Config(connect_timeout=10, read_timeout=10, retries={"max_attempts": 1}))
_db_conn = None  # cache entre invocações num mesmo container "quente"


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


# Status transitórios do Gemini (sobrecarga do free tier, comum com a
# turma inteira chamando junto). Só 1 retry curto: a Lambda tem 30s de
# timeout no total, e essa função roda uma vez por página do PDF.
STATUS_TRANSITORIOS = {429, 500, 502, 503, 504}


def _gemini_post(url: str, corpo: dict) -> dict:
    dados = json.dumps(corpo).encode("utf-8")
    req = urllib.request.Request(
        f"{url}?key={GEMINI_API_KEY}",
        data=dados,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for tentativa in range(2):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as erro:
            detalhe = erro.read().decode("utf-8", errors="replace")
            if erro.code in STATUS_TRANSITORIOS and tentativa == 0:
                time.sleep(1)
                continue
            raise RuntimeError(f"Gemini respondeu {erro.code}: {detalhe}") from erro


def pagina_para_base64_png(pagina, zoom: float = 2.0) -> str:
    pix = pagina.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")


def transcrever_pagina(imagem_b64: str) -> str:
    corpo = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/png", "data": imagem_b64}},
            {"text": "Transcreva TODO o texto visível nesta página, na ordem de leitura. Preserve tabelas como texto estruturado. Não resuma, não comente — só a transcrição."},
        ]}],
        "generationConfig": {"maxOutputTokens": 2000},
    }
    resp = _gemini_post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_TEXTO}:generateContent", corpo
    )
    return resp["candidates"][0]["content"]["parts"][0]["text"]


def gerar_embedding(texto: str) -> list[float]:
    corpo = {"content": {"parts": [{"text": texto}]}, "outputDimensionality": DIMENSAO_EMBEDDING}
    resp = _gemini_post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_EMBED}:embedContent", corpo
    )
    return resp["embedding"]["values"]


def _chunk(texto: str, tamanho: int = TAMANHO_CHUNK, sobreposicao: int = SOBREPOSICAO_CHUNK) -> list[str]:
    chunks = []
    inicio = 0
    while inicio < len(texto):
        chunks.append(texto[inicio:inicio + tamanho])
        inicio += tamanho - sobreposicao
    return [c for c in chunks if c.strip()]


def _conectar_db():
    global _db_conn
    if _db_conn is not None and _db_conn.closed == 0:
        return _db_conn

    # Logs por etapa: se a Lambda travar nos 30s do timeout, o CloudWatch
    # mostra até onde chegou — Secrets Manager (NAT/DNS) ou o próprio RDS
    # (security group/subnet) são causas bem diferentes de "timeout".
    print(f"[_conectar_db] buscando segredo {DB_SECRET_ARN}")
    t0 = time.time()
    segredo = json.loads(_sm.get_secret_value(SecretId=DB_SECRET_ARN)["SecretString"])
    print(f"[_conectar_db] segredo obtido em {time.time() - t0:.1f}s — conectando em {DB_HOST}:5432")

    t1 = time.time()
    _db_conn = psycopg2.connect(
        host=DB_HOST, dbname="ragdb",
        user=segredo["username"], password=segredo["password"],
        connect_timeout=10,
    )
    print(f"[_conectar_db] conectado ao RDS em {time.time() - t1:.1f}s")

    register_vector(_db_conn)
    return _db_conn


def rota_health(_params: dict) -> dict:
    return _response(200, {"status": "ok", "service": "qc-rag"})


def rota_setup_db(_params: dict) -> dict:
    # Mesma lógica de scripts/criar_tabela.py — mas rodando aqui, dentro da
    # VPC, porque o RDS é privado de propósito (publicly_accessible=false)
    # e o CloudShell não tem rota nenhuma pra essa subnet. Só a Lambda
    # alcança o banco diretamente. Compare com criar_tabela.py: lá o
    # segredo inteiro vai pro log (falha proposital); aqui ele nunca sai
    # de _conectar_db().
    conn = _conectar_db()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documentos_qc (
            id SERIAL PRIMARY KEY,
            fonte TEXT NOT NULL,
            pagina INT NOT NULL,
            chunk_texto TEXT NOT NULL,
            embedding VECTOR(768)
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS documentos_qc_embedding_idx
        ON documentos_qc USING hnsw (embedding vector_cosine_ops);
    """)
    conn.commit()
    return _response(200, {"status": "schema pronto"})


def rota_status(_params: dict) -> dict:
    conn = _conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT fonte) FROM documentos_qc")
    total_chunks, total_fontes = cur.fetchone()
    return _response(200, {"total_chunks": total_chunks, "total_fontes": total_fontes})


def rota_transcrever(params: dict) -> dict:
    bucket_key = params.get("bucket_key")
    if not bucket_key:
        return _response(400, {"erro": "informe bucket_key"})

    obj = _s3.get_object(Bucket=DOCS_BUCKET, Key=bucket_key)
    pdf_bytes = obj["Body"].read()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    paginas = [transcrever_pagina(pagina_para_base64_png(p)) for p in doc]

    return _response(200, {"paginas": paginas, "total_paginas": len(paginas)})


def rota_indexar(params: dict) -> dict:
    bucket_key = params.get("bucket_key")
    if not bucket_key:
        return _response(400, {"erro": "informe bucket_key"})

    obj = _s3.get_object(Bucket=DOCS_BUCKET, Key=bucket_key)
    pdf_bytes = obj["Body"].read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    conn = _conectar_db()
    cur = conn.cursor()
    chunks_indexados = 0

    for num_pagina, pagina in enumerate(doc, start=1):
        texto = transcrever_pagina(pagina_para_base64_png(pagina))
        for chunk_texto in _chunk(texto):
            # Idempotência: não reprocessa um chunk já indexado desta fonte/página.
            cur.execute(
                "SELECT 1 FROM documentos_qc WHERE fonte = %s AND pagina = %s AND chunk_texto = %s",
                (bucket_key, num_pagina, chunk_texto),
            )
            if cur.fetchone():
                continue
            embedding = gerar_embedding(chunk_texto)
            # ::vector explícito: o psycopg2 manda a lista Python como array
            # (numeric[]), não como o tipo vector do pgvector — sem o cast,
            # um ORDER BY embedding <=> %s adiante quebra por falta de
            # operador (funciona sem isso só aqui, por coincidência: o
            # Postgres converte array->vector sozinho quando o destino é uma
            # coluna tipada, mas não em contexto de operador).
            cur.execute(
                "INSERT INTO documentos_qc (fonte, pagina, chunk_texto, embedding) VALUES (%s, %s, %s, %s::vector)",
                (bucket_key, num_pagina, chunk_texto, embedding),
            )
            chunks_indexados += 1

    conn.commit()
    return _response(200, {"chunks_indexados": chunks_indexados, "total_paginas": len(doc)})


def rota_perguntar(body: dict) -> dict:
    pergunta = (body or {}).get("pergunta")
    if not pergunta:
        return _response(400, {"erro": "informe 'pergunta' no body"})

    embedding_pergunta = gerar_embedding(pergunta)

    conn = _conectar_db()
    cur = conn.cursor()
    # ::vector explícito pelo mesmo motivo do INSERT em rota_indexar — sem
    # ele, dá "operator does not exist: vector <=> numeric[]" (erro real).
    cur.execute(
        "SELECT fonte, pagina, chunk_texto FROM documentos_qc ORDER BY embedding <=> %s::vector LIMIT %s",
        (embedding_pergunta, TOP_K),
    )
    linhas = cur.fetchall()

    if not linhas:
        return _response(200, {
            "resposta": "Não encontrei nenhum documento indexado ainda. Rode /indexar primeiro.",
            "fontes": [],
        })

    contexto = "\n\n".join(f"[{fonte} p.{pagina}] {texto}" for fonte, pagina, texto in linhas)
    prompt = (
        "Responda a pergunta do usuário usando SOMENTE o contexto abaixo. "
        "Se a resposta não estiver no contexto, diga que não sabe.\n\n"
        f"Contexto:\n{contexto}\n\nPergunta: {pergunta}"
    )
    resp = _gemini_post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_TEXTO}:generateContent",
        {"contents": [{"parts": [{"text": prompt}]}]},
    )
    resposta = resp["candidates"][0]["content"]["parts"][0]["text"]
    fontes = [{"fonte": fonte, "pagina": pagina} for fonte, pagina, _ in linhas]

    return _response(200, {"resposta": resposta, "fontes": fontes})


def handler(event, context):
    path = event.get("rawPath", "")
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    params = event.get("queryStringParameters") or {}

    try:
        if path.endswith("/health"):
            return rota_health(params)
        if path.endswith("/setup-db"):
            return rota_setup_db(params)
        if path.endswith("/status"):
            return rota_status(params)
        if path.endswith("/transcrever"):
            return rota_transcrever(params)
        if path.endswith("/indexar"):
            return rota_indexar(params)
        if path.endswith("/perguntar") and method == "POST":
            body = json.loads(event.get("body") or "{}")
            return rota_perguntar(body)
    except Exception as erro:  # noqa: BLE001 — resposta de erro genérica é intencional aqui
        return _response(500, {"erro": str(erro)})

    return _response(404, {"erro": "rota não encontrada"})
