"""LAB 1 — cria a extensão pgvector e a tabela documentos_qc no RDS.

ATENÇÃO: este script tem uma falha de segurança PROPOSITAL — ache-a antes
de rodar contra um banco de verdade. Dica: procure por "Senha obtida" logo
abaixo.

Variáveis de ambiente esperadas (exporte antes de rodar — ver guia-lab.md):
    DB_HOST        — terraform output -raw rds_endpoint
    DB_SECRET_ARN  — terraform output -raw rds_secret_arn
"""
import json
import os

import boto3
import psycopg2

SECRET_ARN = os.environ["DB_SECRET_ARN"]
DB_HOST = os.environ["DB_HOST"]

sm = boto3.client("secretsmanager")
segredo = sm.get_secret_value(SecretId=SECRET_ARN)
# ATENÇÃO: a linha abaixo é a falha proposital — ache e conserte.
# Ela imprime o SEGREDO INTEIRO (usuário + senha) no console/CloudWatch Logs
# — exatamente o tipo de vazamento que o Secrets Manager deveria evitar.
print(f"Senha obtida: {segredo}")

cred = json.loads(segredo["SecretString"])

conn = psycopg2.connect(
    host=DB_HOST, dbname="ragdb",
    user=cred["username"], password=cred["password"],
)
cur = conn.cursor()

cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
cur.execute("""
    CREATE TABLE IF NOT EXISTS documentos_qc (
        id SERIAL PRIMARY KEY,
        fonte TEXT NOT NULL,
        pagina INT NOT NULL,
        chunk_texto TEXT NOT NULL,
        embedding VECTOR(768)
    );
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS documentos_qc_embedding_idx
    ON documentos_qc USING hnsw (embedding vector_cosine_ops);
""")
conn.commit()
print("✓ Tabela documentos_qc pronta!")
