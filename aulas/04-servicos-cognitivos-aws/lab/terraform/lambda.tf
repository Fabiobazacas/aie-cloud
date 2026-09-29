# A Lambda desta aula usa duas dependências com extensão compilada
# (PyMuPDF e psycopg2) que NÃO vêm no runtime padrão da Lambda — diferente
# do boto3 (já embutido). Por isso, antes de zipar, baixamos os wheels
# pré-compilados pro Linux/x86_64 da Lambda (--platform manylinux2014_x86_64
# --only-binary=:all:), mesmo rodando o apply no CloudShell — assim o
# resultado é sempre compatível, não importa de onde o Terraform roda.
#
# O build vai pra /tmp, NUNCA pra dentro do repo: o $HOME do CloudShell é
# persistente mas tem só ~1GB de cota, e o pip baixa/instala o PyMuPDF (que
# sozinho passa de 20MB extraído) usando um diretório de staging dentro do
# próprio /tmp antes de mover pro --target. Se o --target estivesse dentro
# do repo (outro filesystem, montado por FUSE no CloudShell), esse "mover"
# vira uma cópia (Errno 18: Invalid cross-device link) que multiplica o
# espaço usado e estoura a cota do $HOME — inclusive impedindo o próprio
# Terraform de gravar o terraform.tfstate. Usando /tmp pros dois lados, o
# pip faz um rename de verdade (mesmo filesystem) e nada disso acontece.
#
# Só que /tmp é EFÊMERO entre sessões do CloudShell (limpa ao reconectar),
# enquanto o terraform.tfstate (no $HOME, persistente) continua achando
# que este null_resource já rodou — erro real visto: "archive_file" tenta
# zipar um diretório que sumiu do /tmp numa sessão nova, mesmo sem nenhuma
# mudança no código. always_run com timestamp() força reexecutar o build
# em TODO apply, garantindo que /tmp esteja sempre consistente com o que
# o Terraform espera — custa alguns segundos a mais por apply, mas nunca
# quebra por causa disso.
resource "null_resource" "lambda_build" {
  triggers = {
    requirements = filemd5("${path.module}/../lambda/requirements.txt")
    codigo       = filemd5("${path.module}/../lambda/lambda_function.py")
    always_run   = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      rm -rf "/tmp/qc-rag-lambda-build-${random_string.sufixo.result}"
      mkdir -p "/tmp/qc-rag-lambda-build-${random_string.sufixo.result}"
      pip install \
        --platform manylinux2014_x86_64 \
        --implementation cp \
        --python-version 3.12 \
        --only-binary=:all: \
        --target "/tmp/qc-rag-lambda-build-${random_string.sufixo.result}" \
        -r "${path.module}/../lambda/requirements.txt" \
        -q
      cp "${path.module}/../lambda/lambda_function.py" "/tmp/qc-rag-lambda-build-${random_string.sufixo.result}/"
    EOT
  }
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "/tmp/qc-rag-lambda-build-${random_string.sufixo.result}"
  output_path = "/tmp/qc-rag-lambda-build-${random_string.sufixo.result}.zip"
  depends_on  = [null_resource.lambda_build]
}

resource "aws_lambda_function" "rag" {
  function_name    = "qc-rag-${random_string.sufixo.result}"
  role             = data.aws_iam_role.lab_role.arn
  handler          = "lambda_function.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 30 # cada página chama o Gemini de forma síncrona — PDFs grandes precisam de mais tempo
  memory_size      = 512

  vpc_config {
    subnet_ids         = [aws_subnet.lambda_privada.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DOCS_BUCKET    = local.bucket_name
      DB_HOST        = aws_db_instance.rag.address
      DB_SECRET_ARN  = aws_db_instance.rag.master_user_secret[0].secret_arn
      GEMINI_API_KEY = var.gemini_api_key
    }
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.rag.function_name}"
  retention_in_days = 7
  tags              = local.tags
}

resource "aws_apigatewayv2_api" "http_api" {
  name          = "qc-rag-api-${random_string.sufixo.result}"
  protocol_type = "HTTP"
  tags          = local.tags
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.rag.invoke_arn
  payload_format_version = "2.0"

  # Chamadas ao Gemini (embedding + geração) por página/pergunta podem
  # passar dos 5s padrão do proxy da API Gateway em PDFs maiores.
  timeout_milliseconds = 29000
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# RDS é privado (publicly_accessible = false) e só a Lambda está na VPC que
# alcança essa subnet — por isso o schema (CREATE EXTENSION/TABLE/INDEX) e a
# conferência de linhas rodam aqui, não via psql direto do CloudShell.
resource "aws_apigatewayv2_route" "setup_db" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /setup-db"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "status" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /status"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "transcrever" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /transcrever"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "indexar" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /indexar"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "perguntar" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /perguntar"
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
  function_name = aws_lambda_function.rag.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
