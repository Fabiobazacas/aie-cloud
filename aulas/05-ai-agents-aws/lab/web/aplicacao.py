"""Tela do Deva Contínuo — Streamlit, 4 abas: Painel · Memória · Propostas · Exceções.

Fala com a API (api/principal.py, rodando via `uvicorn api.principal:app`).
Rode com: streamlit run web/aplicacao.py
"""
from __future__ import annotations

import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Deva Contínuo", layout="wide")
st.title("Deva Contínuo — Painel de Continuidade")

aba_painel, aba_memoria, aba_propostas, aba_excecoes = st.tabs(
    ["Painel", "Memória", "Propostas", "Exceções"]
)

with aba_painel:
    st.subheader("Notas por estado")
    try:
        auditor = st.session_state.get("auditor", "")
        resp = requests.get(f"{API_URL}/fila/metricas", headers={"X-Auditor": auditor or "painel"})
        resp.raise_for_status()
        contagens = resp.json()
        colunas = st.columns(len(contagens))
        for coluna, (estado, valor) in zip(colunas, contagens.items()):
            coluna.metric(estado, valor)
    except requests.RequestException as erro:
        st.error(f"não consegui falar com a API em {API_URL}: {erro}")

    st.subheader("Notas")
    try:
        notas = requests.get(f"{API_URL}/notas").json()
        st.dataframe(notas, use_container_width=True)
    except requests.RequestException:
        pass

with aba_memoria:
    st.subheader("Regras aprovadas (MEMORY.md)")
    try:
        aprovadas = requests.get(f"{API_URL}/memoria").json()
        for linha in aprovadas:
            st.markdown(linha)
        if not aprovadas:
            st.caption("nenhuma regra aprovada ainda")
    except requests.RequestException as erro:
        st.error(str(erro))

with aba_propostas:
    st.subheader("Propostas pendentes (MEMORIA-PENDENTE.md)")
    nome_auditor = st.text_input("Seu nome (vira o X-Auditor de quem aprova)", key="auditor")

    if nome_auditor:
        try:
            pendentes = requests.get(
                f"{API_URL}/memoria/pendentes", headers={"X-Auditor": nome_auditor}
            ).json()
        except requests.RequestException as erro:
            st.error(str(erro))
            pendentes = []

        for item in pendentes:
            col_texto, col_botao = st.columns([4, 1])
            col_texto.write(f"**[{item['id']}]** {item['texto']} — proposto por *{item['origem']}* em {item['data']}")
            if col_botao.button("Aprovar", key=f"aprovar-{item['id']}"):
                resp = requests.post(
                    f"{API_URL}/memoria/{item['id']}/aprovar", headers={"X-Auditor": nome_auditor}
                )
                if resp.status_code == 200:
                    st.success(f"aprovado por {nome_auditor}")
                    st.rerun()
                else:
                    st.error(resp.json().get("detail", resp.text))
    else:
        st.info("digite seu nome acima — é o que assina a aprovação em MEMORY.md")

with aba_excecoes:
    st.subheader("Fila de exceções")
    nome_auditor_exc = st.session_state.get("auditor", "")
    try:
        excecoes = requests.get(f"{API_URL}/excecoes").json()
    except requests.RequestException as erro:
        st.error(str(erro))
        excecoes = []

    for nota in excecoes:
        st.write(f"**{nota['id']}** · {nota['fornecedor']} · {nota['descricao']} — motivo: {nota['motivo']}")
        col_categoria, col_deva, col_humano = st.columns([2, 1, 1])
        categoria = col_categoria.text_input("categoria final", key=f"cat-{nota['id']}")

        if col_deva.button("Tentar liberar como 'deva' (deve falhar)", key=f"deva-{nota['id']}"):
            resp = requests.post(
                f"{API_URL}/excecoes/{nota['id']}/liberar",
                params={"categoria_final": categoria or nota["categoria_solicitada"], "por": "deva"},
                headers={"X-Auditor": "deva"},
            )
            st.warning(f"{resp.status_code}: {resp.json().get('detail', resp.text)}")

        if col_humano.button("Liberar (humano)", key=f"humano-{nota['id']}", disabled=not nome_auditor_exc):
            resp = requests.post(
                f"{API_URL}/excecoes/{nota['id']}/liberar",
                params={"categoria_final": categoria or nota["categoria_solicitada"], "por": "humano"},
                headers={"X-Auditor": nome_auditor_exc},
            )
            if resp.status_code == 200:
                st.success("liberado")
                st.rerun()
            else:
                st.error(resp.json().get("detail", resp.text))
