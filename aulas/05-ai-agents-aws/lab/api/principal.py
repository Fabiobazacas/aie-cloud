"""API de Continuidade do Deva — FastAPI.

14 operações ao todo. Só 5 estão na especificação OpenAPI que o agente carrega
(ver ../agente/openapi-agente.json, campo "x-agente-permitido"): listar notas,
detalhar nota, processar nota, propor memória, ler memória aprovada. As outras
9 exigem o header `X-Auditor` — inclusive quando chamadas manualmente (a
fronteira é reforçada em dois lugares: o que o agente enxerga, e o que a API
aceita sem assinatura humana).
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI, Header, HTTPException

from . import modelos
from .servicos import fila, memoria

app = FastAPI(title="Deva Contínuo — API de Continuidade (AWS)")


def exigir_auditor(x_auditor: str | None = Header(default=None)) -> str:
    if not x_auditor or not x_auditor.strip():
        raise HTTPException(status_code=403, detail="operação exige o header X-Auditor com o nome de um humano")
    return x_auditor.strip()


# ---------------------------------------------------------------------------
# 1) Agente — listar notas
# ---------------------------------------------------------------------------
@app.get("/notas")
def listar_notas(estado: str | None = None):
    filtro = modelos.Estado(estado) if estado else None
    return fila.listar_notas(filtro)


# ---------------------------------------------------------------------------
# 2) Agente — detalhar nota
# ---------------------------------------------------------------------------
@app.get("/notas/{nota_id}")
def detalhar_nota(nota_id: str):
    try:
        return fila.obter_nota(nota_id)
    except KeyError as erro:
        raise HTTPException(status_code=404, detail=str(erro))


# ---------------------------------------------------------------------------
# 3) Agente — processar nota (classifica; se ambíguo/duplicado, vira exceção)
# ---------------------------------------------------------------------------
@app.post("/notas/{nota_id}/processar")
def processar_nota(nota_id: str, categoria_final: str, regra_aplicada: str | None = None, motivo: str = ""):
    try:
        nota = fila.obter_nota(nota_id)
    except KeyError as erro:
        raise HTTPException(status_code=404, detail=str(erro))

    if nota["estado"] == modelos.Estado.DUPLICADA.value:
        return nota  # já marcada como duplicada na ingestão — nada a processar

    return fila.marcar_processada(nota_id, categoria_final, regra_aplicada, motivo or "classificado pelo agente")


# ---------------------------------------------------------------------------
# 4) Orquestrador (gatilho/ciclo_do_agente.py) — marcar exceção. Não é uma
#    tool do agente: é a ORQUESTRAÇÃO em volta do agente que decide chamar
#    isso, interpretando a confiança da classificação que ele devolveu.
# ---------------------------------------------------------------------------
@app.post("/notas/{nota_id}/marcar-excecao")
def marcar_excecao(nota_id: str, motivo: str):
    try:
        return fila.marcar_excecao(nota_id, motivo)
    except KeyError as erro:
        raise HTTPException(status_code=404, detail=str(erro))


# ---------------------------------------------------------------------------
# 5) Agente — propor memória
# ---------------------------------------------------------------------------
@app.post("/memoria/propor")
def propor_memoria(proposta: modelos.PropostaMemoria):
    try:
        proposta_id = memoria.propor(proposta.texto, proposta.origem, proposta.nota_id)
    except memoria.TentativaInjecao as erro:
        raise HTTPException(status_code=400, detail=f"tentativa de injeção bloqueada: {erro}")
    return {"id": proposta_id}


# ---------------------------------------------------------------------------
# 6) Agente — ler memória aprovada
# ---------------------------------------------------------------------------
@app.get("/memoria")
def ler_memoria():
    return memoria.listar_aprovadas()


# ---------------------------------------------------------------------------
# 7) Humano — ver propostas pendentes
# ---------------------------------------------------------------------------
@app.get("/memoria/pendentes")
def listar_pendentes(auditor: str = Header(default=None, alias="X-Auditor")):
    exigir_auditor(auditor)
    return memoria.listar_pendentes()


# ---------------------------------------------------------------------------
# 8) Humano — aprovar proposta (409/403 se o próprio "deva" tentar)
# ---------------------------------------------------------------------------
@app.post("/memoria/{proposta_id}/aprovar")
def aprovar_memoria(proposta_id: str, auditor: str = Header(default=None, alias="X-Auditor")):
    nome = exigir_auditor(auditor)
    if nome.lower() == "deva":
        raise HTTPException(status_code=403, detail="o agente não pode aprovar a própria proposta")
    try:
        memoria.aprovar(proposta_id, nome)
    except KeyError as erro:
        raise HTTPException(status_code=404, detail=str(erro))
    return {"status": "aprovada", "por": nome}


# ---------------------------------------------------------------------------
# 9) Humano — arquivar regra aprovada — ESQUECIMENTO — Exercício N1 (não
#    implementado de propósito: ver exercicios.md, Exercício 1)
# ---------------------------------------------------------------------------
@app.post("/memoria/{regra_id}/arquivar")
def arquivar_memoria(regra_id: str, auditor: str = Header(default=None, alias="X-Auditor")):
    exigir_auditor(auditor)
    raise HTTPException(
        status_code=501,
        detail="não implementado neste lab-base — é o Exercício 1 (Esquecimento) de exercicios.md",
    )


# ---------------------------------------------------------------------------
# 10) Humano — listar exceções (dashboard também usa)
# ---------------------------------------------------------------------------
@app.get("/excecoes")
def listar_excecoes():
    return fila.listar_notas(modelos.Estado.EXCECAO) + fila.listar_notas(modelos.Estado.DUPLICADA)


# ---------------------------------------------------------------------------
# 11) Humano — liberar exceção (409 se `por=deva`)
# ---------------------------------------------------------------------------
@app.post("/excecoes/{nota_id}/liberar")
def liberar_excecao(nota_id: str, categoria_final: str, por: str = "humano", auditor: str = Header(default=None, alias="X-Auditor")):
    nome = exigir_auditor(auditor)
    try:
        return fila.liberar_excecao(nota_id, nome, categoria_final, por=por)
    except fila.TransicaoProibida as erro:
        raise HTTPException(status_code=409, detail=str(erro))
    except (KeyError, ValueError) as erro:
        raise HTTPException(status_code=404, detail=str(erro))


# ---------------------------------------------------------------------------
# 12) Humano — métricas da fila (base para o Exercício 3 — Taxa de devolução)
# ---------------------------------------------------------------------------
@app.get("/fila/metricas")
def metricas_fila(auditor: str = Header(default=None, alias="X-Auditor")):
    exigir_auditor(auditor)
    return fila.contagens()


# ---------------------------------------------------------------------------
# 13) Dev/gatilho — semear notas de exemplo
# ---------------------------------------------------------------------------
@app.post("/notas/semear")
def semear_notas(notas: list[dict]):
    criadas = []
    for dados_nota in notas:
        nota_id = dados_nota.get("id") or uuid.uuid4().hex[:8]
        criadas.append(
            fila.inserir_nota(
                fornecedor=dados_nota["fornecedor"],
                descricao=dados_nota["descricao"],
                categoria_solicitada=dados_nota["categoria_solicitada"],
                valor=float(dados_nota["valor"]),
                nota_id=nota_id,
            )
        )
    return criadas


# ---------------------------------------------------------------------------
# 14) Humano — rastreamento de uma decisão (base para o Exercício 2)
# ---------------------------------------------------------------------------
@app.get("/rastreamento/{nota_id}")
def rastrear_decisao(nota_id: str, auditor: str = Header(default=None, alias="X-Auditor")):
    exigir_auditor(auditor)
    try:
        nota = fila.obter_nota(nota_id)
    except KeyError as erro:
        raise HTTPException(status_code=404, detail=str(erro))
    return {
        "nota_id": nota_id,
        "estado": nota["estado"],
        "categoria_final": nota["categoria_final"],
        "regra_aplicada": nota["regra_aplicada"],
    }
