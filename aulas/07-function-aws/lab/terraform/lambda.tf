# As 6 Lambdas da aula. Cada uma é um zip com: o seu lambda_function.py, as
# suas dependências (requirements.txt) e as pastas compartilhadas shared/ e
# prompts/ — montado num build em /tmp.
#
# Dependências com extensão compilada (PyMuPDF, psycopg2) NÃO vêm no runtime
# padrão da Lambda (só o boto3 vem). Por isso baixamos wheels pré-compiladas
# para Linux/x86_64 (--platform manylinux2014_x86_64 --only-binary=:all:),
# mesmo rodando o apply no CloudShell — o resultado é sempre compatível.
#
# O build vai para /tmp, NUNCA para dentro do repo: o $HOME do CloudShell tem
# só ~1 GB de cota, e o pip usa um diretório de staging em /tmp antes de mover
# para o --target (em outro filesystem vira cópia: Errno 18 + cota estourada).
locals {
  # rag = true -> só é criada com habilitar_rag = true
  lambda_cfg_todas = {
    ex01_chunker  = { timeout = 300, memory = 1024, vpc = true, rag = true, disk = 512 }
    ex02_rag      = { timeout = 60, memory = 512, vpc = true, rag = true, disk = 512 }
    ex03_ner      = { timeout = 300, memory = 1024, vpc = false, rag = false, disk = 512 }
    ex04_speech   = { timeout = 120, memory = 512, vpc = false, rag = false, disk = 512 }
    ex05_marketing = { timeout = 300, memory = 512, vpc = false, rag = false, disk = 512 }
    desafio_3d    = { timeout = 900, memory = 1024, vpc = false, rag = false, disk = 1024 }
  }

  lambda_cfg = { for nome, cfg in local.lambda_cfg_todas : nome => cfg if var.habilitar_rag || !cfg.rag }

  env_base = {
    BUCKET             = local.bucket_name
    GEMINI_API_KEY     = var.gemini_api_key
    GEMINI_IMAGE_MODEL = var.gemini_image_model
  }

  # try(..., "") porque com habilitar_rag = false o RDS não existe.
  env_rag = {
    DB_HOST       = try(aws_db_instance.rag[0].address, "")
    DB_SECRET_ARN = try(aws_db_instance.rag[0].master_user_secret[0].secret_arn, "")
  }

  env_por_lambda = {
    ex01_chunker   = local.env_rag
    ex02_rag       = local.env_rag
    ex03_ner       = { DDB_ENTITIES_TABLE = aws_dynamodb_table.entities.name }
    ex04_speech    = { DDB_TRANSCRIPTIONS_TABLE = aws_dynamodb_table.transcriptions.name }
    ex05_marketing = {
      HF_TOKEN         = var.hf_token
      HF_EDIT_SPACE    = var.hf_edit_space
      IMAGE_PROVIDERS  = var.provedores_imagem
      HOME             = "/tmp"
      HF_HOME          = "/tmp/hf"
      GRADIO_TEMP_DIR  = "/tmp/gradio"
    }
    desafio_3d = {
      HF_TOKEN        = var.hf_token
      TRELLIS_SPACE   = var.trellis_space
      HOME            = "/tmp"
      HF_HOME         = "/tmp/hf"
      GRADIO_TEMP_DIR = "/tmp/gradio"
    }
  }

  # Hash do código compartilhado — mudou shared/ ou prompts/, todas as Lambdas
  # são reconstruídas.
  hash_compartilhado = sha1(join("", [
    for f in concat(sort(fileset("${path.module}/..", "shared/*.py")), sort(fileset("${path.module}/..", "prompts/*.md"))) :
    filesha1("${path.module}/../${f}")
  ]))
}

resource "null_resource" "lambda_build" {
  for_each = local.lambda_cfg

  triggers = {
    requirements  = filemd5("${path.module}/../lambda/${each.key}/requirements.txt")
    codigo        = filemd5("${path.module}/../lambda/${each.key}/lambda_function.py")
    compartilhado = local.hash_compartilhado
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      B="${local.build_dir}/${each.key}"
      REQ="${path.module}/../lambda/${each.key}/requirements.txt"
      rm -rf "$B"
      mkdir -p "$B"
      if grep -qE '^[^#[:space:]]' "$REQ"; then
        pip install \
          --platform manylinux2014_x86_64 \
          --implementation cp \
          --python-version 3.12 \
          --only-binary=:all: \
          --target "$B" \
          -r "$REQ" \
          -q
      fi
      cp "${path.module}/../lambda/${each.key}/lambda_function.py" "$B/"
      cp -r "${path.module}/../shared" "$B/shared"
      cp -r "${path.module}/../prompts" "$B/prompts"
      find "$B/shared" -name __pycache__ -prune -exec rm -rf {} +
    EOT
  }
}

data "archive_file" "lambda_zip" {
  for_each = local.lambda_cfg

  type        = "zip"
  source_dir  = "${local.build_dir}/${each.key}"
  output_path = "${local.build_dir}/${each.key}.zip"
  depends_on  = [null_resource.lambda_build]
}

resource "aws_lambda_function" "fn" {
  for_each = local.lambda_cfg

  function_name    = "aula2-${each.key}-${random_string.sufixo.result}"
  role             = data.aws_iam_role.lab_role.arn
  handler          = "lambda_function.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip[each.key].output_path
  source_code_hash = data.archive_file.lambda_zip[each.key].output_base64sha256
  timeout          = each.value.timeout
  memory_size      = each.value.memory

  ephemeral_storage {
    size = each.value.disk
  }

  # Só as Lambdas de RAG entram na VPC (para alcançar o RDS) — ver network.tf.
  dynamic "vpc_config" {
    for_each = each.value.vpc ? [1] : []
    content {
      subnet_ids         = [aws_subnet.lambda_privada[0].id]
      security_group_ids = [aws_security_group.lambda[0].id]
    }
  }

  environment {
    variables = merge(local.env_base, local.env_por_lambda[each.key])
  }

  tags = local.tags

  depends_on = [aws_route_table_association.lambda_privada]
}

# Invocação assíncrona (modo "async": true e S3 Event Notification) tenta 2
# vezes por padrão quando a função falha — o que dobraria chamadas pagas ao
# Gemini e reprocessaria o arquivo. Aqui: zero retries.
resource "aws_lambda_function_event_invoke_config" "sem_retry" {
  for_each = local.lambda_cfg

  function_name          = aws_lambda_function.fn[each.key].function_name
  maximum_retry_attempts = 0
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each = local.lambda_cfg

  name              = "/aws/lambda/${aws_lambda_function.fn[each.key].function_name}"
  retention_in_days = 7
  tags              = local.tags
}
