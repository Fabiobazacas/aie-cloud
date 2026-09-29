# Rede da aula 4 — a peça que NÃO existiria se estivéssemos usando Bedrock.
#
# A Lambda precisa estar numa VPC pra alcançar o RDS (que é privado,
# publicly_accessible = false — nunca exponha um banco). Mas uma Lambda
# dentro de uma VPC NÃO tem acesso à internet por padrão. Se fosse chamar o
# Bedrock, a solução mais barata seria um VPC Interface Endpoint (sem custo
# de NAT Gateway) — mas isso só funciona pra serviços da própria AWS. O
# Gemini é uma API externa (generativelanguage.googleapis.com), então essa
# opção não existe aqui: a Lambda precisa de um NAT Gateway de verdade pra
# alcançar a internet de dentro da VPC. Isso é um custo real (~US$0,045/h +
# por GB) que o desenho 100%-AWS evitaria — ver Exercício 3.1 do material.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Uma das subnets default (já roteia pra um Internet Gateway) hospeda o NAT
# Gateway — ele precisa ficar numa subnet PÚBLICA pra ter saída à internet.
data "aws_subnet" "publica_para_nat" {
  id = data.aws_subnets.default.ids[0]
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = local.tags
}

resource "aws_nat_gateway" "saida_gemini" {
  allocation_id = aws_eip.nat.id
  subnet_id     = data.aws_subnet.publica_para_nat.id
  tags          = local.tags
}

# Subnet nova, só pra Lambda — usa um bloco /24 bem afastado dos /20 que o
# AWS Academy já aloca por padrão pras subnets default (normalmente até 6,
# cobrindo só os primeiros ~96 endereços /24 do range /16). O offset é
# sorteado (random_integer.subnet_offset, em main.tf) em vez de fixo, pra não
# colidir com uma subnet órfã de um apply anterior que falhou antes de
# terminar (ver Troubleshooting no guia-lab.md).
resource "aws_subnet" "lambda_privada" {
  vpc_id            = data.aws_vpc.default.id
  cidr_block        = cidrsubnet(data.aws_vpc.default.cidr_block, 8, random_integer.subnet_offset.result)
  availability_zone = data.aws_subnet.publica_para_nat.availability_zone
  tags              = local.tags
}

resource "aws_route_table" "lambda_privada" {
  vpc_id = data.aws_vpc.default.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.saida_gemini.id
  }

  tags = local.tags
}

resource "aws_route_table_association" "lambda_privada" {
  subnet_id      = aws_subnet.lambda_privada.id
  route_table_id = aws_route_table.lambda_privada.id
}

resource "aws_security_group" "lambda" {
  name   = "qc-rag-lambda-${random_string.sufixo.result}"
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
  name   = "qc-rag-db-${random_string.sufixo.result}"
  vpc_id = data.aws_vpc.default.id

  # Só a Lambda desta aula acessa a porta do Postgres.
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  tags = local.tags
}
