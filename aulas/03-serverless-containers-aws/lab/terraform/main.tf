terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      # Fixado em 4.8.0: a partir da 4.9 o provider passou a chamar
      # GetBucketObjectLockConfiguration ao ler qualquer aws_s3_bucket, e a
      # LabRole do Academy nega essa API explicitamente — o apply quebra
      # mesmo sem usar Object Lock. Não subir essa versão sem testar antes.
      version = "= 4.8.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
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
}
