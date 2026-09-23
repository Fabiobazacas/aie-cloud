# Container code — Aula 3 (AWS)

Versão **FastAPI** da API de catálogo da QC, com a mesma lógica de negócio da
Lambda `v2-s3`, empacotada num **container Docker** para rodar no **AWS
Elastic Beanstalk** (plataforma Docker, container único).

## Arquivos

| Arquivo | O que é |
|---------|---------|
| [app.py](app.py) | API FastAPI com endpoints `/health` e `/produtos` (lê do S3 via boto3) |
| [requirements.txt](requirements.txt) | Dependências (FastAPI + Uvicorn + boto3) |
| [Dockerfile](Dockerfile) | Multi-stage build, imagem final leve (~150 MB) |

## Por que não buildar/importar no CloudShell?

O **AWS CloudShell não tem daemon Docker** (mesma limitação do Azure Cloud
Shell) — `docker build` não roda ali. E diferente do Azure (onde cada aluno
tinha sua própria subscription persistente e podia `az acr import` uma
imagem pronta pro seu ACR), no **Learner Lab cada sessão é uma conta AWS
nova e temporária**: não existe "o ECR do aluno" antes da sessão começar, e a
AWS não tem um comando de "importar de outro registry" que não precise de
Docker (ao contrário do `az acr import`).

**Solução:** a imagem é **construída e publicada uma vez no GHCR pelo
professor** (registry público, fora da conta AWS), e o **Elastic Beanstalk
puxa essa imagem pública diretamente** via `Dockerrun.aws.json` — sem
nenhum passo de ECR do lado do aluno. O Terraform (`beanstalk.tf`) já gera
esse `Dockerrun.aws.json` sozinho a partir da variável `container_image`.

> **ECR continua disponível** no Sandbox se você quiser experimentar
> manualmente (build local + `docker push` para o seu próprio ECR), mas
> **não é o caminho guiado deste lab** — não é necessário para os checkpoints.

## Passo A — Publicar no GHCR (PROFESSOR, 1× por turma)

Feito numa máquina/Codespace **com Docker** (Codespaces já é `linux/amd64`, ideal):

```bash
export GHCR_PAT=ghp_seu_token_aqui   # Settings → Developer settings → Personal access tokens (classic) → escopo write:packages

cd aulas/03-serverless-containers-aws/lab/docker

echo "$GHCR_PAT" | docker login ghcr.io -u elthonf --password-stdin

# IMPORTANTE: Elastic Beanstalk roda linux/amd64 — force a plataforma (essencial em Mac ARM)
docker build --platform linux/amd64 -t ghcr.io/elthonf/produtos-api-aws:v1 .
docker push ghcr.io/elthonf/produtos-api-aws:v1
```

Depois, **torne o package público** (nasce privado por padrão, e o Elastic
Beanstalk do aluno não tem como autenticar num pull privado):

GitHub → **Packages → produtos-api-aws → Package settings → Danger Zone → Change visibility → Public**

> Ajuste `elthonf` para o owner real do GHCR, se for outro, e atualize
> `variables.tf` (`container_image`) e o exemplo no `guia-lab.md` de acordo.

## Passo B — Habilitar o Beanstalk (ALUNO, no CloudShell)

Nenhum build, push ou import — só apontar o Terraform pra imagem pública já publicada:

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform

terraform apply -auto-approve -var="lambda_version=v2-s3" -var="beanstalk_enabled=true"
```

Tempo: ~4-6 min — Elastic Beanstalk sobe uma instância EC2, faz `docker pull`
da imagem e inicia o container.

## Testar o Beanstalk

```bash
BEANSTALK_URL=$(cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform && terraform output -raw beanstalk_url)
echo "$BEANSTALK_URL"

curl "$BEANSTALK_URL/health"
curl "$BEANSTALK_URL/produtos?categoria=moveis"
```

> **Nota:** Elastic Beanstalk `SingleInstance` não tem load balancer nem TLS
> gerenciado por padrão (só HTTP). Em produção, trocar `EnvironmentType` para
> `LoadBalanced` (Application Auto Scaling + ELB — ambos disponíveis no
> Sandbox) dá HTTPS via ACM + escala automática.

## Comparação com a Lambda (mesma lógica, runtime diferente)

| Aspecto | Lambda v2-s3 | Elastic Beanstalk (este container) |
|---------|--------------|-------------------------------------|
| URL | `https://<api-id>.execute-api.<região>.amazonaws.com/produtos` | `http://<env>.<região>.elasticbeanstalk.com/produtos` |
| TLS | ✅ Built-in (API Gateway) | ❌ Não por padrão (precisa ELB + ACM) |
| Cold start | Sim (100ms-1s) | Não há (instância sempre on) |
| Custo idle | $0 | $$ instância EC2 rodando 24/7 |
| Auto-scale | ✅ Nativo, a zero | ❌ 1 instância fixa (`SingleInstance`) — precisa `LoadBalanced` p/ escalar |
| Linguagem | Qualquer runtime Lambda suportado | Qualquer (é container) |
| Identidade | `LabRole` anexada à função | `LabInstanceProfile` anexado à instância EC2 |
