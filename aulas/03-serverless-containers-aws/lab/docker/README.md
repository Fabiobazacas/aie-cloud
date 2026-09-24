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

## Onde buildar e pra onde publicar

O **AWS CloudShell tem Docker** desde jan/2024, em todas as regiões
comerciais — inclusive `us-east-1` e `us-west-2`, as únicas liberadas no
Learner Lab. Então o build acontece **direto no CloudShell**, sem precisar
de máquina própria, Codespace, ou qualquer registry externo.

O destino é o **ECR desta mesma conta**: o Terraform (`ecr.tf`) já cria o
repositório na Phase 1 do apply (mesmo com `beanstalk_enabled=false`) — só
falta o aluno buildar a imagem e dar push nele antes de habilitar o
Beanstalk. É a mesma ordem da versão Azure (ACR primeiro, depois o app que
consome a imagem), só que tudo dentro da mesma sessão/conta temporária —
sem passo de "publicar uma vez pra turma toda".

## Passo A — Build e push pro ECR (ALUNO, no CloudShell)

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform
ECR_URL=$(terraform output -raw ecr_repository_url)
cd ../docker

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$ECR_URL"

# IMPORTANTE: Elastic Beanstalk roda linux/amd64 — force a plataforma (essencial em Mac ARM)
docker build --platform linux/amd64 -t "$ECR_URL:v1" .
docker push "$ECR_URL:v1"
```

> Troque `us-east-1` pela região que você está usando, se for `us-west-2`
> (mesma região do `terraform apply`).

## Passo B — Habilitar o Beanstalk (ALUNO, no CloudShell)

Com a imagem já publicada no ECR, só apontar o Terraform pra habilitar o
Beanstalk (o `Dockerrun.aws.json` já referencia `ecr_repository_url:v1`
automaticamente, sem precisar passar nenhuma variável):

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform

terraform apply -auto-approve -var="lambda_version=v2-s3" -var="beanstalk_enabled=true"
```

Tempo: ~4-6 min — Elastic Beanstalk sobe uma instância EC2, faz `docker
pull` do ECR (via `LabInstanceProfile`, sem credencial extra) e inicia o
container.

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
