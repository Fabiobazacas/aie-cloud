terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# O Learner Lab só libera us-east-1 e us-west-2 — qualquer outra região dá
# erro de acesso. As credenciais vêm do painel "AWS Details" do Vocareum
# (Access Key + Secret Key + SESSION TOKEN — os 3, não só os 2 primeiros).
# Ver guia-lab.md, seção Preparação, para como exportá-las.
provider "aws" {
  region = var.aws_region
}

resource "random_string" "sufixo" {
  length  = 6
  upper   = false
  special = false
}

locals {
  tags = {
    aula         = "3"
    disciplina   = "cloud-cognitive"
    projeto      = "quantum-commerce"
    provisionado = "terraform"
    cloud        = "aws"
  }

  # Nome calculado localmente (não é um atributo lido da AWS) — usado direto
  # como string em todo lugar que precisaria de aws_s3_bucket.catalogo.id/
  # .bucket. Ver s3.tf para o porquê do bucket não ser gerenciado como
  # aws_s3_bucket normal.
  bucket_name = "qc-catalogo-${random_string.sufixo.result}"

  # JSON pronto para --tagging do "aws s3api put-bucket-tagging" (ver s3.tf).
  # Calculado aqui, numa única linha de referência, pra não misturar chaves
  # multilinha dentro do heredoc do local-exec (isso já confundiu o
  # `terraform fmt` uma vez).
  tags_json = jsonencode({ TagSet = [for k, v in local.tags : { Key = k, Value = v }] })
}
