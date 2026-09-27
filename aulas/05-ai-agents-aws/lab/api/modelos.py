"""Modelos de dados do Deva contínuo (versão AWS)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Estado(str, Enum):
    PENDENTE = "pendente"
    PROCESSADA = "processada"
    DUPLICADA = "duplicada"
    EXCECAO = "excecao"


class Nota(BaseModel):
    id: str
    fornecedor: str
    descricao: str
    categoria_solicitada: str
    valor: float
    estado: Estado = Estado.PENDENTE
    categoria_final: str | None = None
    regra_aplicada: str | None = None
    motivo: str | None = None


class PropostaMemoria(BaseModel):
    texto: str = Field(..., description="Regra proposta, em linguagem natural")
    origem: str = Field(..., description="Quem propôs: 'deva' (o agente) ou o nome de um humano")
    nota_id: str | None = None


class AprovacaoMemoria(BaseModel):
    id: str


class LiberacaoExcecao(BaseModel):
    nota_id: str
