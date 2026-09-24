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

### Evitar "no space left on device"

O provider da AWS sozinho passa de 400-500MB — fácil de estourar o `$HOME`
persistente do CloudShell (~1GB, cota fixa). Antes do primeiro
`terraform init`, mande os plugins pro `/tmp` (disco efêmero da VM, bem
maior — não tem problema ser efêmero, a sessão do Academy já é temporária):

```bash
echo 'export TF_DATA_DIR=/tmp/tf-data' >> ~/.bashrc
export TF_DATA_DIR=/tmp/tf-data
mkdir -p $TF_DATA_DIR
```

> Se você já rodou `terraform init` antes de configurar isso e recebeu
> `no space left on device`, rode `rm -rf .terraform .terraform.lock.hcl`
> dentro de `lab/terraform` e refaça o `init` depois de exportar a variável
> acima — ela só vale pro terminal atual, então se abrir um terminal novo do
> CloudShell é só conferir com `echo $TF_DATA_DIR` (o `.bashrc` já cobre
> isso a partir de agora).

### Confirmar ferramentas

```bash
aws sts get-caller-identity   # confirma que as credenciais da sessão estão válidas
terraform -version
docker --version   # CloudShell tem Docker desde jan/2024 — usado na Atividade 3
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
falta de ECS/Fargate/EKS. A imagem é buildada e publicada no **ECR desta
mesma conta**, e o Elastic Beanstalk a **puxa diretamente de lá**.

### Conferir o código FastAPI

[docker/app.py](docker/app.py) tem a mesma lógica da Lambda v2-s3 (lê S3 via
boto3), mas usando FastAPI. O **AWS CloudShell tem Docker** desde jan/2024
(inclusive em `us-east-1`/`us-west-2`), então o build acontece direto ali —
ver [docker/README.md](docker/README.md) para detalhes.

### Passo 1 — Build e push da imagem pro ECR

O Terraform já criou o repositório ECR desde a Atividade 1 (`ecr.tf`, mesmo
com `beanstalk_enabled=false`). Falta só buildar e publicar a imagem nele:

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform
ECR_URL=$(terraform output -raw ecr_repository_url)
cd ../docker

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$ECR_URL"
docker build --platform linux/amd64 -t "$ECR_URL:v1" .
docker push "$ECR_URL:v1"
```

> Troque `us-east-1` pela região que você está usando, se for `us-west-2`.
> Detalhes completos em [docker/README.md](docker/README.md).

### Passo 2 — Habilitar o Elastic Beanstalk

O `Dockerrun.aws.json` já referencia `ecr_repository_url:v1` automaticamente
— não precisa passar nenhuma variável de imagem:

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform

terraform apply -auto-approve -var="lambda_version=v2-s3" -var="beanstalk_enabled=true"
```

Tempo: ~4-6 min — o Elastic Beanstalk sobe uma instância EC2 `t3.micro`, faz
`docker pull` do ECR (via `LabInstanceProfile`, sem credencial extra) e
inicia o container.

### Passo 3 — Testar

```bash
BEANSTALK_URL=$(terraform output -raw beanstalk_url)
echo "$BEANSTALK_URL"

