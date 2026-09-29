"""LAB 1.1 — documenta a SQL que cria a extensão pgvector e a tabela
documentos_qc no RDS (CREATE EXTENSION / TABLE / INDEX hnsw).

NÃO RODE ESTE SCRIPT DIRETO DO CLOUDSHELL: o RDS é privado
(publicly_accessible = false), numa subnet que só a Lambda alcança — uma
conexão daqui trava em "Connection timed out". A mesma SQL roda de
verdade dentro da rota `/setup-db` da Lambda (ver
`lambda/lambda_function.py::rota_setup_db`) — é lá que o LAB 1.1 manda
chamar. Este arquivo existe pra comparação: ele tem uma falha de segurança
PROPOSITAL (uma linha de log que imprime a senha inteira — procure por
"Senha obtida" abaixo) que `rota_setup_db` NÃO tem. Ache a diferença.

Variáveis de ambiente esperadas, se algum dia você rodar isto de dentro
da VPC (ex.: via bastion/SSM):
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
