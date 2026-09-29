# Bucket de DOCUMENTOS da aula 4 — guarda os PDFs de teste que a Lambda lê
# via LabRole (sem credencial no código).
#
# Igual às Aulas 3/5: NÃO usamos o recurso "aws_s3_bucket" — o Read dele
# dispara s3:GetBucketObjectLockConfiguration, que a LabRole nega
# explicitamente (bug antigo do provider, não é regressão de versão). O
# bucket é criado via AWS CLI num null_resource; só o que não dispara essa
# chamada extra (public access block, upload de objeto) usa recurso normal.
resource "null_resource" "docs_bucket" {
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

resource "aws_s3_bucket_public_access_block" "docs" {
  bucket                  = local.bucket_name
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  depends_on = [null_resource.docs_bucket]
}

# Sobe o PDF de teste automaticamente no apply — sem passo de upload manual
# (o mesmo padrão da Aula 3 com o produtos.csv).
resource "aws_s3_object" "catalogo_pdf" {
  bucket = local.bucket_name
  key    = "catalogo_qc.pdf"
  source = "${path.module}/../data/catalogo_qc.pdf"
  etag   = filemd5("${path.module}/../data/catalogo_qc.pdf")

  depends_on = [null_resource.docs_bucket]
}
