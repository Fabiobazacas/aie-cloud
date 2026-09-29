import pytest

from api.modelos import Estado
from api.servicos import fila


def _inserir(nota_id="n1", fornecedor="Fornecedor X", descricao="descricao qualquer", valor=100.0):
    return fila.inserir_nota(
        fornecedor=fornecedor,
        descricao=descricao,
        categoria_solicitada="categoria",
        valor=valor,
        nota_id=nota_id,
    )


def test_nota_nova_comeca_pendente():
    nota = _inserir()
    assert nota["estado"] == Estado.PENDENTE.value
    assert nota["manipulada"] is False


def test_segunda_nota_com_mesmo_hash_nasce_duplicada():
    _inserir(nota_id="n1")
    duplicada = _inserir(nota_id="n2")
    assert duplicada["estado"] == Estado.DUPLICADA.value


def test_nota_com_dados_diferentes_nao_e_duplicada():
    _inserir(nota_id="n1", valor=100.0)
    outra = _inserir(nota_id="n2", valor=200.0)
    assert outra["estado"] == Estado.PENDENTE.value


def test_marcar_processada_atualiza_categoria_e_regra():
    _inserir(nota_id="n1")
    atualizada = fila.marcar_processada("n1", "categoria_final", "regra-1", "motivo")
    assert atualizada["estado"] == Estado.PROCESSADA.value
    assert atualizada["categoria_final"] == "categoria_final"


def test_marcar_excecao():
    _inserir(nota_id="n1")
    atualizada = fila.marcar_excecao("n1", "sem regra aprovada")
    assert atualizada["estado"] == Estado.EXCECAO.value


def test_agente_nao_pode_liberar_propria_excecao():
    _inserir(nota_id="n1")
    fila.marcar_excecao("n1", "sem regra")
    with pytest.raises(fila.TransicaoProibida):
        fila.liberar_excecao("n1", auditor="deva", categoria_final="x", por="deva")


def test_humano_pode_liberar_excecao():
    _inserir(nota_id="n1")
    fila.marcar_excecao("n1", "sem regra")
    liberada = fila.liberar_excecao("n1", auditor="Maria", categoria_final="categoria_x", por="humano")
    assert liberada["estado"] == Estado.PROCESSADA.value
    assert "Maria" in liberada["motivo"]


def test_liberar_excecao_de_nota_nao_excecao_falha():
    _inserir(nota_id="n1")
    with pytest.raises(ValueError):
        fila.liberar_excecao("n1", auditor="Maria", categoria_final="x", por="humano")


def test_proxima_nao_manipulada_avanca_o_cursor():
    _inserir(nota_id="n1")
    _inserir(nota_id="n2", descricao="outra coisa", valor=50.0)

    primeira = fila.proxima_nao_manipulada()
    assert primeira["id"] == "n1"
    fila.marcar_manipulada("n1")

    segunda = fila.proxima_nao_manipulada()
    assert segunda["id"] == "n2"


def test_contagens_reflete_estados():
    _inserir(nota_id="n1")
    _inserir(nota_id="n2")  # duplicada de n1
    contagens = fila.contagens()
    assert contagens["total"] == 2
    assert contagens[Estado.DUPLICADA.value] == 1
    assert contagens[Estado.PENDENTE.value] == 1
