# Zips o código da versão escolhida (var.lambda_version). Terraform empacota
# e faz o deploy direto — não existe um CLI tipo 'func azure functionapp
# publish' na AWS: o 'aws_lambda_function' já sobe o zip no apply.
data "archive_file" "lambda_v1_mock" {
  type        = "zip"
  source_file = "${path.module}/../lambda/v1-mock/lambda_function.py"
  output_path = "${path.module}/.build/v1-mock.zip"
}

data "archive_file" "lambda_v2_s3" {
  type        = "zip"
  source_file = "${path.module}/../lambda/v2-s3/lambda_function.py"
  output_path = "${path.module}/.build/v2-s3.zip"
}

locals {
  lambda_zip_path = var.lambda_version == "v2-s3" ? data.archive_file.lambda_v2_s3.output_path : data.archive_file.lambda_v1_mock.output_path
  lambda_zip_hash = var.lambda_version == "v2-s3" ? data.archive_file.lambda_v2_s3.output_base64sha256 : data.archive_file.lambda_v1_mock.output_base64sha256
}

# Function HTTP da QC. A role de execução é a LabRole (pré-criada) — dá pro
# boto3 dentro do handler acessar o S3 sem nenhuma credencial no código,
# mesmo papel que a Managed Identity cumpria no Azure.
resource "aws_lambda_function" "catalogo" {
  function_name    = "qc-catalogo-${random_string.sufixo.result}"
  role             = data.aws_iam_role.lab_role.arn
  handler          = "lambda_function.handler"
  runtime          = "python3.12"
  filename         = local.lambda_zip_path
  source_code_hash = local.lambda_zip_hash
  timeout          = 10
  memory_size      = 256

  environment {
    variables = {
      S3_BUCKET_CATALOGO = local.bucket_name
    }
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.catalogo.function_name}"
  retention_in_days = 7
  tags              = local.tags
}

# API Gateway HTTP API (mais simples/barata que REST API) — equivalente ao
# trigger HTTP da Azure Function. payload_format_version 2.0 entrega o path
# em event["rawPath"] e a query string em event["queryStringParameters"].
resource "aws_apigatewayv2_api" "http_api" {
  name          = "qc-catalogo-api-${random_string.sufixo.result}"
  protocol_type = "HTTP"
  tags          = local.tags
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.catalogo.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "produtos" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /produtos"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
  tags        = local.tags
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.catalogo.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
