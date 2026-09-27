# Terraform — Aula 5 (AI Agents, AWS) — camada de gatilho opcional

Este Terraform é **opcional**. O lab inteiro (API + Streamlit + ciclo do
agente) roda 100% local, com custo zero, sem nenhum destes recursos. Ele só
existe pra quem quiser demonstrar o gatilho por evento de verdade na nuvem —
o equivalente ao "Nível 3" da escada da continuidade rodando fora do laptop.

Provisiona:

- Bucket S3 de **entrada** (`s3.tf`) — onde um `.json` de nota chega
- Fila SQS (`sqs.tf`) que recebe o evento `S3:ObjectCreated` do bucket
- Policy do SQS liberando o S3 a publicar mensagens (resource policy, não
  precisa de IAM role nova)

## Restrições do Learner Lab que moldam este código

| Restrição | Como o Terraform lida com isso |
|-----------|--------------------------------|
| Só `us-east-1`/`us-west-2` | `variable "aws_region"` com `validation` |
| Não pode criar IAM roles novas | Nenhum recurso aqui precisa de uma — S3→SQS usa resource policy, não role |
| `LabRole` nega `s3:GetBucketObjectLockConfiguration` | O bucket **não** usa `aws_s3_bucket` — criado via CLI num `null_resource` (ver [s3.tf](s3.tf), mesmo padrão das Aulas 3/4) |
| Sessão nova a cada "Start Lab" | Nada pressupõe estado de sessão anterior |

## Como usar

```bash
cd ~/aie-cloud/aulas/05-ai-agents-aws/lab/terraform
terraform init
terraform apply -auto-approve

# usar no gatilho:
python3 ../gatilho/disparador.py --observar --nuvem --fila-url "$(terraform output -raw sqs_queue_url)"

# subir uma nota de teste:
BUCKET=$(terraform output -raw bucket_entrada)
echo '{"fornecedor":"Teste","descricao":"nota de teste via S3","categoria_solicitada":"teste","valor":10}' > /tmp/nota-teste.json
aws s3 cp /tmp/nota-teste.json "s3://$BUCKET/nota-teste.json"
```

## Destroy (regra de ouro — custo zero ao final)

```bash
terraform destroy -auto-approve
```

## Arquivos

| Arquivo | O que define |
|---------|--------------|
| [main.tf](main.tf) | Providers, sufixo aleatório, locals (tags) |
| [variables.tf](variables.tf) | `aws_region` |
| [s3.tf](s3.tf) | Bucket de entrada (via CLI) + notificação S3→SQS |
| [sqs.tf](sqs.tf) | Fila SQS + policy que permite o S3 publicar nela |
| [outputs.tf](outputs.tf) | `bucket_entrada`, `sqs_queue_url` |
