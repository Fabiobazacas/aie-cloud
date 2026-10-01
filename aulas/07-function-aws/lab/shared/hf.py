"""Edição de imagem (image-to-image) via Space do Hugging Face, com gradio_client.

Usado pelo Exercício 05 quando o modelo de imagem do Gemini não tem cota (free
tier). O Space padrão é o FLUX.1 Kontext (black-forest-labs/FLUX.1-Kontext-Dev):
recebe a foto do produto + uma instrução e devolve a foto editada, preservando o
produto. Roda em GPU compartilhada (ZeroGPU): sem HF_TOKEN a cota diária é
pequena; com um token gratuito do Hugging Face ela é maior.

A API do Space pode mudar. Para ver os parâmetros atuais:
    python -c "from gradio_client import Client; Client('black-forest-labs/FLUX.1-Kontext-Dev').view_api()"
"""
from __future__ import annotations

import os

# Lambda só escreve em /tmp; o gradio_client e o huggingface_hub cacheiam em $HOME.
os.environ.setdefault("HOME", "/tmp")
os.environ.setdefault("HF_HOME", "/tmp/hf")
os.environ.setdefault("GRADIO_TEMP_DIR", "/tmp/gradio")

SPACE_PADRAO = "black-forest-labs/FLUX.1-Kontext-Dev"


def _caminho_do_resultado(resultado) -> str:
    item = resultado[0] if isinstance(resultado, (tuple, list)) else resultado
    if isinstance(item, dict):
        item = item.get("path") or item.get("value")
    if not (isinstance(item, str) and os.path.exists(item)):
        raise RuntimeError(f"Resultado inesperado do Space: {resultado!r}")
    return item


def editar_imagem(imagem: bytes, nome_arquivo: str, prompt: str) -> tuple[bytes, str]:
    """Devolve (bytes da imagem editada, extensão). Levanta exceção se o Space falhar."""
    from gradio_client import Client, handle_file  # empacotado pelo Terraform

    space = os.environ.get("HF_EDIT_SPACE") or SPACE_PADRAO
    token = os.environ.get("HF_TOKEN")

    caminho = f"/tmp/{os.path.basename(nome_arquivo)}"
    with open(caminho, "wb") as arquivo:
        arquivo.write(imagem)
    try:
        client = Client(space, **({"token": token} if token else {}), verbose=False)
        resultado = client.predict(
            input_image=handle_file(caminho),
            prompt=prompt,
            seed=0,
            randomize_seed=True,
            guidance_scale=2.5,
            steps=28,
            api_name="/infer",
        )
    finally:
        os.unlink(caminho)

    saida = _caminho_do_resultado(resultado)
    with open(saida, "rb") as arquivo:
        return arquivo.read(), os.path.splitext(saida)[1].lstrip(".") or "webp"