curl "$BEANSTALK_URL/health"
curl "$BEANSTALK_URL/produtos?categoria=moveis"
```

### Passo 4 — Comparação Lambda vs Elastic Beanstalk (5 min)

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
| `data.aws_iam_role.lab_role` → `couldn't find resource` / `NoSuchEntity` para `LabRole`/`LabInstanceProfile` (confirmado também via `aws iam get-role`) | Você entrou por um curso/módulo do AWS Academy diferente do "Cloud Developing" — nem todo sandbox da Academy provisiona `LabRole`/`LabInstanceProfile` (alguns, como trilhas de Data Engineering, só têm papéis de serviço tipo `EMR_DefaultRole`) | Volte em `awsacademy.instructure.com` e entre pelo curso/módulo certo (o que tem "Cloud Developing" ou equivalente); `aws iam list-roles` ajuda a confirmar o que existe na conta antes de gastar tempo depurando o Terraform |
| `NoSuchBucket` ao criar `aws_s3_bucket_public_access_block`/`aws_s3_object`, com um bucket que já tinha "sido criado" numa sessão anterior | `terraform.tfstate` antigo (de uma sessão/conta AWS anterior) ainda está na pasta — o Terraform acha que o bucket/`null_resource` já existe e não tenta recriar, mas a conta atual é outra e nunca teve esse recurso | Rodando numa conta/sessão nova: `rm -f terraform.tfstate terraform.tfstate.backup` antes do `apply` (não precisa mexer em `.terraform/`) |
| `AccessDenied: ... GetBucketObjectLockConfiguration ... explicit deny` no bucket do catálogo | Bug antigo e conhecido do provider AWS: o recurso `aws_s3_bucket` sempre tenta ler o Object Lock do bucket, e a `LabRole` nega essa chamada — acontece em qualquer versão do provider | Já corrigido no `s3.tf` (o bucket é criado via AWS CLI num `null_resource`, não via `aws_s3_bucket`). Se aparecer de novo, rode `git pull` pra garantir que está com a versão mais recente do lab |
| `terraform init`/`apply` → `no space left on device` | `$HOME` do CloudShell é persistente mas só tem ~1GB, e o provider da AWS sozinho passa de 400MB | Configure `TF_DATA_DIR=/tmp/tf-data` **antes** do `init` (ver Preparação); se já tinha rodado `init` sem isso: `rm -rf .terraform .terraform.lock.hcl` e refaça o `init` |
| `Error: Inconsistent dependency lock file` | O `.terraform.lock.hcl` ainda referencia uma versão de provider antiga (ex.: depois de um `git pull` que mudou `main.tf`) | Rode o `terraform init -upgrade` que a própria mensagem sugere |
| `terraform apply` → região negada / `AuthFailure` | Região fora de `us-east-1`/`us-west-2` | Usar `-var="aws_region=us-east-1"` (ou `us-west-2`) |
| Lambda retorna 500 "falha ao acessar S3" | Variável `S3_BUCKET_CATALOGO` não chegou ou objeto não subiu | Conferir `environment.variables` em `lambda.tf` + rodar `terraform apply` de novo |
| `aws_elastic_beanstalk_environment` falha citando `vockey` | Key pair `vockey` só existe por padrão em `us-east-1` | Rodando em `us-west-2`: `aws ec2 create-key-pair --key-name vockey --region us-west-2 --query "KeyMaterial" --output text > vockey.pem` antes do apply |
| `data.aws_elastic_beanstalk_solution_stack` não encontra nenhuma stack | AWS mudou o nome da plataforma Docker disponível | Rodar `aws elasticbeanstalk list-available-solution-stacks --query "SolutionStacks[?contains(@,'Docker')]"` e ajustar o `name_regex` em `beanstalk.tf` |
| Elastic Beanstalk fica "Severe"/"Degraded" | Imagem não foi publicada no ECR antes do `beanstalk_enabled=true`, ou o push foi pra tag/repositório errado | Confira `terraform output ecr_repository_url` e refaça o `docker push` (Passo A do [docker/README.md](docker/README.md)) — depois reaplique |
| Elastic Beanstalk sobe mas `curl` dá timeout | Instância ainda inicializando / security group | Aguardar 1-2 min; conferir status com `aws elasticbeanstalk describe-environments` |
| `terraform destroy` trava em `aws_elastic_beanstalk_environment` | Beanstalk demora a terminar a instância EC2 | Normal, aguardar — pode levar alguns minutos a mais que os outros recursos |
| `docker: command not found` no CloudShell | Raro — CloudShell tem Docker desde jan/2024 em todas as regiões comerciais | Confirme com `docker --version`; se realmente faltar, veja o changelog do CloudShell na sua conta/região |

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
