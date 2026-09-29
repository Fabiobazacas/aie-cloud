# Terraform — Aula 4 (AWS): Pipeline de RAG

Código IaC completo pro pipeline de RAG da Quantum Commerce:

- Bucket S3 de documentos + upload automático do `catalogo_qc.pdf`
- RDS PostgreSQL 16 (pgvector habilitado via SQL depois do apply)
- Rede dedicada: NAT Gateway + subnet privada pra Lambda alcançar o Gemini
  (API externa — não é um serviço AWS, então não dá pra usar VPC endpoint)
- Lambda (Python 3.12) com PyMuPDF + psycopg2 + pgvector, atrás de uma API
  Gateway HTTP API com 4 rotas: `/health`, `/transcrever`, `/indexar`, `/perguntar`

## Restrições do Learner Lab que moldam este código

| Restrição | Como o Terraform lida com isso |
|-----------|--------------------------------|
| Só `us-east-1`/`us-west-2` | `variable "aws_region"` com `validation` |
| Não pode criar IAM roles novas | `iam.tf` só **lê** (`data`) a `LabRole` — nunca cria `aws_iam_role` |
| `LabRole` nega `s3:GetBucketObjectLockConfiguration` | O bucket **não** usa `aws_s3_bucket` — criado via CLI num `null_resource` (ver `s3.tf`, mesmo padrão das Aulas 3/5) |
| Lambda com dependências compiladas (PyMuPDF, psycopg2) | `lambda.tf` baixa wheels `manylinux2014_x86_64` via `pip install --platform ... --only-binary=:all:` antes de zipar — funciona não importa de onde o `apply` roda |
| Gemini é externo à AWS (não dá VPC Endpoint) | `network.tf` cria um NAT Gateway + subnet dedicada só pra isso — custo real (~US$0,045/h + por GB), documentado no material |

## Como usar

```bash
cd ~/aie-cloud/aulas/04-servicos-cognitivos-aws/lab/terraform
terraform init
terraform apply -auto-approve -var="gemini_api_key=$GEMINI_API_KEY"
```

`gemini_api_key` é obrigatória e sensível — nunca commite um `.tfvars` com
ela. Passe sempre via `-var` (ou `TF_VAR_gemini_api_key` no ambiente).

## Destroy (regra de ouro — custo zero ao final)

```bash
terraform destroy -auto-approve -var="gemini_api_key=$GEMINI_API_KEY"
```

## Arquivos

| Arquivo | O que define |
|---------|--------------|
| [main.tf](main.tf) | Providers, sufixo aleatório, locals (tags) |
| [variables.tf](variables.tf) | `aws_region`, `gemini_api_key` |
| [iam.tf](iam.tf) | `data` source pra `LabRole` |
| [s3.tf](s3.tf) | Bucket de documentos (via CLI) + upload do `catalogo_qc.pdf` |
| [network.tf](network.tf) | NAT Gateway + subnet dedicada + Security Groups |
| [rds.tf](rds.tf) | RDS PostgreSQL 16 + subnet group |
| [lambda.tf](lambda.tf) | Build da Lambda (deps manylinux) + API Gateway + 4 rotas |
| [outputs.tf](outputs.tf) | `rag_docs_bucket`, `rds_endpoint`, `rds_secret_arn`, `lambda_function_name`, `api_gateway_url` |

## Outputs disponíveis

```bash
terraform output -raw rag_docs_bucket
terraform output -raw rds_endpoint
terraform output -raw rds_secret_arn
terraform output -raw api_gateway_url
```
