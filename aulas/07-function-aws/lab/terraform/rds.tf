# O banco vetorial dos Exercícios 01/02: RDS PostgreSQL + extensão pgvector
# (substitui o Azure AI Search). Só existe com habilitar_rag = true.
#
# pgvector NÃO é habilitado pelo Terraform — é uma extensão do PostgreSQL e
# só pode ser criada via SQL depois que a instância está de pé. Quem faz isso
# é a própria Lambda, na primeira chamada (shared/db.py -> garantir_schema).
# Terraform provisiona infraestrutura; SQL configura o banco por dentro.
resource "aws_db_subnet_group" "rag" {
  count      = var.habilitar_rag ? 1 : 0
  name       = "aula2-db-${random_string.sufixo.result}"
  subnet_ids = data.aws_subnets.default.ids # RDS exige >= 2 AZs no subnet group
  tags       = local.tags
}

resource "aws_db_instance" "rag" {
  count      = var.habilitar_rag ? 1 : 0
  identifier = "aula2-db-${random_string.sufixo.result}"
  engine     = "postgres"
  # Só o major version: a AWS aposenta minors periodicamente, e fixar um minor
  # exato quebra o lab no semestre seguinte.
  engine_version             = "16"
  auto_minor_version_upgrade = true
  instance_class             = "db.t3.micro"

  allocated_storage = 20
  db_name           = "ragdb"
  username          = "ragadmin"

  # Senha gerada e guardada no Secrets Manager — sem senha hardcoded.
  manage_master_user_password = true

  publicly_accessible = false
  skip_final_snapshot = true

  db_subnet_group_name   = aws_db_subnet_group.rag[0].name
  vpc_security_group_ids = [aws_security_group.rds[0].id]

  tags = local.tags
}
