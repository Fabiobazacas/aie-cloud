# Bucket do CATÁLOGO da QC — criado NESTA aula (independente das demais).
# Lambda e Elastic Beanstalk leem o produtos.csv daqui via IAM Role (sem
# credenciais no código). Também guarda o pacote de deploy do Beanstalk
# (prefixo beanstalk/) para não precisar de um segundo bucket.
resource "aws_s3_bucket" "catalogo" {
  bucket = "qc-catalogo-${random_string.sufixo.result}"
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "catalogo" {
  bucket                  = aws_s3_bucket.catalogo.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Sobe o produtos.csv automaticamente no apply — sem passo de upload manual.
resource "aws_s3_object" "produtos" {
  bucket = aws_s3_bucket.catalogo.id
  key    = "catalogo/produtos.csv"
  source = "${path.module}/../data/produtos.csv"
  etag   = filemd5("${path.module}/../data/produtos.csv")
}
