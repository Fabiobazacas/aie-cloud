output "s3_bucket_catalogo" {
  description = "Bucket S3 do catálogo (criado nesta aula, já com produtos.csv)"
  value       = aws_s3_bucket.catalogo.bucket
}

# Lambda + API Gateway
output "lambda_function_name" {
  description = "Nome da função Lambda"
  value       = aws_lambda_function.catalogo.function_name
}

output "api_gateway_url" {
  description = "URL base da API Gateway HTTP API (ex.: <url>/produtos, <url>/health)"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

# Elastic Beanstalk (condicional)
output "beanstalk_url" {
  description = "URL do Elastic Beanstalk quando habilitado; do contrário, mensagem"
  value       = var.beanstalk_enabled ? "http://${aws_elastic_beanstalk_environment.qc[0].cname}" : "Beanstalk ainda não habilitado — publique a imagem (docker/README.md) e rode 'terraform apply' com -var beanstalk_enabled=true"
}
