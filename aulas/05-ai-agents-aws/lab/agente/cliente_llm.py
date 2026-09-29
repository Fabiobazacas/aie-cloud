"""Cliente do agente "Deva" — 2 provedores: mock (padrão, custo zero) e
gemini (Google Gemini, free tier).

Por que Gemini e não Bedrock: confirmamos numa sessão real do AWS Academy
Learner Lab que `aws bedrock list-foundation-models` devolve
`AccessDeniedException` por FALTA DE POLICY (não por modelo desabilitado) —
essa conta não libera Bedrock de jeito nenhum. O Google Gemini tem free tier
sem cartão de crédito (aistudio.google.com/apikey) e cobre os três usos que
este módulo precisa (texto, e o mesmo provedor serve visão e embeddings nos
outros pontos do pipeline — ver aulas/04-servicos-cognitivos-aws/exercicios.md).

Cada GRUPO deve criar sua própria chave gratuita (GEMINI_API_KEY) — uma
chave única compartilhada pela turma inteira esbarra no rate limit do free
tier quando vários grupos chamam ao mesmo tempo.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

# "-latest" em vez de um nome versionado: o Google aposenta versões de
# modelo periodicamente (gemini-2.0-flash já voltou 404 num teste real).
# https://ai.google.dev/gemini-api/docs/models
MODEL_ID_GEMINI = "gemini-flash-latest"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID_GEMINI}:generateContent"

OPENAPI_PATH = Path(__file__).resolve().parent / "openapi-agente.json"

PROVEDORES = ("mock", "gemini")

# Status transitórios do Gemini — o free tier volta 503 (sobrecarga) com
# alguma frequência, principalmente com a turma inteira chamando junto.
STATUS_TRANSITORIOS = {429, 500, 502, 503, 504}
TENTATIVAS = 4


def carregar_ferramentas_permitidas() -> list[dict]:
    """Lê openapi-agente.json e devolve só as operações com x-agente-permitido=true
    — a mesma fronteira que a API reforça no header X-Auditor, mas do lado do
    que o agente sequer enxerga. (Documentação/uso didático — classificar_nota
    não faz tool-use de verdade; ver Exercício 4 pra estender isso.)"""
    spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    ferramentas = []
    for _caminho, operacoes in spec["paths"].items():
        for _metodo, operacao in operacoes.items():
            if operacao.get("x-agente-permitido"):
                ferramentas.append({"name": operacao["operationId"], "description": operacao["summary"]})
    return ferramentas


def _validar_provedor(provedor: str) -> None:
    if provedor not in PROVEDORES:
        raise ValueError(f"provedor deve ser um de {PROVEDORES}, recebi {provedor!r}")


def _classificar_mock(nota: dict, regras_aprovadas: list[str]) -> dict:
    descricao = nota["descricao"].lower()
    for regra in regras_aprovadas:
        for palavra in descricao.split():
            if len(palavra) > 4 and palavra in regra.lower():
                return {
                    "categoria_final": nota["categoria_solicitada"],
                    "regra_aplicada": regra,
                    "motivo": f"regra aprovada bate com '{palavra}' na descrição",
                    "confianca": 0.9,
                }
    return {
        "categoria_final": None,
        "regra_aplicada": None,
        "motivo": "nenhuma regra aprovada cobre esta descrição — nenhum precedente encontrado",
        "confianca": 0.3,
    }


def _prompt_classificacao(nota: dict, regras_aprovadas: list[str]) -> str:
    return (
        "Você é o Deva, um agente que classifica notas fiscais de despesas corporativas.\n"
        "Regras já aprovadas (aplique-as literalmente, não invente exceções):\n"
        + "\n".join(f"- {r}" for r in regras_aprovadas)
        + f"\n\nNota: fornecedor={nota['fornecedor']!r}, descricao={nota['descricao']!r}, "
        f"categoria_solicitada={nota['categoria_solicitada']!r}, valor={nota['valor']}.\n\n"
        "Responda SOMENTE com um JSON, sem markdown, sem texto antes ou depois: "
        '{"categoria_final": str|null, "regra_aplicada": str|null, "motivo": str, "confianca": float 0-1}. '
        "confianca < 0.6 se nenhuma regra aprovada cobrir claramente o caso."
    )


def _chamar_gemini(prompt: str, temperatura: float, max_tokens: int) -> str:
    import requests

    chave = os.environ.get("GEMINI_API_KEY")
    if not chave:
        raise RuntimeError(
            "GEMINI_API_KEY não definida. Crie sua chave gratuita em "
            "https://aistudio.google.com/apikey e rode: export GEMINI_API_KEY=<sua-chave>"
        )
    corpo = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperatura, "maxOutputTokens": max_tokens},
    }
    for tentativa in range(TENTATIVAS):
        resp = requests.post(GEMINI_URL, params={"key": chave}, json=corpo, timeout=30)
        if resp.status_code in STATUS_TRANSITORIOS and tentativa < TENTATIVAS - 1:
            time.sleep(2 ** tentativa)  # 1s, 2s, 4s
            continue
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def classificar_nota(nota: dict, regras_aprovadas: list[str], provedor: str = "mock") -> dict:
    """Decide a categoria final da nota com base nas regras já aprovadas (MEMORY.md).
    confianca < 0.6 é o sinal pra ciclo_do_agente.py tratar como exceção."""
    _validar_provedor(provedor)
    if provedor == "mock":
        return _classificar_mock(nota, regras_aprovadas)

    texto = _chamar_gemini(_prompt_classificacao(nota, regras_aprovadas), temperatura=0, max_tokens=500)
    texto = texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(texto)


def propor_regra_para_excecao(nota: dict, provedor: str = "mock") -> str:
    """Texto de proposta de regra quando a nota vira exceção — vai para
    MEMORIA-PENDENTE.md via POST /memoria/propor com origem='deva'."""
    _validar_provedor(provedor)
    if provedor == "mock":
        return f"Notas de '{nota['fornecedor']}' com descrição parecida com '{nota['descricao']}' deveriam ser categorizadas como {nota['categoria_solicitada']}?"

    prompt = (
        f"A nota de {nota['fornecedor']} ({nota['descricao']}, categoria solicitada "
        f"{nota['categoria_solicitada']}) não bate com nenhuma regra aprovada. "
        "Escreva, em uma frase objetiva, uma PROPOSTA de regra para este caso — "
        "proposta, não decisão; um humano ainda vai revisar."
    )
    return _chamar_gemini(prompt, temperatura=0.3, max_tokens=200)
