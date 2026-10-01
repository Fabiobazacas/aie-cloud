"""Exercício 05 — Campanha de marketing com IA generativa.

    POST /campaign   {"bucket_key": "images/sabonete.png"}      (async por padrão)

Pipeline: imagem do produto no S3 -> Gemini (visão) analisa a embalagem e cria a
campanha -> edição de imagem em modo image-to-image: a foto do produto vira uma
cena de campanha ambientada no tema da embalagem -> campaign.json + imagem no S3.

Edição de imagem (IMAGE_PROVIDERS, em ordem; o primeiro que funcionar vence):
  gemini  modelo de imagem do Gemini (precisa de cota — o free tier não tem)
  hf      Space do Hugging Face (FLUX.1 Kontext) via gradio_client (shared/hf.py)

Se nenhum gerar a imagem, a campanha em texto ainda é entregue e o motivo vai em
`image_error`.

Variáveis de ambiente: BUCKET, GEMINI_API_KEY, GEMINI_IMAGE_MODEL, IMAGE_PROVIDERS,
HF_TOKEN (opcional), HF_EDIT_SPACE (opcional).
"""
import logging
import os
from datetime import datetime, timezone

from shared import gemini, hf, prompts, s3io, web

logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger(__name__)

MIME_POR_EXTENSAO = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
}
MIME_GEMINI_EDITAVEIS = {"image/png", "image/jpeg"}
CONTENT_TYPE_POR_EXTENSAO = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}


def prompt_de_edicao(prompt_imagem: str) -> str:
    return (
        "Edit this product photo into a rich, professional advertising scene. Keep the product "
        "itself exactly identical — shape, colors, packaging, label text and branding — and clearly "
        "visible. Build the scene around the theme shown on the packaging (the ingredients, fruits, "
        "plants, colors and motifs printed on it), changing the background, lighting, props and "
        f"composition. Scene direction: {prompt_imagem}"
    )


def editar_imagem(provedor: str, prompt: str, imagem: bytes, mime: str, chave: str) -> tuple[bytes, str]:
    if provedor == "gemini":
        if mime not in MIME_GEMINI_EDITAVEIS:
            raise RuntimeError(f"edição de imagem do Gemini aceita PNG/JPG; recebido {mime}")
        return gemini.gerar_imagem(prompt, imagem, mime), "png"
    if provedor == "hf":
        return hf.editar_imagem(imagem, os.path.basename(chave), prompt)
    raise RuntimeError(f"provedor de imagem desconhecido: {provedor!r} (use gemini e/ou hf)")


def processar(body: dict) -> dict:
    chave = web.chave_obrigatoria(body)
    imagem = s3io.ler(chave)
    mime = MIME_POR_EXTENSAO.get(os.path.splitext(chave)[1].lower(), "image/jpeg")
    log.info("Imagem carregada: %d bytes (%s)", len(imagem), mime)

    # 1. Visão: analisa o produto/embalagem e cria a campanha
    campanha = gemini.gerar_json(
        [gemini.parte_arquivo(imagem, mime), "Analise a imagem do produto a seguir e crie uma campanha de marketing completa."],
        sistema=prompts.carregar("marketing_campaign.md"),
        temperatura=0.5,
        max_tokens=4096,
    )

    # 2. Prompt de imagem (o prompt de sistema pede em image_generation.prompt)
    prompt_imagem = None
    if isinstance(campanha, dict):
        prompt_imagem = (campanha.get("image_generation") or {}).get("prompt") or campanha.get("image_prompt")

    # 3. Image-to-image: tenta cada provedor, em ordem
    base = s3io.nome_base(chave)
    imagem_key, imagem_url, origem, erros = None, None, None, []
    if not prompt_imagem:
        erros.append("a campanha não trouxe prompt de imagem")
    else:
        provedores = [p.strip() for p in os.environ.get("IMAGE_PROVIDERS", "gemini,hf").split(",") if p.strip()]
        for provedor in provedores:
            try:
                gerada, extensao = editar_imagem(provedor, prompt_de_edicao(prompt_imagem), imagem, mime, chave)
            except Exception as erro:  # noqa: BLE001 — cada provedor pode falhar de jeitos diferentes
                log.warning("Provedor %s falhou: %s", provedor, erro)
                erros.append(f"{provedor}: {str(erro)[:200]}")
                continue
            imagem_key = f"campaigns/{base}/campaign_image.{extensao}"
            s3io.gravar(imagem_key, gerada, CONTENT_TYPE_POR_EXTENSAO.get(extensao, "application/octet-stream"))
            imagem_url = s3io.url_assinada(imagem_key)
            origem = provedor
            break

    # 4. Gravar o JSON da campanha
    erro_imagem = None if imagem_key else "; ".join(erros)
    campaign_key = f"campaigns/{base}/campaign.json"
    s3io.gravar_json(campaign_key, {
        "campaign": campanha,
        "source_image": chave,
        "generated_image": imagem_key,
        "image_source": origem,
        "image_error": erro_imagem,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "ok",
        "bucket_key": chave,
        "campaign_path": campaign_key,
        "generated_image": imagem_key,
        "generated_image_url": imagem_url,
        "image_source": origem,
        "image_error": erro_imagem,
    }


ROTAS = {("POST", "/campaign"): (processar, True)}


def handler(event, context):
    return web.executar(event, context, ROTAS)
