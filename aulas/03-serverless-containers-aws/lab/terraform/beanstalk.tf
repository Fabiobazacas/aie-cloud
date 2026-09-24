# Elastic Beanstalk, plataforma Docker — NÃO existe ECS/Fargate/EKS/App Runner
# no Learner Lab (nem em nenhum outro Learner Lab verificado). Elastic
# Beanstalk com Docker de container único é o mais próximo disso no Academy
# (mais parecido com ACI/App Service do que com um orquestrador completo).
#
# A imagem vem do ECR desta MESMA conta (ver ecr.tf) — o aluno builda e dá
# push direto no AWS CloudShell (que tem Docker desde jan/2024) antes de
# rodar este apply com beanstalk_enabled=true. Ver docker/README.md.
data "aws_elastic_beanstalk_solution_stack" "docker" {
  most_recent = true
  name_regex  = "running Docker$"
}

resource "aws_elastic_beanstalk_application" "qc" {
  name = "qc-catalogo-${random_string.sufixo.result}"
  tags = local.tags
}

# Dockerrun.aws.json zipado na hora — é só isso que o Beanstalk precisa
# quando a imagem já existe publicada (não builda nada, só faz "docker run").
data "archive_file" "beanstalk_bundle" {
  count       = var.beanstalk_enabled ? 1 : 0
  type        = "zip"
  output_path = "${path.module}/.build/beanstalk-app.zip"

  source {
    filename = "Dockerrun.aws.json"
    content = jsonencode({
      AWSEBDockerrunVersion = "1"
      Image = {
        Name   = "${aws_ecr_repository.produtos_api.repository_url}:v1"
        Update = "true"
      }
      Ports = [
        { ContainerPort = "8080" }
      ]
    })
  }
}

resource "aws_s3_object" "beanstalk_bundle" {
  count  = var.beanstalk_enabled ? 1 : 0
  bucket = local.bucket_name
  key    = "beanstalk/app-${random_string.sufixo.result}.zip"
  source = data.archive_file.beanstalk_bundle[0].output_path
  etag   = data.archive_file.beanstalk_bundle[0].output_md5

  depends_on = [null_resource.catalogo_bucket]
}

resource "aws_elastic_beanstalk_application_version" "qc" {
  count       = var.beanstalk_enabled ? 1 : 0
  name        = "v-${random_string.sufixo.result}"
  application = aws_elastic_beanstalk_application.qc.name
  bucket      = local.bucket_name
  key         = aws_s3_object.beanstalk_bundle[0].key
}

resource "aws_elastic_beanstalk_environment" "qc" {
  count               = var.beanstalk_enabled ? 1 : 0
  name                = "qc-env-${random_string.sufixo.result}"
  application         = aws_elastic_beanstalk_application.qc.name
  solution_stack_name = data.aws_elastic_beanstalk_solution_stack.docker.name
  version_label       = aws_elastic_beanstalk_application_version.qc[0].name
  tags                = local.tags

  # Configuração exigida pelo próprio Learner Lab para qualquer app no
  # Elastic Beanstalk (ver tabela de recursos): Service role = LabRole,
  # EC2 key pair = vockey, IAM instance profile = LabInstanceProfile.
  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "ServiceRole"
    value     = data.aws_iam_role.lab_role.name
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = data.aws_iam_instance_profile.lab_instance_profile.name
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "EC2KeyName"
    value     = var.ec2_key_pair_name
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "InstanceType"
    value     = "t3.micro"
  }

  # Réplica única, sem load balancer — mesma limitação didática do ACI
  # (ver exercício 2.3/discussão de escala no guia).
  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "EnvironmentType"
    value     = "SingleInstance"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "S3_BUCKET_CATALOGO"
    value     = local.bucket_name
  }
}
