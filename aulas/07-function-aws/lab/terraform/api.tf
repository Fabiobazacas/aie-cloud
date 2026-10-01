# Uma única API Gateway HTTP API na frente das 6 Lambdas — equivalente aos
# HTTP Triggers das Azure Functions (POST /api/process, /api/ner, ...).
resource "aws_apigatewayv2_api" "http_api" {
  name          = "aula2-api-${random_string.sufixo.result}"
  protocol_type = "HTTP"
  tags          = local.tags
}

resource "aws_apigatewayv2_integration" "lambda" {
  for_each = local.lambda_cfg

  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.fn[each.key].invoke_arn
  payload_format_version = "2.0"

  # Máximo da API Gateway HTTP API. Pipelines mais longos usam "async": true.
  timeout_milliseconds = 29000
}

locals {
  # rota -> Lambda dona dela
  rotas_todas = {
    "GET /health"       = "ex01_chunker"
    "POST /process"     = "ex01_chunker"
    "POST /rag/query"   = "ex02_rag"
    "GET /rag/chunks"   = "ex02_rag"
    "POST /ner"         = "ex03_ner"
    "POST /transcribe"  = "ex04_speech"
    "POST /campaign"    = "ex05_marketing"
    "POST /convert3d"   = "desafio_3d"
  }

  rotas = { for rota, lambda in local.rotas_todas : rota => lambda if contains(keys(local.lambda_cfg), lambda) }
}

resource "aws_apigatewayv2_route" "rota" {
  for_each = local.rotas

  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = each.key
  target    = "integrations/${aws_apigatewayv2_integration.lambda[each.value].id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
  tags        = local.tags
}

resource "aws_lambda_permission" "apigw" {
  for_each = local.lambda_cfg

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fn[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# Permite o S3 invocar a Lambda do Desafio (S3 Event Notification — ver s3.tf).
resource "aws_lambda_permission" "s3_desafio" {
  statement_id   = "AllowS3Invoke"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.fn["desafio_3d"].function_name
  principal      = "s3.amazonaws.com"
  source_arn     = "arn:aws:s3:::${local.bucket_name}"
  source_account = data.aws_caller_identity.current.account_id
}
