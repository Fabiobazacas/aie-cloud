"""Cliente mínimo da API REST do Google Gemini — só urllib, sem SDK.

Substitui o Azure OpenAI do laboratório original: chat/visão/áudio
(generateContent), embeddings (batchEmbedContents) e edição de imagem.

Por que Gemini e não Bedrock: o Learner Lab desta disciplina nega o acesso ao
Bedrock por falta de policy. O Gemini tem free tier sem cartão
(aistudio.google.com/apikey). Cada GRUPO deve criar a própria chave — uma
chave compartilhada pela turma esbarra no rate limit do free tier.

Modelos mudam: se algum devolver 404, liste os disponíveis para a sua chave:
    curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

MODELO_TEXTO = os.environ.get("GEMINI_TEXT_MODEL", "gemini-flash-lite-latest")
MODELO_EMBEDDING = "gemini-embedding-001"
MODELO_IMAGEM = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

# gemini-embedding-001 devolve 3072 dimensões por padrão; pedimos 768 para
# bater com a coluna VECTOR(768) do pgvector (e gastar menos armazenamento).
DIMENSAO_EMBEDDING = 768

STATUS_TRANSITORIOS = {429, 500, 502, 503, 504}


class GeminiError(RuntimeError):
    pass


def _post(caminho: str, corpo: dict, timeout: int = 90, tentativas: int = 4) -> dict:
    chave = os.environ.get("GEMINI_API_KEY")
    if not chave:
        raise GeminiError("GEMINI_API_KEY não definida no ambiente da função.")

    req = urllib.request.Request(
        f"{BASE_URL}/{caminho}",
        data=json.dumps(corpo).encode("utf-8"),
        # Chave no header (não na query string) para não vazar em logs/URLs.
        headers={"Content-Type": "application/json", "x-goog-api-key": chave},
        method="POST",
    )
    for tentativa in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as erro:
            detalhe = erro.read().decode("utf-8", errors="replace")
            if erro.code in STATUS_TRANSITORIOS and tentativa < tentativas - 1:
                time.sleep(2 ** tentativa)  # 1s, 2s, 4s
                continue
            raise GeminiError(f"Gemini respondeu {erro.code}: {detalhe[:500]}") from erro
        except urllib.error.URLError as erro:
            if tentativa < tentativas - 1:
                time.sleep(2 ** tentativa)
                continue
            raise GeminiError(f"Falha de rede ao chamar o Gemini: {erro.reason}") from erro
    raise GeminiError("Gemini: tentativas esgotadas")


def parte_arquivo(dados: bytes, mime_type: str) -> dict:
    """Parte multimodal (imagem, áudio, PDF) enviada inline em base64."""
    return {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(dados).decode("ascii")}}


def _partes(conteudo) -> list[dict]:
    if isinstance(conteudo, str):
        return [{"text": conteudo}]
    return [{"text": p} if isinstance(p, str) else p for p in conteudo]


def _texto_da_resposta(resp: dict) -> str:
    candidatos = resp.get("candidates") or []
    if not candidatos:
        motivo = resp.get("promptFeedback", {}).get("blockReason", "sem candidatos")
        raise GeminiError(f"Gemini não devolveu resposta ({motivo})")
    partes = candidatos[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in partes).strip()


def gerar(
    conteudo,
    sistema: str | None = None,
    temperatura: float = 0.2,
    max_tokens: int = 8192,
    json_mode: bool = False,
    modelo: str | None = None,
) -> str:
    """generateContent. `conteudo` é um texto ou uma lista de textos/partes
    (ex.: [parte_arquivo(png, "image/png"), "Transcreva esta página"])."""
    config = {"temperature": temperatura, "maxOutputTokens": max_tokens}
    if json_mode:
        config["responseMimeType"] = "application/json"
    corpo = {"contents": [{"role": "user", "parts": _partes(conteudo)}], "generationConfig": config}
    if sistema:
        corpo["systemInstruction"] = {"parts": [{"text": sistema}]}
    resp = _post(f"{modelo or MODELO_TEXTO}:generateContent", corpo)
    return _texto_da_resposta(resp)


def extrair_json(texto: str):
    """Faz parse de JSON mesmo que o modelo tenha embrulhado em ```json ... ```."""
    limpo = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip())
    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        achado = re.search(r"(\{.*\}|\[.*\])", limpo, re.DOTALL)
        if achado:
            return json.loads(achado.group(1))
        raise


def gerar_json(conteudo, **kwargs):
    return extrair_json(gerar(conteudo, json_mode=True, **kwargs))


def embeddings(textos: list[str], tipo: str = "RETRIEVAL_DOCUMENT", lote: int = 50) -> list[list[float]]:
    """Embeddings de 768 dimensões. tipo: RETRIEVAL_DOCUMENT (indexar) ou
    RETRIEVAL_QUERY (a pergunta do usuário) — o Gemini otimiza cada um."""
    vetores: list[list[float]] = []
    for i in range(0, len(textos), lote):
        pedidos = [
            {
                "model": f"models/{MODELO_EMBEDDING}",
                "content": {"parts": [{"text": t}]},
                "taskType": tipo,
                "outputDimensionality": DIMENSAO_EMBEDDING,
            }
            for t in textos[i:i + lote]
        ]
        resp = _post(f"{MODELO_EMBEDDING}:batchEmbedContents", {"requests": pedidos})
        vetores.extend(e["values"] for e in resp["embeddings"])
    return vetores


def gerar_imagem(prompt: str, imagem: bytes, mime_type: str) -> bytes:
    """Image-to-image: a foto do produto entra como referência e o prompt
    descreve a peça de campanha. Levanta GeminiError se o modelo não devolver
    imagem (free tier sem acesso, bloqueio de segurança, etc.)."""
    corpo = {
        "contents": [{"role": "user", "parts": [{"text": prompt}, parte_arquivo(imagem, mime_type)]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    resp = _post(f"{MODELO_IMAGEM}:generateContent", corpo, timeout=120)
    candidatos = resp.get("candidates") or []
    partes = candidatos[0].get("content", {}).get("parts", []) if candidatos else []
    for parte in partes:
        dados = parte.get("inlineData") or parte.get("inline_data")
        if dados and dados.get("data"):
            return base64.b64decode(dados["data"])
    texto = " ".join(p.get("text", "") for p in partes).strip()
    raise GeminiError(f"O modelo {MODELO_IMAGEM} não devolveu imagem. Resposta: {texto[:300] or resp}")
