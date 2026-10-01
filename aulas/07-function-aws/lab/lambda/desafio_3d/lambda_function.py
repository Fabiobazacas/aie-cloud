"""Exercício Desafio — imagem 2D -> modelo 3D (TRELLIS no HuggingFace Spaces).

Duas formas de disparar:
  - EVENT-DRIVEN (a original, "Blob Trigger"): subir uma imagem em
    images-3d/ no S3 dispara esta Lambda via S3 Event Notification.
  - HTTP: POST /convert3d {"bucket_key": "images-3d/cadeira.png"}  (async por padrão)

Saída: models3d/<nome>/model.glb + metadata.json (ou error.json se falhar).

A conversão leva de 1 a vários minutos (fila + GPU do Space) — por isso esta
função tem timeout de 15 min e nunca roda de forma síncrona atrás da API Gateway.

Space padrão: trellis-community/TRELLIS (o microsoft/TRELLIS original está fora do ar).
Os Spaces rodam em GPU compartilhada (ZeroGPU): sem HF_TOKEN a cota diária é minúscula
e a conversão costuma falhar com "exceeded your ZeroGPU quota" — use um token por grupo.

Variáveis de ambiente: BUCKET, HF_TOKEN (recomendado), TRELLIS_SPACE (opcional).
"""
import logging
import os
from datetime import datetime, timezone

# Lambda só escreve em /tmp; o gradio_client e o huggingface_hub cacheiam em $HOME.
os.environ.setdefault("HOME", "/tmp")
os.environ.setdefault("HF_HOME", "/tmp/hf")
os.environ.setdefault("GRADIO_TEMP_DIR", "/tmp/gradio")

from shared import s3io, web  # noqa: E402

logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger(__name__)


def converter_para_3d(imagem: bytes, nome_arquivo: str) -> tuple[bytes, str]:
    """Devolve (bytes do modelo, extensão). Levanta exceção se o Space falhar."""
    from gradio_client import Client, handle_file  # empacotado pelo Terraform

    space = os.environ.get("TRELLIS_SPACE") or "trellis-community/TRELLIS"
    token = os.environ.get("HF_TOKEN")

    caminho = f"/tmp/{os.path.basename(nome_arquivo)}"
    with open(caminho, "wb") as arquivo:
        arquivo.write(imagem)

    try:
        log.info("Conectando ao HuggingFace Space: %s", space)
        client = Client(space, **({"token": token} if token else {}), verbose=False)

        client.predict(api_name="/start_session")  # exigido pelo Space do TRELLIS

        # Remove o fundo e centraliza o objeto (o TRELLIS espera essa imagem pré-processada)
        log.info("Pré-processando a imagem...")
        preprocessada = client.predict(image=handle_file(caminho), api_name="/preprocess_image")
        if isinstance(preprocessada, dict):
            preprocessada = preprocessada.get("path") or preprocessada.get("value")

        log.info("Gerando o modelo 3D (1-3 min, GPU compartilhada)...")
        resultado = client.predict(
            image=handle_file(preprocessada),
            multiimages=[],
            seed=0,
            ss_guidance_strength=7.5,
            ss_sampling_steps=12,
            slat_guidance_strength=3.0,
            slat_sampling_steps=12,
            multiimage_algo="stochastic",
            mesh_simplify=0.95,
            texture_size=1024,
            api_name="/generate_and_extract_glb",
        )
    finally:
        os.unlink(caminho)

    # O Space devolve (preview 3D, GLB com preview, arquivo GLB para download)
    glb = resultado[2] if isinstance(resultado, (tuple, list)) and len(resultado) >= 3 else resultado
    if isinstance(glb, dict):
        glb = glb.get("path") or glb.get("value")
    if not (isinstance(glb, str) and os.path.exists(glb)):
        raise RuntimeError(f"Resultado inesperado do TRELLIS: {resultado!r}")
    with open(glb, "rb") as arquivo:
        return arquivo.read(), os.path.splitext(glb)[1].lstrip(".") or "glb"


def converter(body: dict) -> dict:
    chave = web.chave_obrigatoria(body)
    base = s3io.nome_base(chave)
    log.info("Conversão 3D: s3://%s/%s", s3io.bucket(), chave)

    try:
        modelo, formato = converter_para_3d(s3io.ler(chave), os.path.basename(chave))
    except Exception as erro:  # noqa: BLE001 — registramos error.json e repassamos
        s3io.gravar_json(f"models3d/{base}/error.json", {
            "source": chave, "error": str(erro), "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        raise

    modelo_key = f"models3d/{base}/model.{formato}"
    s3io.gravar(modelo_key, modelo, "model/gltf-binary")
    s3io.gravar_json(f"models3d/{base}/metadata.json", {
        "source_image": chave,
        "model_path": modelo_key,
        "model_format": formato,
        "model_size_bytes": len(modelo),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "ok", "bucket_key": chave, "model_path": modelo_key, "model_size_bytes": len(modelo)}


ROTAS = {("POST", "/convert3d"): (converter, True)}


def handler(event, context):
    return web.executar(event, context, ROTAS, rota_s3=("POST", "/convert3d"))
