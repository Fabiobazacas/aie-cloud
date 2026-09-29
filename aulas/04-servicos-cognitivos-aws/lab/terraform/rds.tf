# O banco vetorial da aula: RDS PostgreSQL + extensão pgvector.
#
# pgvector NÃO é habilitado pelo Terraform — é uma extensão do PostgreSQL, e
# só pode ser criada via SQL depois que a instância já está de pé (ver
# scripts/criar_tabela.py). Terraform provisiona infraestrutura; SQL
# configura o banco por dentro.
resource "aws_db_subnet_group" "rag" {
  name       = "qc-rag-db-${random_string.sufixo.result}"
  subnet_ids = data.aws_subnets.default.ids # RDS exige >=2 AZs no subnet group
  tags       = local.tags
}

resource "aws_db_instance" "rag" {
  identifier     = "qc-rag-db-${random_string.sufixo.result}"
  engine         = "postgres"
  engine_version = "16.4"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  db_name           = "ragdb"
  username          = "ragadmin"

  # Senha gerada e guardada automaticamente no Secrets Manager — sem senha
  # hardcoded, sem nós escolhendo/copiando nada manualmente.
  manage_master_user_password = true

  publicly_accessible = false
  skip_final_snapshot = true

  db_subnet_group_name   = aws_db_subnet_group.rag.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  tags = local.tags
}
