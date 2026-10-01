"""Carrega os prompts de sistema (arquivos .md) empacotados junto com a Lambda."""
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def carregar(nome: str) -> str:
    return (PROMPTS_DIR / nome).read_text(encoding="utf-8")
