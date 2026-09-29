# Bucket de ENTRADA do Deva — o equivalente AWS do container Blob do Azure.
# Só existe pra quem for rodar o gatilho em modo `--nuvem` (opcional; o modo
# padrão do lab observa uma pasta local, custo zero). Subir um .json aqui
# dispara o evento S3 → SQS que gatilho/disparador.py --observar --nuvem consome.
#
# Igual às Aulas 3/4: NÃO usamos o recurso "aws_s3_bucket" — o Read dele
# dispara s3:GetBucketObjectLockConfiguration, que a LabRole nega
# explicitamente (bug antigo do provider, não é regressão de versão). O
# bucket é criado via AWS CLI num null_resource; só a config de notificação
# (que faz outra chamada, sem o Object Lock) usa um recurso Terraform normal.
resource "null_resource" "entrada_bucket" {
  triggers = {
    bucket_name = local.bucket_name
    region      = var.aws_region
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      if [ "${var.aws_region}" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "${local.bucket_name}" --region "${var.aws_region}"
      else
        aws s3api create-bucket --bucket "${local.bucket_name}" --region "${var.aws_region}" --create-bucket-configuration LocationConstraint="${var.aws_region}"
      fi
      aws s3api put-bucket-tagging --bucket "${local.bucket_name}" --tagging '${local.tags_json}'
    EOT
  }

  provisioner "local-exec" {
    when    = destroy
    command = "aws s3 rb \"s3://${self.triggers.bucket_name}\" --force || true"
  }
}

resource "aws_s3_bucket_public_access_block" "entrada" {
  bucket                  = local.bucket_name
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  depends_on = [null_resource.entrada_bucket]
}

resource "aws_s3_bucket_notification" "entrada_para_sqs" {
  bucket = local.bucket_name

  queue {
    queue_arn = aws_sqs_queue.gatilho.arn
    events    = ["s3:ObjectCreated:*"]
  }

  depends_on = [
    null_resource.entrada_bucket,
    aws_sqs_queue_policy.permite_s3,
  ]
}
