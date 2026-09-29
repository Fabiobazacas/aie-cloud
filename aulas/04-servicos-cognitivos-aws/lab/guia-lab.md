# Guia de Laboratório — Aula 4 (AWS): Pipeline de RAG

**Tema:** RAG (Retrieval-Augmented Generation) — do PDF ao endpoint
**Plataforma:** AWS Academy Learner Lab + Google Gemini (free tier)
**Ambiente:** **AWS CloudShell** — tudo no browser, sem instalar nada

---

## Visão geral do lab

```
Preparação — chave do Gemini + Terraform no CloudShell             ~10 min
LAB 1 — Provisionamento (S3 + RDS/pgvector + Lambda + rede)         ~25 min (a maior parte esperando o RDS)
LAB 2 — Transcrição de PDF via LLM multimodal (Gemini)              ~15 min
LAB 3 — Chunking + embeddings -> pgvector                           ~10 min
LAB 4 — Endpoint de RAG (pergunta -> resposta)                      ~10 min
Wrap-up — terraform destroy + verificação de custo zero              ~5 min
```

> **Regra de ouro:** sempre encerrar com `terraform destroy`. O RDS é o
> recurso mais caro por hora deste módulo — não deixe rodando de um dia
> pro outro.

---

## Preparação

### 1. Crie a chave gratuita do Gemini (uma por GRUPO)

