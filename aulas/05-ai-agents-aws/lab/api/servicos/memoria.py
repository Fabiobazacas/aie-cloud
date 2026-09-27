"""Memória revisável: MEMORY.md (aprovada) e MEMORIA-PENDENTE.md (proposta).

O agente PROPÕE (`propor`); só um humano, autenticado via header `X-Auditor`,
APROVA (`aprovar`). A linha que entra em MEMORY.md carrega sempre o nome do
auditor — nunca "deva".
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from . import armazenamento as armz

MEMORY_MD = "MEMORY.md"
MEMORIA_PENDENTE_MD = "MEMORIA-PENDENTE.md"

LIMITE_FILA_PENDENTE = 50

# Cada padrão sozinho não basta: "mencionar um limite" é trabalho normal de
# auditor. O que dispara o filtro é uma frase que tenta MUDAR uma regra/limite
# vinda de texto que o próprio agente extraiu de um documento (origem="deva")
# — nunca de uma proposta digitada por um humano na tela.
PADROES_SUSPEITOS = [
    re.compile(r"ignor\w*\s+(a|as)?\s*regras?\b", re.IGNORECASE),
    re.compile(r"(aument|mud|alter|defin|troc)\w*\s+o\s+limite", re.IGNORECASE),
    re.compile(r"apag\w*\s+(a\s+)?regra", re.IGNORECASE),
    re.compile(r"desconsider\w*\s+(as\s+)?instruç", re.IGNORECASE),
]


class TentativaInjecao(Exception):
    """Levantada quando um texto de origem automática (o agente) tenta mudar
    uma regra/limite — comportamento de prompt injection vindo de um documento."""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_pendentes() -> list[dict]:
    linhas = armz.ler_texto(MEMORIA_PENDENTE_MD).splitlines()
    itens = []
    padrao = re.compile(r"^- \[(?P<id>[\w-]+)\] (?P<texto>.*) \(proposto por (?P<origem>.*) em (?P<data>.*)\)$")
    for linha in linhas:
        m = padrao.match(linha.strip())
        if m:
            itens.append(m.groupdict())
    return itens


def _grava_pendentes(itens: list[dict]) -> None:
    linhas = [
        f"- [{i['id']}] {i['texto']} (proposto por {i['origem']} em {i['data']})"
        for i in itens
    ]
    armz.escrever_texto(MEMORIA_PENDENTE_MD, "\n".join(linhas) + ("\n" if linhas else ""))


def propor(texto: str, origem: str, nota_id: str | None = None) -> str:
    """Enfileira uma proposta de regra. Levanta TentativaInjecao se o texto
    parecer um comando pra mudar regra/limite E a origem for o próprio agente."""
    if origem == "deva" and any(p.search(texto) for p in PADROES_SUSPEITOS):
        raise TentativaInjecao(f"texto suspeito vindo do agente: {texto!r}")

    pendentes = _parse_pendentes()
    if len(pendentes) >= LIMITE_FILA_PENDENTE:
        raise RuntimeError("fila de propostas cheia (limite de 50) — precisa de revisão humana")

    novo_id = uuid.uuid4().hex[:8]
    pendentes.append({"id": novo_id, "texto": texto, "origem": origem, "data": _agora()})
    _grava_pendentes(pendentes)
    return novo_id


def listar_pendentes() -> list[dict]:
    return _parse_pendentes()


def listar_aprovadas() -> list[str]:
    linhas = armz.ler_texto(MEMORY_MD).splitlines()
    return [linha.strip() for linha in linhas if linha.strip().startswith("- ")]


def aprovar(proposta_id: str, auditor: str) -> None:
    """Move uma proposta de MEMORIA-PENDENTE.md para MEMORY.md, assinada pelo
    auditor. A validação de que `auditor` veio de um header X-Auditor de
    verdade é responsabilidade da camada de API (principal.py), não daqui."""
    pendentes = _parse_pendentes()
    alvo = next((i for i in pendentes if i["id"] == proposta_id), None)
    if alvo is None:
        raise KeyError(f"proposta {proposta_id!r} não encontrada")

    linha = f"- {alvo['texto']} (aprovado por {auditor} em {_agora()}, regra: {proposta_id})"
    atual = armz.ler_texto(MEMORY_MD)
    armz.escrever_texto(MEMORY_MD, atual + linha + "\n")

    pendentes = [i for i in pendentes if i["id"] != proposta_id]
    _grava_pendentes(pendentes)
