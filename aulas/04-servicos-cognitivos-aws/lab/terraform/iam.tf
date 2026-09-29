# O Learner Lab NÃO permite criar roles novas (só service-linked roles) — o
# IAM já vem com LabRole pré-criada. Por isso aqui só LEMOS (data source)
# essa identidade — nunca criamos um aws_iam_role novo neste lab.
data "aws_iam_role" "lab_role" {
  name = "LabRole"
}
