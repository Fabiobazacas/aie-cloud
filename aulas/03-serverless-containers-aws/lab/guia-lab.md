# Guia de Laboratório — Aula 3 (AWS)

**Tema:** Serverless & Containers
**Plataforma:** AWS Academy Learner Lab (Cloud Developing)
**Ambiente:** **AWS CloudShell** — tudo no browser, sem instalar nada

---

## Visão geral do lab

```
Atividade 1 — Lambda HTTP via Terraform (deploy embutido no apply)     ~25 min  (L₁)
Atividade 2 — Lambda lendo S3 (CSV QC) via IAM Role (LabRole)          ~40 min  (L₂)
Atividade 3 — Mesmo código em container: Elastic Beanstalk (Docker)    ~50 min  (L₃)
Wrap-up    — terraform destroy + verificação custo zero                ~10 min
```

> **Regra de ouro:** sempre encerrar com `terraform destroy`. Custo zero ao
> final — e ao fim da sessão de 4h o Learner Lab **derruba tudo de qualquer
> forma**, então nunca deixe pra depois.

---

## Recursos disponíveis no Learner Lab

Levantamento feito no Sandbox do curso *AWS Academy Cloud Developing*. É um
**subconjunto curado** dos serviços AWS, não a lista completa — qualquer
serviço fora desta lista provavelmente vai dar erro de permissão.

| Item | Valor |
|------|-------|
| Crédito | US$ 100 por aluno |
| Duração da sessão | 4 horas (clique "Start Lab" de novo para renovar) |
| Regiões permitidas | **us-east-1** e **us-west-2** apenas |
| IAM | Sem console de usuário próprio; **não pode criar roles** (exceto service-linked) — use `LabRole`/`LabInstanceProfile`, já pré-criados |
| Persistência | Recursos somem no "Reset" ou no fim do curso — cada sessão é uma conta nova |

**Principais serviços liberados** (relevantes para esta aula): API Gateway,
CloudFormation, CloudShell, CloudWatch, DynamoDB, ECR (registry, sem serviço
de execução), Elastic Beanstalk (Docker), EC2 (nano/micro/small, séries
t2/t3), IAM (só leitura/anexar `LabRole`), Lambda, RDS, S3, Secrets Manager,
SNS/SQS, Step Functions, Systems Manager, X-Ray.

**❌ Não disponível** (nem neste nem em nenhum outro Learner Lab verificado):
**ECS, Fargate, EKS, App Runner** — ou seja, nenhum orquestrador de
containers completo. É por isso que a Atividade 3 usa Elastic Beanstalk em
vez de ECS/Fargate (o que a versão Azure faz com ACI em vez de AKS).

---

## Pré-requisitos

- ✅ Sessão ativa no AWS Academy Learner Lab ("Start Lab" clicado, luz verde)
- ✅ Repositório `aie-cloud` clonado no **AWS CloudShell**

> **Aula independente:** esta aula **não depende da Aula 2**. O Terraform cria
> seu próprio bucket S3 de catálogo e já sobe o `produtos.csv` no `apply`
> (de [lab/data/produtos.csv](data/produtos.csv)).

---

## Preparação (5 min)

### Pegar as credenciais temporárias da sessão

No Learner Lab, clique em **AWS Details** (canto superior do painel do
Vocareum) → **Show** ao lado de "AWS CLI". Copie o bloco inteiro — ele já
vem no formato de `~/.aws/credentials`, com **3 campos, não 2**:

```ini
[default]
aws_access_key_id=...
aws_secret_access_key=...
aws_session_token=...
```

> **Erro mais comum da aula:** esquecer o `aws_session_token`. Como a conta é
> temporária, as credenciais são de **sessão** (STS), não uma Access Key
> permanente de usuário IAM — sem o token, toda chamada AWS falha com
> `InvalidClientTokenId` ou `ExpiredToken`.

No CloudShell, cole no arquivo de credenciais:

```bash
mkdir -p ~/.aws
cat > ~/.aws/credentials << 'EOF'
[default]
aws_access_key_id=SEU_ACCESS_KEY
aws_secret_access_key=SEU_SECRET_KEY
aws_session_token=SEU_SESSION_TOKEN
EOF
```

> Se você abrir o **AWS CloudShell de dentro do próprio Learner Lab** (menu
> Services → CloudShell, já autenticado), este passo é automático — as
> credenciais da sessão já estão disponíveis no ambiente. Só é manual se
> você estiver usando outro terminal.

