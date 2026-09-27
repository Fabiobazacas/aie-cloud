import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from api.servicos import armazenamento  # noqa: E402


@pytest.fixture(autouse=True)
def dados_isolados(tmp_path, monkeypatch):
    """Cada teste usa um diretório de dados próprio — sem rede, sem estado
    compartilhado entre testes."""
    monkeypatch.setattr(armazenamento, "DADOS_DIR", tmp_path)
    monkeypatch.delenv("ARMAZENAMENTO", raising=False)
    yield tmp_path
