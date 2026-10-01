variable "aws_region" {
  description = "Região AWS — o Learner Lab só libera us-east-1 ou us-west-2"
  type        = string
  default     = "us-east-1"

  validation {
    condition     = contains(["us-east-1", "us-west-2"], var.aws_region)
    error_message = "O AWS Academy Learner Lab só libera us-east-1 ou us-west-2."
  }
}

variable "gemini_api_key" {
  description = "Chave gratuita do Google Gemini do GRUPO (aistudio.google.com/apikey) — NUNCA commitar. Passe via -var=\"gemini_api_key=$GEMINI_API_KEY\"."
  type        = string
  sensitive   = true
}

variable "habilitar_rag" {
  description = "true = sobe RDS/pgvector + NAT Gateway + Exercícios 01 e 02 (demora ~15 min e é o que mais custa por hora). false = só Exercícios 03, 04, 05 e Desafio (deploy em ~2 min)."
  type        = bool
  default     = true
}

variable "hf_token" {
  description = "Token do HuggingFace do GRUPO (huggingface.co/settings/tokens, tipo Read, gratuito) — NUNCA commitar. Usado pelo Ex05 e pelo Desafio 3D: os Spaces rodam em GPU compartilhada (ZeroGPU) e, sem token, a cota diária anônima acaba em 1-2 chamadas."
  type        = string
  default     = ""
  sensitive   = true
}

variable "trellis_space" {
  description = "Space do HuggingFace com o modelo TRELLIS (Desafio 3D). O microsoft/TRELLIS original está em CONFIG_ERROR; este é um fork da comunidade com a mesma API."
  type        = string
  default     = "trellis-community/TRELLIS"
}

variable "hf_edit_space" {
  description = "Space do HuggingFace de edição de imagem (image-to-image) do Exercício 05. Precisa expor /infer(input_image, prompt, seed, randomize_seed, guidance_scale, steps)."
  type        = string
  default     = "black-forest-labs/FLUX.1-Kontext-Dev"
}

variable "provedores_imagem" {
  description = "Ordem dos provedores de image-to-image do Ex05: gemini (precisa de cota de imagem — o free tier não tem) e/ou hf (Space do Hugging Face)."
  type        = string
  default     = "gemini,hf"
}

variable "gemini_image_model" {
  description = "Modelo Gemini de geração/edição de imagem do Exercício 05 (usado só se 'gemini' estiver em provedores_imagem). Se der 404, liste os modelos da sua chave (ver guia-lab.md)."
  type        = string
  default     = "gemini-2.5-flash-image"
}
