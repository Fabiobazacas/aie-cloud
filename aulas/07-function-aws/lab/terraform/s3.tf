# Bucket ÚNICO da aula — o equivalente ao Storage Account + containers do
# laboratório Azure. Os "containers" viram prefixos (pastas):
#
#   entradas:  documents/  audios/  images/  images-3d/
#   saídas:    chunks/  entities/  transcriptions/  campaigns/  models3d/  jobs/
#
# Igual às Aulas 3/4/5: NÃO usamos o recurso "aws_s3_bucket" — o Read dele
# dispara s3:GetBucketObjectLockConfiguration, que a LabRole nega
# explicitamente (bug antigo do provider, não é regressão de versão). O
# bucket é criado via AWS CLI num null_resource; só o que não dispara essa
# chamada extra (public access block, upload de objeto, notificação) usa
# recurso normal.
resource "null_resource" "bucket" {
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

resource "aws_s3_bucket_public_access_block" "bucket" {
  bucket                  = local.bucket_name
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  depends_on = [null_resource.bucket]
}

# Sobe os arquivos de exemplo (lab/data/documents, audios, images) no apply —
# sem passo de upload manual. A chave no S3 é o caminho relativo dentro de
# lab/data (ex.: documents/matricula.pdf).
resource "aws_s3_object" "entradas" {
  for_each = fileset("${path.module}/../data", "**")

  bucket = local.bucket_name
  key    = each.value
  source = "${path.module}/../data/${each.value}"
  etag   = filemd5("${path.module}/../data/${each.value}")

  depends_on = [null_resource.bucket]
}

# Event-driven do Desafio: todo upload em images-3d/ dispara a Lambda
# desafio_3d (o "Blob Trigger" do laboratório Azure). O destino (models3d/)
# fica FORA do prefixo filtrado, senão a Lambda dispararia a si mesma em loop.
resource "aws_s3_bucket_notification" "desafio_3d" {
  bucket = local.bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.fn["desafio_3d"].arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "images-3d/"
  }

  depends_on = [aws_lambda_permission.s3_desafio, null_resource.bucket]
}
