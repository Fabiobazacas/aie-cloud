"""Ciclo do agente — uma volta processa UMA nota e mostra um dos três
desfechos: extraído, duplicado ou exceção.

Roda 3x seguidas (contra as notas semeadas por disparador.py --semear) pra
demonstrar os três estados, um por vez — igual ao roteiro do slide 42.

Uso:
    python ciclo_do_agente.py --uma-volta
    python ciclo_do_agente.py --uma-volta --mock=false   # usa Bedrock de verdade
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agente import cliente_bedrock  # noqa: E402
from api.modelos import Estado  # noqa: E402
from api.servicos import fila, memoria  # noqa: E402

LIMIAR_CONFIANCA = 0.6


def uma_volta(mock: bool = True) -> None:
    nota = fila.proxima_nao_manipulada()
    if nota is None:
        print("nenhuma nota pendente — rode disparador.py --semear primeiro")
        return

    if nota["estado"] == Estado.DUPLICADA.value:
        print(f"[duplicado] nota {nota['id']} ({nota['fornecedor']}) — {nota['motivo']}")
        fila.marcar_manipulada(nota["id"])
        return

    regras = memoria.listar_aprovadas()
    decisao = cliente_bedrock.classificar_nota(nota, regras, mock=mock)

    if decisao["confianca"] >= LIMIAR_CONFIANCA and decisao["categoria_final"]:
        fila.marcar_processada(
            nota["id"], decisao["categoria_final"], decisao["regra_aplicada"], decisao["motivo"]
        )
        print(f"[extraído] nota {nota['id']} → categoria={decisao['categoria_final']} · {decisao['motivo']}")
    else:
        fila.marcar_excecao(nota["id"], decisao["motivo"])
        texto_proposta = cliente_bedrock.propor_regra_para_excecao(nota, mock=mock)
        proposta_id = memoria.propor(texto_proposta, origem="deva", nota_id=nota["id"])
        print(f"[exceção] nota {nota['id']} → {decisao['motivo']}")
        print(f"          proposta enfileirada em MEMORIA-PENDENTE.md (id={proposta_id}): {texto_proposta}")

    fila.marcar_manipulada(nota["id"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--uma-volta", action="store_true", required=True)
    parser.add_argument("--mock", type=lambda v: v.lower() != "false", default=True, help="use --mock=false pra chamar o Bedrock de verdade")
    args = parser.parse_args()
    uma_volta(mock=args.mock)