Acesse [aistudio.google.com/apikey](https://aistudio.google.com/apikey),
faça login com uma conta Google, clique em **"Create API key"** → **"new
project"** (não pede cartão de crédito). Copie a chave.

```bash
export GEMINI_API_KEY="sua-chave-aqui"
```

> **Não compartilhe a chave entre grupos** — o rate limit do free tier é
> por chave; se a turma inteira usar a mesma, todo mundo toma `429 Too Many
> Requests` no meio da aula.

### 2. Clonar o repositório e instalar o Terraform

```bash
rm -rf aie-cloud   # se já tiver clonado antes numa sessão anterior
git clone https://github.com/fabiobazacas/aie-cloud.git
cd aie-cloud/aulas/04-servicos-cognitivos-aws/lab/terraform

command -v terraform >/dev/null || {
  curl -sSL -o /tmp/tf.zip https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip
  unzip -o /tmp/tf.zip -d ~/bin && export PATH=$HOME/bin:$PATH
}
terraform -version
```

### 3. Evitar "no space left on device"

```bash
echo 'export TF_DATA_DIR=/tmp/tf-data-aula4' >> ~/.bashrc
export TF_DATA_DIR=/tmp/tf-data-aula4
mkdir -p $TF_DATA_DIR
```

---

## LAB 1 — Provisionamento (Terraform)

**Objetivo:** subir bucket S3, RDS PostgreSQL 16 (pgvector), a rede (NAT
Gateway + subnet dedicada) e a Lambda de RAG — tudo num `apply` só.

```bash
cd ~/aie-cloud/aulas/04-servicos-cognitivos-aws/lab/terraform

terraform init
terraform plan -var="gemini_api_key=$GEMINI_API_KEY"
terraform apply -auto-approve -var="gemini_api_key=$GEMINI_API_KEY"
```

Tempo: ~10-15 min (RDS é o gargalo). Enquanto espera, abra os arquivos
`.tf` no VS Code (`code .`) e explore:

| Arquivo | O que define |
|---------|--------------|
| `main.tf` | Providers, sufixo aleatório, locals (tags) |
| `variables.tf` | `aws_region`, `gemini_api_key` |
| `iam.tf` | `data` source pra `LabRole` (nunca cria role nova) |
| `s3.tf` | Bucket de documentos (via CLI — ver comentário no arquivo) + upload automático do `catalogo_qc.pdf` |
| `network.tf` | NAT Gateway + subnet dedicada pra Lambda alcançar o Gemini (API externa) + Security Groups |
| `rds.tf` | RDS PostgreSQL 16, senha via Secrets Manager (`manage_master_user_password`) |
| `lambda.tf` | Build da Lambda (PyMuPDF + psycopg2 via wheels manylinux) + API Gateway HTTP API + 4 rotas |
| `outputs.tf` | Todos os outputs usados pelos passos seguintes |

Ao final, confira os outputs:

```bash
terraform output
```

**✅ Checkpoint L₁:** `terraform output rds_endpoint` e `terraform output api_gateway_url` retornam valores?

---

## LAB 1.1 — Criar a extensão pgvector e a tabela

pgvector não é habilitado pelo Terraform — é uma extensão do PostgreSQL,
então precisa de SQL depois que a instância já está de pé.

```bash
cd ~/aie-cloud/aulas/04-servicos-cognitivos-aws/lab
pip install --user psycopg2-binary boto3 -q

export DB_HOST=$(cd terraform && terraform output -raw rds_endpoint)
export DB_SECRET_ARN=$(cd terraform && terraform output -raw rds_secret_arn)
echo "RDS: $DB_HOST"

python3 scripts/criar_tabela.py
```

> **Antes de rodar:** abra `scripts/criar_tabela.py` e leia com atenção —
> tem uma falha de segurança proposital (uma linha de log que imprime a
> senha inteira). Ache e conserte antes de rodar contra qualquer banco que
> não seja este lab descartável.

Confirme via `psql`:

```bash
segredo=$(aws secretsmanager get-secret-value --secret-id "$DB_SECRET_ARN" --query SecretString --output text)
export PGPASSWORD=$(echo "$segredo" | python3 -c "import json,sys; print(json.load(sys.stdin)['password'])")
psql -h "$DB_HOST" -U ragadmin -d ragdb -c "\d documentos_qc"
```

**✅ Checkpoint L₁.₁:** a tabela `documentos_qc` existe, com a coluna `embedding VECTOR(768)`?

---

## LAB 2 — Transcrição de PDF via LLM Multimodal

**Objetivo:** entender a lógica de "LLM-based OCR" rodando localmente,
depois testar o mesmo código já deployado na Lambda.

### Passo 1 — Explorar e rodar a versão local

```bash
cd ~/aie-cloud/aulas/04-servicos-cognitivos-aws/lab
pip install --user pymupdf requests -q

cd scripts
python3 transcrever_pdf.py ../data/catalogo_qc.pdf
```

Leia o código de `transcrever_pdf.py` antes de rodar — é a MESMA lógica
que está dentro da Lambda (`../lambda/lambda_function.py`), só que contra
um PDF local em vez do S3.

### Passo 2 — Testar o endpoint de verdade

```bash
cd ~/aie-cloud/aulas/04-servicos-cognitivos-aws/lab/terraform
export API_URL=$(terraform output -raw api_gateway_url)
echo "API: $API_URL"

curl -s "$API_URL/health" | python3 -m json.tool
curl -s "$API_URL/transcrever?bucket_key=catalogo_qc.pdf" | python3 -m json.tool
```

> **Cold start de alguns segundos na primeira chamada** — a função precisa
> "acordar" (e ainda estabelecer a primeira conexão pela VPC). Chamadas
> seguintes são mais rápidas.

**Challenge:** o código usa `gemini-2.0-flash` (rápido e dentro do free
tier). O que mudaria se você trocasse por um modelo Gemini Pro (mais caro,
melhor em tabelas)?

**✅ Checkpoint L₂:** o `curl` em `/transcrever` devolve o texto das 3 páginas do `catalogo_qc.pdf`?

---

## LAB 3 — Chunking + Embeddings

**Objetivo:** dividir o texto transcrito em chunks e gerar um embedding
(vetor) por chunk via Gemini, inserindo tudo no `documentos_qc`.

```bash
curl -s "$API_URL/indexar?bucket_key=catalogo_qc.pdf" | python3 -m json.tool
```

Rode o mesmo comando DE NOVO — repare que `chunks_indexados` vem **zero**
na segunda vez: é o filtro de idempotência evitando reprocessar chunks já
indexados.

Confirme via `psql`:

```bash
psql -h "$DB_HOST" -U ragadmin -d ragdb -c "SELECT COUNT(*) FROM documentos_qc;"
```

### Revisão de segurança (pausa de 2 min)

Reabra `lambda_function.py` e confira, junto com a turma:

- Senha do RDS: só existe no Secrets Manager, nunca em variável nem no código.
- Chave do Gemini: só como variável de ambiente da Lambda (injetada pelo Terraform) — nunca escrita no `.py`.
- Nenhum valor exibido/logado em nenhuma rota.
- `git log -p` no repositório do grupo não deveria mostrar nenhum segredo.

**✅ Checkpoint L₃:** `SELECT COUNT(*)` retorna um número maior que zero?

---

## LAB 4 — Endpoint de RAG (pergunta → resposta)

**Objetivo:** fechar o pipeline — perguntar em linguagem natural e receber
uma resposta com fontes citadas.

```bash
curl -s -X POST "$API_URL/perguntar" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Qual o prazo para troca de móveis por arrependimento?"}' \
  | python3 -m json.tool
```

Explore o arquivo `lambda_function.py` e a função `rota_perguntar` — discuta
com a turma:

- Como trocar a pergunta fixa por outra qualquer (o endpoint já aceita).
- Tempo de processamento: são duas chamadas ao Gemini (embedding da
  pergunta + geração da resposta) mais uma busca no pgvector — cada uma
  soma latência.
- Por que encapsular isso numa tool pra um agente, em vez de uma API que só
  um humano usa.
- Troca de provedor de solução (Gemini → outro LLM): só a função
  `_gemini_post`/`gerar_embedding`/`transcrever_pagina` mudariam — o resto
  da arquitetura (RDS/pgvector, Lambda, API Gateway) fica igual.

**✅ Checkpoint L₄:** a resposta cita a fonte (`catalogo_qc.pdf`, página correta)?

---

## Wrap-up — Destroy e custo zero

```bash
cd ~/aie-cloud/aulas/04-servicos-cognitivos-aws/lab/terraform
terraform destroy -auto-approve -var="gemini_api_key=$GEMINI_API_KEY"
```

Tempo: ~5-10 min (o NAT Gateway e o RDS demoram mais que o resto).
Confira no Vocareum que o budget ficou praticamente igual ao início da
aula — o RDS é o item mais caro por hora deste módulo.

---

## Troubleshooting — Problemas comuns

| Problema | Causa | Solução |
|----------|-------|---------|
| `terraform apply` falha no `null_resource.lambda_build` com `Invalid cross-device link` seguido de `No space left on device` (arquivos do PyMuPDF) | Versão antiga do lab baixava as dependências da Lambda pra dentro do repo (`${path.module}/.build`), que fica no `$HOME` do CloudShell — só ~1GB de cota. O `pip` tenta mover do seu staging em `/tmp` pro `--target`, isso vira cópia entre filesystems diferentes e estoura a cota | `git pull` pra pegar a versão atual do `lambda.tf` (o build agora roda inteiro em `/tmp/qc-rag-lambda-build-...`, mesmo filesystem do staging do `pip`) e rode `terraform apply` de novo |
| `terraform apply` falha no `null_resource.lambda_build` com outro erro de `pip` (não é o de cross-device/espaço acima) | CloudShell sem acesso à internet, ou `pip` desatualizado | `pip install --upgrade pip` e rode `terraform apply` de novo — o `null_resource` é idempotente |
| `Failed to write state`/`errored.tfstate` (disco cheio) no meio do apply | Consequência do problema de espaço acima — quando o disco enche, o Terraform também não consegue gravar o próprio `terraform.tfstate` | Depois de atualizar o `lambda.tf` (linha acima), rode `df -h $HOME` pra confirmar que sobrou espaço; se o apply imprimiu um bloco JSON de "raw state", salve-o num arquivo e rode `terraform state push <arquivo>` antes de tentar de novo, pra não perder o rastro de recursos já criados (S3, NAT Gateway, EIP). **Depois, confira na conta se não sobrou NAT Gateway/EIP órfão** (cobra por hora mesmo sem uso): `aws ec2 describe-nat-gateways --filter "Name=tag:projeto,Values=quantum-commerce"` — se aparecer algo em estado diferente de `deleted`/`deleting` e o `terraform state list` não conhecer esse recurso, delete manualmente pelo console ou `aws ec2 delete-nat-gateway` |
| `terraform apply` falha em `aws_db_instance.rag` com `InvalidParameterCombination: Cannot find version 16.4 for postgres` | A AWS aposenta minor versions do Postgres periodicamente; um `engine_version` fixo tipo `16.4` para de existir | `git pull` pra pegar a versão atual do `rds.tf` (`engine_version = "16"`, só o major — a RDS resolve pro minor disponível automaticamente) e reaplique |
| Lambda retorna `500` com `"Gemini respondeu 403"` ou `401` | `GEMINI_API_KEY` errada ou não passada no `-var` do apply | Confira `echo $GEMINI_API_KEY` antes do apply; reaplique passando `-var="gemini_api_key=$GEMINI_API_KEY"` de novo (isso atualiza só a variável de ambiente da Lambda, é rápido) |
| Lambda retorna `500` com erro de timeout/conexão ao chamar o Gemini | NAT Gateway ainda provisionando, ou security group da Lambda sem egress liberado | Confira `terraform state show aws_nat_gateway.saida_gemini` — o `State` precisa estar `available`; aguarde 1-2 min após o apply |
| `psql` dá `timeout expired` | Rodando de fora da rede da VPC (isso é esperado — só a Lambda acessa o RDS diretamente); o comando do guia usa `psql` do CloudShell, que também não está na VPC | Use `psql` só pra conferência via um bastion, ou confie nos resultados via `curl` nas rotas da Lambda — o CloudShell não tem rota pra dentro da VPC por padrão |
| `terraform apply` falha criando a subnet (`CidrBlockInvalid` ou sobreposição) | O offset `200` do `cidrsubnet` colidiu com uma subnet já existente na conta (raro, mas possível em contas reutilizadas) | Troque o offset em `network.tf` (`cidrsubnet(..., 8, 200)` → tente `201`, `210`, etc.) e reaplique |
| `429 Too Many Requests` do Gemini | Rate limit do free tier estourado — provavelmente a chave está sendo usada por mais de um grupo | Confirme que cada grupo tem sua própria `GEMINI_API_KEY` |
| `terraform destroy` trava no NAT Gateway | Normal — NAT Gateway demora alguns minutos a mais que os outros recursos pra deletar | Aguarde; não interrompa o comando |

---

## Referências

- [Google Gemini API — Text generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [pgvector — GitHub](https://github.com/pgvector/pgvector)
- [AWS Lambda — Configuring VPC access](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html)
- [AWS NAT Gateway — how it works](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)
- [PyMuPDF documentation](https://pymupdf.readthedocs.io/)
