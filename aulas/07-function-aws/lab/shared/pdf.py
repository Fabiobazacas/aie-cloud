"""Extração de texto de PDF (PyMuPDF) com fallback para OCR via Gemini."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from . import gemini

PROMPT_OCR = (
    "Transcreva TODO o texto visível nesta página, na ordem de leitura. Preserve tabelas "
    "como texto estruturado. Não resuma, não comente — só a transcrição."
)


def extrair_texto(pdf_bytes: bytes) -> str:
    """Texto do PDF, página a página, marcado com '[Página N]'.

    Páginas sem camada de texto (PDF escaneado — é o caso do matricula.pdf da
    aula) são enviadas como imagem ao Gemini, que age como um "OCR por LLM",
    o mesmo truque da Aula 4. As páginas escaneadas são processadas em
    paralelo para caber no tempo da Lambda.
    """
    import fitz  # PyMuPDF — wheel manylinux empacotada pelo Terraform

    documento = fitz.open(stream=pdf_bytes, filetype="pdf")
    textos: list[str | None] = []
    imagens: dict[int, bytes] = {}
    for indice, pagina in enumerate(documento):
        texto = pagina.get_text().strip()
        textos.append(texto or None)
        if not texto:
            imagens[indice] = pagina.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")

    def ocr(indice: int) -> str:
        return gemini.gerar(
            [gemini.parte_arquivo(imagens[indice], "image/png"), PROMPT_OCR], max_tokens=4096
        )

    if imagens:
        with ThreadPoolExecutor(max_workers=3) as pool:
            for indice, texto in zip(imagens, pool.map(ocr, imagens)):
                textos[indice] = texto

    return "\n\n".join(f"[Página {i}]\n{t}" for i, t in enumerate(textos, start=1))
