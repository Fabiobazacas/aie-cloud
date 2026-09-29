output "rag_docs_bucket" {
  description = "Bucket S3 de documentos (criado nesta aula, já com catalogo_qc.pdf)"
  value       = local.bucket_name
}

output "rds_endpoint" {
  description = "Endpoint do RDS PostgreSQL (host, sem porta)"
  value       = aws_db_instance.rag.address
}

output "rds_secret_arn" {
  description = "ARN do secret no Secrets Manager com usuário/senha do RDS"
  value       = aws_db_instance.rag.master_user_secret[0].secret_arn
}

output "lambda_function_name" {
  description = "Nome da função Lambda de RAG"
  value       = aws_lambda_function.rag.function_name
}

output "api_gateway_url" {
  description = "URL base da API (ex.: <url>/health, <url>/transcrever, <url>/indexar, <url>/perguntar)"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}
