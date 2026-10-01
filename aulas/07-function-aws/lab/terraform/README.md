# Terraform — Aula 7 (AWS): Pipelines Cognitivos Serverless

Um `terraform apply` cria tudo da aula no AWS Academy Learner Lab.

## Recursos

| Recurso | Arquivo | Observação |
|---------|---------|------------|
| Bucket S3 + upload de `lab/data/**` | `s3.tf` | Criado via AWS CLI (`null_resource`): o recurso `aws_s3_bucket` dispara `GetBucketObjectLockConfiguration`, negado pela LabRole |
| S3 Event Notification (`images-3d/` → Lambda) | `s3.tf` | Gatilho do Desafio |
| 6 Lambdas (Python 3.12) | `lambda.tf` | Zip montado em `/tmp` com wheels `manylinux2014_x86_64`; `LabRole` como execution role |
| API Gateway HTTP API + rotas | `api.tf` | Timeout de integração: 29 s (por isso o modo `async`) |
| 2 tabelas DynamoDB | `dynamodb.tf` | Billing `PAY_PER_REQUEST` |
| RDS PostgreSQL 16 + NAT Gateway + subnet | `rds.tf`, `network.tf` | **Só com `habilitar_rag = true`** |

## Variáveis

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `gemini_api_key` | — (obrigatória) | Chave do Gemini **do grupo**. `sensitive`. Nunca commitar. |
| `habilitar_rag` | `true` | `false` = sem RDS/NAT/Ex01/Ex02 (deploy ~2 min) |
| `aws_region` | `us-east-1` | Só `us-east-1` ou `us-west-2` no Learner Lab |
| `hf_token` | `""` | Token HuggingFace **do grupo** (Read, gratuito). `sensitive`. Usado pelo Ex05 e pelo Desafio — sem ele a cota anônima de GPU acaba em 1–2 chamadas |
| `hf_edit_space` | `black-forest-labs/FLUX.1-Kontext-Dev` | Space de edição de imagem (image-to-image) do Ex05 |
| `provedores_imagem` | `gemini,hf` | Ordem dos provedores de imagem do Ex05 (o free tier do Gemini não tem cota de imagem, então quem edita é o `hf`) |
| `trellis_space` | `trellis-community/TRELLIS` | Space do Desafio 3D (o `microsoft/TRELLIS` original está em `CONFIG_ERROR`) |
| `gemini_image_model` | `gemini-2.5-flash-image` | Modelo de imagem do Gemini, usado só se `gemini` estiver em `provedores_imagem` |

## Uso

```bash
export TF_DATA_DIR=/tmp/tf-data-aula7 && mkdir -p $TF_DATA_DIR
terraform init
terraform apply -auto-approve -var="gemini_api_key=$GEMINI_API_KEY"
terraform output
terraform destroy -auto-approve -var="gemini_api_key=$GEMINI_API_KEY"
```

## Decisões de desenho (para discutir em aula)

- **Só as Lambdas de RAG ficam na VPC.** O RDS é privado, então Ex01/Ex02 precisam estar na VPC — e, como o Gemini é uma API externa, precisam de um NAT Gateway. Ex03, 04, 05 e o Desafio não falam com o RDS: ficam fora da VPC, com internet direta e sem NAT.
- **Sem credenciais no código.** S3, DynamoDB e Secrets Manager são acessados pela `LabRole`. A única chave de verdade (Gemini) chega por variável de ambiente.
- **Zero retries em invocação assíncrona** (`aws_lambda_function_event_invoke_config`): o padrão da AWS é tentar 2 vezes, o que repetiria chamadas pagas ao LLM.
- **Código compartilhado empacotado em cada Lambda** (`shared/`, `prompts/`): simples de ler e de depurar; em produção seria uma Lambda Layer.
