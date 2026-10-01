# DynamoDB substitui o Cosmos DB (NoSQL serverless, cobrança por requisição).
# Mapeamento: partition key do Cosmos -> hash key; "id" do documento -> range key.

resource "aws_dynamodb_table" "entities" {
  name         = "aula2-entities-${random_string.sufixo.result}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "documentName"
  range_key    = "id"

  attribute {
    name = "documentName"
    type = "S"
  }

  attribute {
    name = "id"
    type = "S"
  }

  tags = local.tags
}

resource "aws_dynamodb_table" "transcriptions" {
  name         = "aula2-transcriptions-${random_string.sufixo.result}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "audioFileName"
  range_key    = "id"

  attribute {
    name = "audioFileName"
    type = "S"
  }

  attribute {
    name = "id"
    type = "S"
  }

  tags = local.tags
}
