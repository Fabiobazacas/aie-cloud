# Bucket do CATÁLOGO da QC — criado NESTA aula (independente das demais).
# Lambda e Elastic Beanstalk leem o produtos.csv daqui via IAM Role (sem
# credenciais no código). Também guarda o pacote de deploy do Beanstalk
# (prefixo beanstalk/) para não precisar de um segundo bucket.
#
# NÃO usamos o recurso "aws_s3_bucket" aqui de propósito: o Read desse
# recurso dispara mais de 10 chamadas extras (versioning, lifecycle, cors,
# replication, OBJECT LOCK, etc.) pra popular atributos legados — e a
# LabRole do Academy tem deny explícito em s3:GetBucketObjectLockConfiguration.
# Isso quebra o apply mesmo sem Object Lock estar em uso, em QUALQUER versão
# do provider (bug antigo, não é regressão de versão — ver
# https://github.com/terraform-providers/terraform-provider-aws/issues/7550).
# Solução: criar o bucket via AWS CLI (que só chama CreateBucket, sem os
# reads extras) e referenciar o nome como string (local.bucket_name, já
# calculado em main.tf a partir do sufixo aleatório).
resource "null_resource" "catalogo_bucket" {
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

  # --force apaga os objetos antes do bucket — cobre o caso de o Terraform
  # não ter conseguido destruir aws_s3_object antes (ordem já garantida
  # pelos depends_on abaixo, isso aqui é só uma rede de segurança).
  provisioner "local-exec" {
    when    = destroy
    command = "aws s3 rb \"s3://${self.triggers.bucket_name}\" --force || true"
  }
}

resource "aws_s3_bucket_public_access_block" "catalogo" {
  bucket                  = local.bucket_name
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  depends_on = [null_resource.catalogo_bucket]
}

# Sobe o produtos.csv automaticamente no apply — sem passo de upload manual.
resource "aws_s3_object" "produtos" {
  bucket = local.bucket_name
  key    = "catalogo/produtos.csv"
  source = "${path.module}/../data/produtos.csv"
  etag   = filemd5("${path.module}/../data/produtos.csv")

  depends_on = [null_resource.catalogo_bucket]
}
