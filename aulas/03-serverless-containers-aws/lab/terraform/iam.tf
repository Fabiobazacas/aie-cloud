# O Learner Lab NÃO permite criar roles novas (só service-linked roles) — o
# IAM já vem com LabRole (para anexar a serviços como Lambda) e
# LabInstanceProfile (para instâncias EC2/Elastic Beanstalk) pré-criados.
# Por isso aqui só LEMOS (data source) essas duas identidades — nunca criamos
# um aws_iam_role novo neste lab.
data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

data "aws_iam_instance_profile" "lab_instance_profile" {
  name = "LabInstanceProfile"
}
