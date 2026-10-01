output "bucket" {
  description = "Bucket S3 da aula (entradas: documents/ audios/ images/ images-3d/; saídas: chunks/ entities/ transcriptions/ campaigns/ models3d/ jobs/)"
  value       = local.bucket_name
}

output "api_gateway_url" {
  description = "URL base da API (ex.: <url>/process, <url>/rag/query, <url>/ner, <url>/transcribe, <url>/campaign, <url>/convert3d)"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "rds_endpoint" {
  description = "Endpoint do RDS PostgreSQL (null com habilitar_rag = false)"
  value       = try(aws_db_instance.rag[0].address, null)
}

output "rds_secret_arn" {
  description = "ARN do secret no Secrets Manager com usuário/senha do RDS (null com habilitar_rag = false)"
  value       = try(aws_db_instance.rag[0].master_user_secret[0].secret_arn, null)
}

output "dynamodb_entities" {
  description = "Tabela DynamoDB do Exercício 03 (NER)"
  value       = aws_dynamodb_table.entities.name
}

output "dynamodb_transcriptions" {
  description = "Tabela DynamoDB do Exercício 04 (transcrições)"
  value       = aws_dynamodb_table.transcriptions.name
}

output "lambdas" {
  description = "Nome real de cada função Lambda (para logs: aws logs tail /aws/lambda/<nome> --follow)"
  value       = { for nome, fn in aws_lambda_function.fn : nome => fn.function_name }
}
