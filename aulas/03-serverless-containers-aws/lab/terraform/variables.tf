variable "aws_region" {
  description = "Região AWS — o Learner Lab só libera us-east-1 ou us-west-2"
  type        = string
  default     = "us-east-1"

  validation {
    condition     = contains(["us-east-1", "us-west-2"], var.aws_region)
    error_message = "O AWS Academy Learner Lab só libera us-east-1 ou us-west-2."
  }
}

variable "lambda_version" {
  description = "Código da Lambda a deployar: 'v1-mock' (Atividade 1) ou 'v2-s3' (Atividade 2)"
  type        = string
  default     = "v1-mock"

  validation {
    condition     = contains(["v1-mock", "v2-s3"], var.lambda_version)
    error_message = "lambda_version deve ser 'v1-mock' ou 'v2-s3'."
  }
}

variable "beanstalk_enabled" {
  description = "Quando true, provisiona o Elastic Beanstalk (Atividade 3). Deixe false até ter a imagem pública publicada (ver docker/README.md)."
  type        = bool
  default     = false
}

variable "container_image" {
  description = "Imagem pública (GHCR ou Docker Hub) que o Elastic Beanstalk vai rodar — ver docker/README.md (Passo A)"
  type        = string
  default     = "ghcr.io/elthonf/produtos-api-aws:v1"
}

variable "ec2_key_pair_name" {
  # vockey já existe por padrão em us-east-1. Em us-west-2 (ou outra conta),
  # crie antes com: aws ec2 create-key-pair --key-name vockey --region us-west-2
  # --query "KeyMaterial" --output text > vockey.pem
  description = "Key pair EC2 para o Elastic Beanstalk usar (padrão do Academy: 'vockey')"
  type        = string
  default     = "vockey"
}
