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

# Offset do bloco /24 da subnet dedicada da Lambda (ver network.tf). Sorteado
# em vez de fixo: numa conta que já teve uma subnet órfã de um apply anterior
# (ex.: um apply que falhou por espaço em disco antes de gravar o state — ver
# guia-lab.md) ou que é compartilhada por mais de um grupo, um valor fixo
# colide direto com o que já existe (InvalidSubnet.Conflict). Sorteando entre
# 100 e 250 ficamos bem longe das ~6 subnets /20 que o Academy já cria por
# padrão (endereços até ~172.31.95.x) e reduzimos a chance de colisão entre
# execuções diferentes pra 1 em ~150.
resource "random_integer" "subnet_offset" {
  min = 100
  max = 250
}

locals {
  tags = {
    aula         = "4"
    disciplina   = "cloud-cognitive"
    projeto      = "quantum-commerce"
    provisionado = "terraform"
    cloud        = "aws"
  }

  # Igual às Aulas 3/5: nome calculado localmente, não lido de um
  # aws_s3_bucket — ver s3.tf para o porquê.
  bucket_name = "qc-rag-docs-${random_string.sufixo.result}"
  tags_json   = jsonencode({ TagSet = [for k, v in local.tags : { Key = k, Value = v }] })
}