### Instalar o Terraform (1x por CloudShell)

Diferente do `aws` CLI, o **Terraform não vem pré-instalado** no CloudShell.
O `$HOME` do CloudShell é persistente (~1GB, entre sessões), então isso só
precisa ser feito **uma vez**:

```bash
command -v terraform >/dev/null || {
  curl -sSL -o /tmp/terraform.zip https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip
  unzip -o /tmp/terraform.zip -d ~/bin
  echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc
  export PATH=$HOME/bin:$PATH
}
terraform -version
```

> Se aparecer `command not found: unzip`, rode `sudo yum install -y unzip`
> antes (CloudShell é Amazon Linux).

### Confirmar ferramentas

```bash
aws sts get-caller-identity   # confirma que as credenciais da sessão estão válidas
terraform -version
docker --version 2>/dev/null || echo "sem docker no CloudShell — esperado, ver docker/README.md"
```

### Ir para o Terraform da Aula 3 (AWS)

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform
ls
# main.tf  variables.tf  iam.tf  s3.tf  lambda.tf  beanstalk.tf  outputs.tf  README.md
```

Leia rapidamente cada `.tf` (3 min) — veja o [README do Terraform](terraform/README.md) para um resumo.

---

## Atividade 1 — Lambda HTTP via Terraform

**Objetivo:** Provisionar uma AWS Lambda (Python 3.12) com API Gateway HTTP
API e fazer deploy de uma função HTTP simples (versão mock). Diferente do
Azure (que precisa do CLI `func`), o **Terraform já faz o deploy do código**
no próprio `apply` — não existe um passo separado de "publish".

### Passo 1 — Phase 1 do Terraform

Provisiona bucket S3 do catálogo + Lambda (v1-mock) + API Gateway. **Não cria o Elastic Beanstalk ainda.**

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform

terraform init
terraform apply -auto-approve
# lambda_version=v1-mock (default), beanstalk_enabled=false (default)
```

Tempo: ~1-2 min. Isso já cria o bucket do catálogo e sobe o `produtos.csv`. Anote os outputs (`lambda_function_name`, `api_gateway_url`).

### Passo 2 — Testar

```bash
API_URL=$(terraform output -raw api_gateway_url)
echo "$API_URL"

curl -s "$API_URL/health" | python3 -m json.tool
curl -s "$API_URL/produtos" | python3 -m json.tool
curl -s "$API_URL/produtos?categoria=eletronicos" | python3 -m json.tool
curl -s "$API_URL/produtos?nome=cadeira" | python3 -m json.tool
```

> **Primeira chamada pode demorar algumas centenas de ms a 1-2s** — cold
> start. Chamadas seguintes são mais rápidas (a Lambda fica "quente" por
> alguns minutos).

**✅ Checkpoint L₁:** O `curl` retorna JSON com lista de produtos mock?

---

## Atividade 2 — Lambda lendo S3 via IAM Role

**Objetivo:** Trocar o mock por dados reais do S3 do catálogo (criado nesta
aula). **Sem credenciais no código** — autenticação via a **IAM Role de
execução da Lambda** (`LabRole`, anexada no Terraform desde o Passo 1).

### Conferir o que já foi provisionado

Abra [terraform/lambda.tf](terraform/lambda.tf) e observe:

- **`role = data.aws_iam_role.lab_role.arn`** — a Lambda roda com a IAM Role
  pré-criada do Learner Lab (não criamos uma role nova — o Academy não deixa)
- **`environment.variables.S3_BUCKET_CATALOGO`** — variável de ambiente já
  injetada (nome do bucket S3 do catálogo desta aula)
- Não existe nenhum "role assignment" explícito de S3 aqui: a `LabRole` do
  Academy já vem com permissão ampla o suficiente para os serviços do
  Sandbox, incluindo S3 — diferente do Azure, onde tivemos que criar
  explicitamente um `azurerm_role_assignment` de "Storage Blob Data Reader"

> **Tudo isso já foi aplicado no Passo 1 da Atividade 1.** Só falta trocar o código.

### Passo 1 — Trocar para a versão v2-s3

A pasta [lambda/v2-s3/](lambda/v2-s3/) tem o código que **lê o CSV do S3 via
`boto3`** — sem chaves no código; o `boto3.client("s3")` pega as credenciais
automaticamente da execution role da Lambda.

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform

