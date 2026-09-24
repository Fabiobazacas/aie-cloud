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
| `LabRole` nega `s3:GetBucketObjectLockConfiguration` | O bucket do catálogo **não** usa o recurso `aws_s3_bucket` (seu Read dispara essa chamada e quebra o apply) — é criado via AWS CLI num `null_resource` (ver [s3.tf](s3.tf)) |

## Como usar (no AWS CloudShell)

### Phase 0 — Instalar o Terraform (1x por CloudShell, não vem pré-instalado)

```bash
command -v terraform >/dev/null || {
  curl -sSL -o /tmp/terraform.zip https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip
  unzip -o /tmp/terraform.zip -d ~/bin
  echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc
  export PATH=$HOME/bin:$PATH
}
terraform -version
```

### Phase 0.5 — Evitar "no space left on device"

O provider da AWS sozinho passa de 400-500MB — fácil de estourar o `$HOME`
persistente do CloudShell (~1GB). Manda os plugins pro `/tmp` antes do
`init` (ver [guia-lab.md](../guia-lab.md), seção Preparação, para detalhes):

```bash
echo 'export TF_DATA_DIR=/tmp/tf-data' >> ~/.bashrc
export TF_DATA_DIR=/tmp/tf-data
mkdir -p $TF_DATA_DIR
```

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
| [main.tf](main.tf) | Providers (aws, random, archive, null), sufixo aleatório, locals |
| [variables.tf](variables.tf) | `aws_region`, `lambda_version`, `beanstalk_enabled`, `container_image`, `ec2_key_pair_name` |
| [iam.tf](iam.tf) | `data` sources para `LabRole`/`LabInstanceProfile` (nunca cria roles) |
| [s3.tf](s3.tf) | Bucket do catálogo (via CLI, não `aws_s3_bucket` — ver acima) + upload do `produtos.csv` |
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
