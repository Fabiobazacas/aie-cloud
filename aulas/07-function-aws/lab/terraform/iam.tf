# O Learner Lab NÃO permite criar roles novas (só service-linked roles) — o
# IAM já vem com a LabRole pré-criada. Por isso aqui só LEMOS (data source)
# essa identidade — nunca criamos um aws_iam_role novo neste lab. Todas as
# Lambdas usam a LabRole como execution role: é ela que dá acesso a S3,
# DynamoDB, Secrets Manager e CloudWatch Logs sem nenhuma credencial no código.
data "aws_iam_role" "lab_role" {
  name = "LabRole"
}
