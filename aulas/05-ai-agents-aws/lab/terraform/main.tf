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

locals {
  tags = {
    aula         = "5-ai-agents"
    disciplina   = "cloud-cognitive"
    projeto      = "deva-continuo"
    provisionado = "terraform"
    cloud        = "aws"
  }

  # Igual ao padrão das Aulas 3/4: nome calculado localmente, não lido de um
  # aws_s3_bucket — ver s3.tf para o porquê.
  bucket_name = "deva-entrada-${random_string.sufixo.result}"
  tags_json   = jsonencode({ TagSet = [for k, v in local.tags : { Key = k, Value = v }] })
}
