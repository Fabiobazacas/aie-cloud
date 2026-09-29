"""Notas + fila de exceções — a fronteira em código, não em prosa.

A regra que mais importa deste módulo: uma exceção NUNCA volta sozinha para
"processada" se quem pediu a transição for o próprio agente (`por == "deva"`).
Só um humano libera, via `liberar_excecao`.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ..modelos import Estado
from . import armazenamento as armz

NOTAS_JSON = "notas.json"


class TransicaoProibida(Exception):
    """O agente tentou fazer uma transição de estado que só um humano pode fazer."""


def _hash_nota(fornecedor: str, valor: float, descricao: str) -> str:
    chave = f"{fornecedor.strip().lower()}|{valor:.2f}|{descricao.strip().lower()}"
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()[:16]


def _carregar() -> list[dict]:
    return armz.ler_json(NOTAS_JSON, [])


def _salvar(notas: list[dict]) -> None:
    armz.escrever_json(NOTAS_JSON, notas)


def inserir_nota(fornecedor: str, descricao: str, categoria_solicitada: str, valor: float, nota_id: str) -> dict:
    notas = _carregar()
    hash_nota = _hash_nota(fornecedor, valor, descricao)
    duplicada = any(n["hash"] == hash_nota and n["id"] != nota_id for n in notas)

    registro = {
        "id": nota_id,
        "fornecedor": fornecedor,
        "descricao": descricao,
        "categoria_solicitada": categoria_solicitada,
        "valor": valor,
        "hash": hash_nota,
        "estado": Estado.DUPLICADA.value if duplicada else Estado.PENDENTE.value,
        "categoria_final": None,
        "regra_aplicada": None,
        "motivo": "hash igual a uma nota já recebida" if duplicada else None,
        "manipulada": False,
    }
    notas.append(registro)
    _salvar(notas)
    return registro


def listar_notas(estado: Estado | None = None) -> list[dict]:
    notas = _carregar()
    if estado is None:
        return notas
    return [n for n in notas if n["estado"] == estado.value]


def obter_nota(nota_id: str) -> dict:
    for n in _carregar():
        if n["id"] == nota_id:
            return n
    raise KeyError(f"nota {nota_id!r} não encontrada")


def _atualizar(nota_id: str, **campos) -> dict:
    notas = _carregar()
    for n in notas:
        if n["id"] == nota_id:
            n.update(campos)
            _salvar(notas)
            return n
    raise KeyError(f"nota {nota_id!r} não encontrada")


def marcar_processada(nota_id: str, categoria_final: str, regra_aplicada: str | None, motivo: str) -> dict:
    return _atualizar(
        nota_id,
        estado=Estado.PROCESSADA.value,
        categoria_final=categoria_final,
        regra_aplicada=regra_aplicada,
        motivo=motivo,
    )


def marcar_excecao(nota_id: str, motivo: str) -> dict:
    return _atualizar(nota_id, estado=Estado.EXCECAO.value, motivo=motivo)


def liberar_excecao(nota_id: str, auditor: str, categoria_final: str, por: str = "humano") -> dict:
    """Só passa daqui se `por` não for 'deva' — é a transição proibida em código,
    não em instrução de prompt."""
    nota = obter_nota(nota_id)
    if nota["estado"] not in (Estado.EXCECAO.value, Estado.DUPLICADA.value):
        raise ValueError(f"nota {nota_id!r} não está em exceção/duplicada (estado atual: {nota['estado']})")
    if por == "deva":
        raise TransicaoProibida("exceção não pode ser liberada pelo próprio agente")

    return _atualizar(
        nota_id,
        estado=Estado.PROCESSADA.value,
        categoria_final=categoria_final,
        regra_aplicada=f"liberado manualmente por {auditor}",
        motivo=f"exceção liberada por {auditor}",
    )


def proxima_nao_manipulada() -> dict | None:
    """Próxima nota (em ordem de chegada) que o ciclo do agente ainda não
    mostrou — inclusive se ela já nasceu DUPLICADA na ingestão."""
    for n in _carregar():
        if not n.get("manipulada", False):
            return n
    return None


def marcar_manipulada(nota_id: str) -> None:
    _atualizar(nota_id, manipulada=True)


def contagens() -> dict[str, int]:
    notas = _carregar()
    resultado = {estado.value: 0 for estado in Estado}
    for n in notas:
        resultado[n["estado"]] = resultado.get(n["estado"], 0) + 1
    resultado["total"] = len(notas)
    return resultado
