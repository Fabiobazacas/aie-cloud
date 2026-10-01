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
provider "aws" {
  region = var.aws_region
}

resource "random_string" "sufixo" {
  length  = 6
  upper   = false
  special = false
}

# Offset do bloco /24 da subnet dedicada das Lambdas de RAG (ver network.tf).
# Sorteado em vez de fixo para não colidir com subnets órfãs de um apply
# anterior que falhou, nem com outros grupos na mesma conta.
resource "random_integer" "subnet_offset" {
  min = 100
  max = 250
}

data "aws_caller_identity" "current" {}

locals {
  tags = {
    aula         = "7-function-aws"
    disciplina   = "cloud-cognitive"
    provisionado = "terraform"
    cloud        = "aws"
  }

  # Nome calculado localmente, não lido de um aws_s3_bucket — ver s3.tf.
  bucket_name = "aula2-cognitivo-${random_string.sufixo.result}"
  tags_json   = jsonencode({ TagSet = [for k, v in local.tags : { Key = k, Value = v }] })

  # Pasta temporária de build das Lambdas (nunca dentro do repo — ver lambda.tf).
  build_dir = "/tmp/aula2-build-${random_string.sufixo.result}"
}
