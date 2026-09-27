variable "aws_region" {
  description = "Região AWS — o Learner Lab só libera us-east-1 ou us-west-2"
  type        = string
  default     = "us-east-1"

  validation {
    condition     = contains(["us-east-1", "us-west-2"], var.aws_region)
    error_message = "O AWS Academy Learner Lab só libera us-east-1 ou us-west-2."
  }
}
