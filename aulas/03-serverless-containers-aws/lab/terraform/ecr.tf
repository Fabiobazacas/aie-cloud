# Repositório ECR pra imagem da Atividade 3. Criado desde a Phase 1 (mesmo
# com beanstalk_enabled=false) porque o aluno builda e publica a imagem
# ANTES de habilitar o Beanstalk — mesma ordem da versão Azure (ACR primeiro,
# depois o app que consome a imagem). O AWS CloudShell tem Docker desde
# jan/2024 em todas as regiões comerciais (inclusive us-east-1/us-west-2),
# então o build+push acontece direto no CloudShell, sem precisar de registry
# externo nem de máquina própria.
resource "aws_ecr_repository" "produtos_api" {
  name                 = "qc-produtos-api-${random_string.sufixo.result}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true # permite terraform destroy mesmo com imagens dentro

  tags = local.tags
}
