# Terraform — Aula 3 (AWS)

Código IaC para provisionar a **camada de compute** da Quantum Commerce no
**AWS Academy Learner Lab**:

- Bucket S3 de catálogo **criado nesta aula** + upload automático do `produtos.csv`
- Lambda (Python 3.12) com `LabRole` anexada + API Gateway HTTP API
- Elastic Beanstalk (plataforma Docker, container único) — habilitado via flag
  `beanstalk_enabled` depois de publicar a imagem pública (ver
  [../docker/README.md](../docker/README.md))

> **Independente das demais aulas.** Este Terraform cria seu próprio bucket
> de catálogo e sobe o CSV no `apply`.

## Restrições do Learner Lab que moldam este código

| Restrição | Como o Terraform lida com isso |
|-----------|--------------------------------|
| Só `us-east-1`/`us-west-2` | `variable "aws_region"` com `validation` que rejeita qualquer outra região |
| Não pode criar IAM roles novas | `iam.tf` só **lê** (`data`) `LabRole`/`LabInstanceProfile` — nunca cria `aws_iam_role` |
| Sem ECS/Fargate/EKS/App Runner | Container roda em **Elastic Beanstalk** (Docker de container único) |
| Sessão nova a cada "Start Lab" (conta temporária) | Nenhum recurso pressupõe estado de uma sessão anterior — tudo nasce e morre dentro do `apply`/`destroy` da sessão atual |

## Como usar (no AWS CloudShell)

### Phase 1 — Provisionar tudo exceto Beanstalk (~2 min)

```bash
cd ~/aie-cloud/aulas/03-serverless-containers-aws/lab/terraform

terraform init
terraform apply -auto-approve
# beanstalk_enabled fica em false (default); lambda_version fica em v1-mock
```

Provisiona: bucket S3 do catálogo (com `produtos.csv`) + Lambda (v1-mock) + API Gateway.

### Trocar para a versão v2-s3 da Lambda (Atividade 2)

```bash
terraform apply -auto-approve -var="lambda_version=v2-s3"
```

### Phase 2 — Após publicar a imagem pública, habilitar o Beanstalk

```bash
terraform apply -auto-approve -var="lambda_version=v2-s3" -var="beanstalk_enabled=true"
```

### Destroy (regra de ouro — custo zero ao final)

```bash
terraform destroy -auto-approve -var="lambda_version=v2-s3" -var="beanstalk_enabled=true"
```

> Sempre repita as mesmas `-var` do último `apply` no `destroy`, ou o
> Terraform vai tentar recriar/remover recursos condicionais na ordem errada.

## Arquivos

| Arquivo | O que define |
|---------|--------------|
| [main.tf](main.tf) | Providers (aws, random, archive), sufixo aleatório, locals |
| [variables.tf](variables.tf) | `aws_region`, `lambda_version`, `beanstalk_enabled`, `container_image`, `ec2_key_pair_name` |
| [iam.tf](iam.tf) | `data` sources para `LabRole`/`LabInstanceProfile` (nunca cria roles) |
| [s3.tf](s3.tf) | Bucket do catálogo + upload do `produtos.csv` |
| [lambda.tf](lambda.tf) | Zip do código (v1-mock/v2-s3) + Lambda + API Gateway HTTP API |
| [beanstalk.tf](beanstalk.tf) | Elastic Beanstalk (application + application version + environment), condicional |
| [outputs.tf](outputs.tf) | `s3_bucket_catalogo`, `lambda_function_name`, `api_gateway_url`, `beanstalk_url` |

## Outputs disponíveis

```bash
terraform output -raw s3_bucket_catalogo
terraform output -raw lambda_function_name
terraform output -raw api_gateway_url
terraform output -raw beanstalk_url   # só faz sentido com beanstalk_enabled=true
```
