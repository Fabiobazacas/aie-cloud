"""Cliente do agente "Deva" — Amazon Bedrock (Claude), com fallback --mock.

Em modo --mock (padrão do lab, custo zero) a "decisão" vem de uma heurística
determinística, sem nenhuma chamada de rede — suficiente pra demonstrar os
três estados (processada/duplicada/exceção) numa sala sem depender do
Bedrock estar habilitado. Em modo real, troca por uma chamada
`bedrock-runtime` ao `anthropic.claude-3-haiku-20240307-v1:0`.
"""
from __future__ import annotations

import json
from pathlib import Path

MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
OPENAPI_PATH = Path(__file__).resolve().parent / "openapi-agente.json"


def carregar_ferramentas_permitidas() -> list[dict]:
    """Lê openapi-agente.json e devolve só as operações com x-agente-permitido=true,
    já no formato toolSpec do Bedrock Converse API — a MESMA fronteira que a
    API reforça no header X-Auditor, mas do lado do que o agente sequer enxerga."""
    spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    ferramentas = []
    for caminho, operacoes in spec["paths"].items():
        for metodo, operacao in operacoes.items():
            if not operacao.get("x-agente-permitido"):
                continue
            ferramentas.append({
                "toolSpec": {
                    "name": operacao["operationId"],
                    "description": operacao["summary"],
                    "inputSchema": {"json": {"type": "object", "properties": {}, "additionalProperties": True}},
                }
            })
    return ferramentas


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


def classificar_nota(nota: dict, regras_aprovadas: list[str], mock: bool = True) -> dict:
    """Decide a categoria final da nota com base nas regras já aprovadas (MEMORY.md).
    confianca < 0.6 é o sinal pra ciclo_do_agente.py tratar como exceção."""
    if mock:
        return _classificar_mock(nota, regras_aprovadas)

    import boto3

    bedrock = boto3.client("bedrock-runtime")
    prompt = (
        "Você é o Deva, um agente que classifica notas fiscais de despesas corporativas.\n"
        f"Regras já aprovadas (aplique-as literalmente, não invente exceções):\n"
        + "\n".join(f"- {r}" for r in regras_aprovadas)
        + f"\n\nNota: fornecedor={nota['fornecedor']!r}, descricao={nota['descricao']!r}, "
        f"categoria_solicitada={nota['categoria_solicitada']!r}, valor={nota['valor']}.\n\n"
        "Responda SOMENTE com um JSON: "
        '{"categoria_final": str|null, "regra_aplicada": str|null, "motivo": str, "confianca": float 0-1}. '
        "confianca < 0.6 se nenhuma regra aprovada cobrir claramente o caso."
    )
    resposta = bedrock.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 500, "temperature": 0},
    )
    texto = resposta["output"]["message"]["content"][0]["text"]
    return json.loads(texto)


def propor_regra_para_excecao(nota: dict, mock: bool = True) -> str:
    """Texto de proposta de regra quando a nota vira exceção — vai para
    MEMORIA-PENDENTE.md via POST /memoria/propor com origem='deva'."""
    if mock:
        return f"Notas de '{nota['fornecedor']}' com descrição parecida com '{nota['descricao']}' deveriam ser categorizadas como {nota['categoria_solicitada']}?"

    import boto3

    bedrock = boto3.client("bedrock-runtime")
    prompt = (
        f"A nota de {nota['fornecedor']} ({nota['descricao']}, categoria solicitada "
        f"{nota['categoria_solicitada']}) não bate com nenhuma regra aprovada. "
        "Escreva, em uma frase objetiva, uma PROPOSTA de regra para este caso — "
        "proposta, não decisão; um humano ainda vai revisar."
    )
    resposta = bedrock.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 200, "temperature": 0.3},
    )
    return resposta["output"]["message"]["content"][0]["text"].strip()
