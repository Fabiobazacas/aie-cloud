"""LAB 2 — versão LOCAL (CloudShell) da transcrição via LLM multimodal.

Roda a mesma lógica que a rota /transcrever da Lambda usa (ver
../lambda/lambda_function.py), mas contra um PDF LOCAL, sem precisar do S3
nem da API Gateway no ar — serve pra explorar/entender o código antes de
testar o endpoint de verdade.

Variável de ambiente esperada:
    GEMINI_API_KEY — sua chave do grupo (aistudio.google.com/apikey)
"""
import base64
import os
import sys
from pathlib import Path

import fitz  # PyMuPDF — ver guia-lab.md LAB 2 pra instalar
import requests  # idem

# Relativo ao arquivo, não ao diretório atual — assim funciona rodando de
# lab/, de lab/scripts/, ou de onde for (já vimos essa exata confusão de
# diretório acontecer com criar_tabela.py também).
PDF_PADRAO = Path(__file__).resolve().parent.parent / "data" / "catalogo_qc.pdf"

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MODEL_ID = "gemini-2.0-flash"  # confira o nome atual em ai.google.dev/gemini-api/docs/models
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent"


def pagina_para_base64_png(pagina, zoom=2.0):
    pix = pagina.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")


def transcrever_pagina(imagem_b64: str) -> str:
    corpo = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/png", "data": imagem_b64}},
                {"text": "Transcreva TODO o texto visível nesta página, na ordem de leitura. Preserve tabelas como texto estruturado. Não resuma, não comente — só a transcrição."},
            ]
        }],
        "generationConfig": {"maxOutputTokens": 2000},
    }
    resp = requests.post(URL, params={"key": GEMINI_API_KEY}, json=corpo, timeout=30)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def transcrever_pdf(caminho_pdf: str) -> list[str]:
    doc = fitz.open(caminho_pdf)
    paginas_texto = []
    for pagina in doc:
        img_b64 = pagina_para_base64_png(pagina)
        paginas_texto.append(transcrever_pagina(img_b64))
    return paginas_texto


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else str(PDF_PADRAO)
    textos = transcrever_pdf(caminho)
    for i, texto in enumerate(textos, 1):
        print(f"--- Página {i} ---\n{texto}\n")
