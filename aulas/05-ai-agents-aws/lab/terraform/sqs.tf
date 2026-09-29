# Fila SQS que recebe o evento S3:ObjectCreated do bucket de entrada — o
# "Event Grid → Logic App" da versão Azure vira "S3 Event Notification → SQS"
# aqui. disparador.py --observar --nuvem consome essa fila via boto3.
resource "aws_sqs_queue" "gatilho" {
  name                       = "deva-gatilho-${random_string.sufixo.result}"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 3600
  tags                       = local.tags
}

# Sem essa policy, o S3 não tem permissão de publicar na fila — diferente do
# LabRole (que autoriza uma IDENTIDADE), isso é uma resource policy no
# próprio SQS, então não esbarra na restrição de "não pode criar roles novas".
resource "aws_sqs_queue_policy" "permite_s3" {
  queue_url = aws_sqs_queue.gatilho.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.gatilho.arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = "arn:aws:s3:::${local.bucket_name}" }
      }
    }]
  })
}
