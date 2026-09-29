"""Gatilho — o Nível 3 da escada da continuidade: "um arquivo chegou e o
processo começou", sem ninguém digitar nada.

Padrão (sem `--nuvem`): observa a pasta local `dados/entrada/` — custo zero,
nenhuma chamada AWS. Com `--nuvem`: consome uma fila SQS que recebe eventos
S3:ObjectCreated (ver ../terraform/sqs.tf) — o equivalente AWS do
"Event Grid → Logic App" da versão Azure.

Uso:
    python disparador.py --semear                 # insere 3 notas de exemplo
    python disparador.py --observar                # observa dados/entrada/ (local)
    python disparador.py --observar --nuvem        # observa a fila SQS (AWS)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.servicos import fila, memoria  # noqa: E402

ENTRADA_DIR = Path(__file__).resolve().parent.parent / "dados" / "entrada"
PROCESSADAS_DIR = ENTRADA_DIR / "processadas"

NOTAS_EXEMPLO = [
    {
        "fornecedor": "Estacionamento GRU Aeroporto",
        "descricao": "Estacionamento em aeroporto durante viagem a trabalho",
        "categoria_solicitada": "deslocamento",
        "valor": 45.00,
    },
    {
        # Mesmo fornecedor/descrição/valor da primeira — hash bate, vira DUPLICADA
        # já na ingestão. É o Nível 3 do slide 42: "duplicado" sem ninguém decidir nada.
        "fornecedor": "Estacionamento GRU Aeroporto",
        "descricao": "Estacionamento em aeroporto durante viagem a trabalho",
        "categoria_solicitada": "deslocamento",
        "valor": 45.00,
    },
    {
        # Nenhuma regra aprovada cobre isso ainda — vira EXCECAO no ciclo do agente.
        "fornecedor": "Clube de Assinatura de Vinhos LTDA",
        "descricao": "Assinatura mensal de clube de vinhos entregue no escritório",
        "categoria_solicitada": "confraternizacao",
        "valor": 189.90,
    },
]


def _semear_regra_base() -> None:
    """Sem nenhuma regra aprovada, a 1ª nota também iria pra exceção — o que
    quebraria a demonstração dos 3 estados em 3 voltas. Semeia uma regra já
    aprovada (como se um humano já tivesse revisado isso antes da aula)."""
    if memoria.listar_aprovadas():
        return
    proposta_id = memoria.propor(
        "Estacionamento em aeroporto durante viagem a trabalho é despesa de deslocamento, não é viagem aérea",
        origem="seed",
    )
    memoria.aprovar(proposta_id, auditor="seed-do-lab")


def semear() -> None:
    _semear_regra_base()
    for exemplo in NOTAS_EXEMPLO:
        nota_id = uuid.uuid4().hex[:8]
        registro = fila.inserir_nota(nota_id=nota_id, **exemplo)
        print(f"semeada: {registro['id']} · {registro['fornecedor']} · estado inicial={registro['estado']}")


def _processar_arquivo(caminho: Path) -> None:
    dados_nota = json.loads(caminho.read_text(encoding="utf-8"))
    nota_id = dados_nota.get("id") or uuid.uuid4().hex[:8]
    registro = fila.inserir_nota(
        fornecedor=dados_nota["fornecedor"],
        descricao=dados_nota["descricao"],
        categoria_solicitada=dados_nota["categoria_solicitada"],
        valor=float(dados_nota["valor"]),
        nota_id=nota_id,
    )
    print(f"gatilho disparado por {caminho.name} → nota {registro['id']} (estado={registro['estado']})")


def observar_local(intervalo: float = 2.0) -> None:
    ENTRADA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSADAS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"observando {ENTRADA_DIR} — solte um .json de nota ali pra disparar o gatilho (Ctrl+C pra sair)")
    while True:
        for caminho in sorted(ENTRADA_DIR.glob("*.json")):
            _processar_arquivo(caminho)
            caminho.rename(PROCESSADAS_DIR / caminho.name)
        time.sleep(intervalo)


def observar_sqs(fila_url: str, intervalo: float = 5.0) -> None:
    """Consome a fila SQS que recebe S3:ObjectCreated do bucket de entrada
    (ver terraform/sqs.tf) — o gatilho por evento em modo AWS."""
    import boto3

    sqs = boto3.client("sqs")
    s3 = boto3.client("s3")
    print(f"observando a fila SQS {fila_url} (Ctrl+C pra sair)")
    while True:
        resp = sqs.receive_message(QueueUrl=fila_url, MaxNumberOfMessages=5, WaitTimeSeconds=10)
        for msg in resp.get("Messages", []):
            corpo = json.loads(msg["Body"])
            for registro in corpo.get("Records", []):
                bucket = registro["s3"]["bucket"]["name"]
                chave = registro["s3"]["object"]["key"]
                objeto = s3.get_object(Bucket=bucket, Key=chave)
                dados_nota = json.loads(objeto["Body"].read())
                nota_id = dados_nota.get("id") or uuid.uuid4().hex[:8]
                registro_nota = fila.inserir_nota(
                    fornecedor=dados_nota["fornecedor"],
                    descricao=dados_nota["descricao"],
                    categoria_solicitada=dados_nota["categoria_solicitada"],
                    valor=float(dados_nota["valor"]),
                    nota_id=nota_id,
                )
                print(f"gatilho S3 disparado por s3://{bucket}/{chave} → nota {registro_nota['id']}")
            sqs.delete_message(QueueUrl=fila_url, ReceiptHandle=msg["ReceiptHandle"])
        time.sleep(intervalo)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--semear", action="store_true", help="insere as 3 notas de exemplo")
    parser.add_argument("--observar", action="store_true", help="observa a entrada continuamente")
    parser.add_argument("--nuvem", action="store_true", help="observa via SQS/S3 em vez da pasta local")
    parser.add_argument("--fila-url", help="URL da fila SQS (obrigatório com --observar --nuvem)")
    args = parser.parse_args()

    if args.semear:
        semear()
    elif args.observar and args.nuvem:
        if not args.fila_url:
            sys.exit("--observar --nuvem exige --fila-url (terraform output -raw sqs_queue_url)")
        observar_sqs(args.fila_url)
    elif args.observar:
        observar_local()
    else:
        parser.print_help()