terraform apply -auto-approve -var="lambda_version=v2-s3"
```

Tempo: ~30s. O Terraform re-zipa o código de `lambda/v2-s3/` e atualiza a função.

### Passo 2 — Testar

```bash
API_URL=$(terraform output -raw api_gateway_url)

# Agora retorna os 20 produtos REAIS do S3!
curl -s "$API_URL/produtos?categoria=moveis" | python3 -m json.tool
curl -s "$API_URL/produtos?nome=cadeira" | python3 -m json.tool
```

> **Erro comum:** `AccessDenied` no S3 — raríssimo com `LabRole` (ela já vem
> ampla), mas se acontecer, confirme com `aws sts get-caller-identity` que
> as credenciais de sessão não expiraram (sessões de 4h; clique "Start Lab"
> de novo se precisar).

### Passo 3 — Reflexão (3 min)

Anote no `entrega-grupo-aula03.md` do seu grupo:

1. Procure por "key", "password", "credential", "secret" em todo o código
   da Lambda v2-s3. O que você encontra?
2. Como a Lambda consegue ler o S3 "sem credenciais"?
3. Se um agente em produção precisar acessar 5 buckets S3 diferentes, qual a
   estratégia recomendada?

**✅ Checkpoint L₂:** A Lambda retorna os 20 produtos reais do CSV?

---

## Atividade 3 — Container no Elastic Beanstalk

**Objetivo:** Levar o **mesmo código** (em FastAPI, empacotado em container)
para rodar no **Elastic Beanstalk** — a alternativa disponível no Academy à
falta de ECS/Fargate/EKS. A imagem já vem pronta (publicada no GHCR pelo
professor); o Elastic Beanstalk a **puxa diretamente do registry público**.

### Conferir o código FastAPI

[docker/app.py](docker/app.py) tem a mesma lógica da Lambda v2-s3 (lê S3 via
boto3), mas usando FastAPI. Ver [docker/README.md](docker/README.md) para o
porquê de não haver um passo de build/import do lado do aluno aqui (sem
Docker no CloudShell + cada sessão é uma conta AWS nova).

### Passo 1 — Habilitar o Elastic Beanstalk

Nenhum build, push ou import — o Terraform já sabe qual imagem pública usar
(`var.container_image`, default `ghcr.io/elthonf/produtos-api-aws:v1`):

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform

terraform apply -auto-approve -var="lambda_version=v2-s3" -var="beanstalk_enabled=true"
```

Tempo: ~4-6 min — o Elastic Beanstalk sobe uma instância EC2 `t3.micro`, faz
`docker pull` da imagem e inicia o container.

### Passo 2 — Testar

```bash
BEANSTALK_URL=$(terraform output -raw beanstalk_url)
echo "$BEANSTALK_URL"

curl "$BEANSTALK_URL/health"
curl "$BEANSTALK_URL/produtos?categoria=moveis"
```

### Passo 3 — Comparação Lambda vs Elastic Beanstalk (5 min)

| Aspecto | Lambda | Elastic Beanstalk |
|---------|--------|--------------------|
| URL | `https://<api-id>.execute-api.<região>.amazonaws.com/produtos` | `http://<env>.<região>.elasticbeanstalk.com/produtos` |
| TLS | ✅ Built-in (API Gateway) | ❌ Não por padrão (precisa `LoadBalanced` + ACM) |
| Cold start | Sim (100ms-1s) | Não há (instância sempre on) |
| Custo idle | $0 | $$ instância EC2 24/7 |
| Auto-scale | ✅ 0-N, nativo | ❌ 1 instância fixa (`SingleInstance`) |
| Linguagem | Runtime Lambda suportado | Qualquer (é container) |
| Identidade | `LabRole` anexada à função | `LabInstanceProfile` anexado à instância |

**Pergunta para o `entrega-grupo-aula03.md`:**

Para a QC, qual você levaria para produção da API de catálogo? Justifique em
3-5 frases considerando: tráfego esperado, custo, latência aceitável,
complexidade operacional. **Bônus:** e se a AWS liberasse ECS/Fargate no seu
ambiente de produção real (fora do Academy) — mudaria sua resposta? Por quê?

**✅ Checkpoint L₃:** Você fez deploy do mesmo código em 2 formas (Lambda + Elastic Beanstalk) e ambos respondem `/produtos`?

