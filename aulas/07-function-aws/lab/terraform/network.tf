# Rede dos Exercícios 01 e 02 (só existe com habilitar_rag = true).
#
# As Lambdas de RAG precisam estar numa VPC para alcançar o RDS (privado,
# publicly_accessible = false — nunca exponha um banco). Mas uma Lambda dentro
# de uma VPC NÃO tem acesso à internet por padrão, e o Gemini é uma API
# EXTERNA (generativelanguage.googleapis.com) — não existe VPC Endpoint para
# ela. Solução: NAT Gateway (~US$0,045/h + por GB). Esse é um custo real que o
# desenho 100%-AWS (Bedrock via VPC Endpoint) evitaria.
#
# As Lambdas dos Exercícios 03, 04, 05 e Desafio NÃO usam o RDS, então ficam
# FORA da VPC: têm internet direta, sem NAT. Compare os dois desenhos no
# Exercício 3.3 do material.
data "aws_vpc" "default" {
  default = true
}

# "default-for-az" é essencial: sem esse filtro, um apply POSTERIOR faz este
# data source se auto-incluir a nossa subnet nova (mesma VPC), e o NAT Gateway
# pode cair dentro da subnet PRIVADA — sem rota para um Internet Gateway,
# virando um buraco negro de rede. "default-for-az = true" restringe às
# subnets que a AWS criou junto com a VPC default.
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "aws_subnet" "publica_para_nat" {
  id = data.aws_subnets.default.ids[0]
}

resource "aws_eip" "nat" {
  count  = var.habilitar_rag ? 1 : 0
  domain = "vpc"
  tags   = local.tags
}

resource "aws_nat_gateway" "saida_gemini" {
  count         = var.habilitar_rag ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = data.aws_subnet.publica_para_nat.id
  tags          = local.tags
}

# Subnet nova, só para as Lambdas de RAG — bloco /24 sorteado, longe das /20
# que o Academy já aloca por padrão nas subnets default.
resource "aws_subnet" "lambda_privada" {
  count             = var.habilitar_rag ? 1 : 0
  vpc_id            = data.aws_vpc.default.id
  cidr_block        = cidrsubnet(data.aws_vpc.default.cidr_block, 8, random_integer.subnet_offset.result)
  availability_zone = data.aws_subnet.publica_para_nat.availability_zone
  tags              = local.tags
}

resource "aws_route_table" "lambda_privada" {
  count  = var.habilitar_rag ? 1 : 0
  vpc_id = data.aws_vpc.default.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.saida_gemini[0].id
  }

  tags = local.tags
}

resource "aws_route_table_association" "lambda_privada" {
  count          = var.habilitar_rag ? 1 : 0
  subnet_id      = aws_subnet.lambda_privada[0].id
  route_table_id = aws_route_table.lambda_privada[0].id
}

resource "aws_security_group" "lambda" {
  count  = var.habilitar_rag ? 1 : 0
  name   = "aula2-lambda-${random_string.sufixo.result}"
  vpc_id = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

resource "aws_security_group" "rds" {
  count  = var.habilitar_rag ? 1 : 0
  name   = "aula2-db-${random_string.sufixo.result}"
  vpc_id = data.aws_vpc.default.id

  # Só as Lambdas desta aula acessam a porta do Postgres.
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda[0].id]
  }

  tags = local.tags
}
