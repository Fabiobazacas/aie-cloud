output "bucket_entrada" {
  description = "Bucket S3 de entrada (modo --nuvem do gatilho)"
  value       = local.bucket_name
}

output "sqs_queue_url" {
  description = "URL da fila SQS — usar em disparador.py --observar --nuvem --fila-url <valor>"
  value       = aws_sqs_queue.gatilho.id
}