---

## Wrap-up — Destroy e custo zero (10 min)

### Passo 1 — Destruir o ambiente da Aula 3

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform

terraform destroy -auto-approve -var="lambda_version=v2-s3" -var="beanstalk_enabled=true"
```

Tempo: ~3-5 min (Elastic Beanstalk demora mais para derrubar a instância EC2). Tudo desta aula é removido — inclusive o bucket S3 do catálogo.

### Passo 2 — Verificar custo

No Vocareum, o painel do Learner Lab mostra o **budget restante** (dos US$
100) — confira que a sessão consumiu pouco. Diferente do Azure, não há um
"Cost Management" navegável em tempo real dentro da conta temporária.

---

## Conexão com o projeto Quantum Commerce

**Saída desta aula:**

- Lambda + API Gateway + Elastic Beanstalk provisionados via Terraform
- API de catálogo da QC funcionando em **2 sabores** — você decide qual leva para o projeto integrado final

**Para os agentes da QC (Aula 4 e disciplinas seguintes do MBA):**

A API que você implantou é a primeira **tool** que os agentes da QC vão consumir. Spec sugerida (a mesma da versão Azure — a tool não muda, só o backend):

```json
{
  "name": "buscar_produtos_qc",
  "description": "Busca produtos da Quantum Commerce por categoria ou nome",
  "input_schema": {
    "type": "object",
    "properties": {
      "categoria": {"type": "string", "description": "Categoria (ex: moveis, eletronicos)"},
      "nome":      {"type": "string", "description": "Substring do nome do produto"}
    }
  }
}
```

---

## Troubleshooting — Problemas comuns

| Problema | Causa | Solução |
|----------|-------|---------|
| `InvalidClientTokenId` / `ExpiredToken` em qualquer comando `aws`/`terraform` | Faltou o `aws_session_token` ou a sessão de 4h expirou | Recolar as 3 credenciais de `~/.aws/credentials` (ver Preparação); clicar "Start Lab" de novo se a sessão caducou |
| `terraform apply` → região negada / `AuthFailure` | Região fora de `us-east-1`/`us-west-2` | Usar `-var="aws_region=us-east-1"` (ou `us-west-2`) |
| Lambda retorna 500 "falha ao acessar S3" | Variável `S3_BUCKET_CATALOGO` não chegou ou objeto não subiu | Conferir `environment.variables` em `lambda.tf` + rodar `terraform apply` de novo |
| `aws_elastic_beanstalk_environment` falha citando `vockey` | Key pair `vockey` só existe por padrão em `us-east-1` | Rodando em `us-west-2`: `aws ec2 create-key-pair --key-name vockey --region us-west-2 --query "KeyMaterial" --output text > vockey.pem` antes do apply |
| `data.aws_elastic_beanstalk_solution_stack` não encontra nenhuma stack | AWS mudou o nome da plataforma Docker disponível | Rodar `aws elasticbeanstalk list-available-solution-stacks --query "SolutionStacks[?contains(@,'Docker')]"` e ajustar o `name_regex` em `beanstalk.tf` |
| Elastic Beanstalk fica "Severe"/"Degraded" | Imagem do GHCR está privada ou não existe | Professor: tornar `ghcr.io/elthonf/produtos-api-aws:v1` público (ver [docker/README.md](docker/README.md)) |
| Elastic Beanstalk sobe mas `curl` dá timeout | Instância ainda inicializando / security group | Aguardar 1-2 min; conferir status com `aws elasticbeanstalk describe-environments` |
| `terraform destroy` trava em `aws_elastic_beanstalk_environment` | Beanstalk demora a terminar a instância EC2 | Normal, aguardar — pode levar alguns minutos a mais que os outros recursos |
| `docker: command not found` no CloudShell | Esperado — CloudShell não tem daemon Docker | Não precisa de Docker no aluno; ver [docker/README.md](docker/README.md) (a imagem já vem pronta e pública) |

---

## Referências

- [AWS Academy — Learner Lab](https://awsacademy.instructure.com/)
- [AWS Lambda — Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [API Gateway HTTP API](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [boto3 — credenciais e execution role da Lambda](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html)
- [Elastic Beanstalk — plataforma Docker](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/single-container-docker.html)
- [Elastic Beanstalk vs ECS vs EKS](https://aws.amazon.com/blogs/containers/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
