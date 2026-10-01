# Aula 7 (AWS) — Pipelines Cognitivos Serverless: do PDF ao Modelo 3D

> **Material adicional/suplementar**, adaptado para AWS a partir do laboratório
> "Serviços Cognitivos em Cloud" (Azure Functions + Azure OpenAI). Segue o
> mesmo padrão das aulas `*-aws` deste repositório: **Terraform no AWS Academy
> Learner Lab + Google Gemini** como modelo de IA. Combine com o professor
> se/como este material entra na avaliação.

## Objetivos de aprendizagem

Ao final deste material, você será capaz de:

- Construir **pipelines cognitivos serverless** (Lambda + API Gateway + S3) que leem arquivos de um bucket, chamam um LLM e gravam o resultado.
- Fazer **chunking semântico** via LLM, gerar **embeddings** e indexar num banco vetorial (**RDS PostgreSQL + pgvector**).
- Construir um endpoint de **RAG** com **busca híbrida** (vetorial + palavra-chave, fundidas por RRF).
- Extrair **entidades (NER)** de um documento escaneado e persistir em **DynamoDB**.
- **Transcrever áudio** e avaliar um atendimento com um LLM multimodal.
- Gerar uma **campanha de marketing** a partir da foto de um produto (visão + imagem generativa).
- Disparar processamento por **evento** (S3 Event Notification → Lambda) e lidar com tarefas longas com **modo assíncrono**.
- Reconhecer o que muda — e o que não muda — ao trocar de nuvem: a lógica dos pipelines é a mesma, só a infraestrutura por trás muda.

---

## Por que esta aula importa para um AI Engineer

Quase todo sistema de IA em produção é uma cadeia de etapas pequenas: ler um
arquivo, extrair texto, chamar um modelo, validar o JSON, persistir. Saber
montar essa cadeia sobre serviços gerenciados — sem servidor para cuidar — e
saber **onde ela quebra** (timeout de API, custo de rede, rate limit do
modelo) é o que separa uma demo de um serviço que a empresa consegue operar.

---

## O que muda de Azure para AWS

| Conceito | Azure (laboratório original) | AWS (este material) |
|----------|------------------------------|----------------------|
| Compute / HTTP triggers | Azure Functions (Python v2) | **Lambda** + **API Gateway HTTP API** |
| Armazenamento de arquivos | Blob Storage (containers) | **S3** (um bucket, containers viram prefixos) |
| LLM de chat / visão | Azure OpenAI GPT-4o | **Google Gemini** (`gemini-flash-lite-latest`) |
| Embeddings | `text-embedding-3-small` (1536 dim) | Gemini `gemini-embedding-001` (768 dim) |
| Busca vetorial | Azure AI Search | **RDS PostgreSQL + pgvector** (busca híbrida por RRF) |
| NoSQL | Cosmos DB | **DynamoDB** |
| Fala para texto | Azure Speech STT | **Gemini** com entrada de áudio |
| Imagem generativa (Ex05) | GPT-image-2 (image edits) | **Space do Hugging Face** (FLUX.1 Kontext, image-to-image) — ou o modelo de imagem do Gemini, se a chave tiver cota |
| 2D → 3D (Desafio) | TRELLIS via HuggingFace Spaces | TRELLIS via HuggingFace Spaces (`trellis-community/TRELLIS`) |
| Blob Trigger (Desafio) | Blob Trigger → Queue Trigger | **S3 Event Notification → Lambda** |
| Segredos / identidade | Chaves em `local.settings.json` | **LabRole** (sem credencial no código) + Secrets Manager |
| IaC | Bicep | **Terraform** |
| URL temporária de arquivo | SAS URL | **Presigned URL** |

A lógica de negócio (prompts, chunking, RAG, NER, avaliação de atendimento,
campanha) **não muda** — os arquivos em [lab/prompts/](lab/prompts/) são os
mesmos do laboratório original.

---

## ⚠️ Bedrock indisponível — use Gemini (free tier)

O Learner Lab desta disciplina **não libera o Amazon Bedrock** (nega por falta
de policy). Por isso os pipelines usam o **Google Gemini**: free tier sem
cartão de crédito, cobre texto, visão, áudio e embeddings. **Cada grupo cria a
própria chave** ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)) —
uma chave compartilhada pela turma inteira estoura o rate limit.

> **Exercício 05 e Desafio — Hugging Face Spaces.** O free tier do Gemini **não
> tem cota de geração de imagem** (todos os modelos de imagem respondem
> `429, limit: 0`). Por isso a edição de imagem do Ex05 (image-to-image) e a
> conversão 2D→3D do Desafio rodam em **Spaces do Hugging Face**, em GPU
> compartilhada (ZeroGPU). Cada grupo cria também um **token gratuito do
> Hugging Face** ([huggingface.co/settings/tokens](https://huggingface.co/settings/tokens),
> tipo Read): sem token a cota anônima acaba em 1–2 chamadas, e mesmo com token
> a conta gratuita rende só alguns minutos de GPU por dia (~1 min por imagem,
> ~2 min por modelo 3D). Se o grupo tiver uma chave do Gemini com faturamento
> ativado, o Ex05 usa o Gemini automaticamente.

---

## Material da aula

| Arquivo | Quando usar |
|---------|-------------|
| [lab/guia-lab.md](lab/guia-lab.md) | Passo a passo guiado em sala — provisionamento + 5 exercícios + desafio |
| [lab/terraform/](lab/terraform/) | IaC completo, um `terraform apply` só: S3 + 6 Lambdas + API Gateway + DynamoDB + (opcional) RDS/pgvector/NAT |
| [lab/lambda/](lab/lambda/) | Código de cada exercício: `ex01_chunker`, `ex02_rag`, `ex03_ner`, `ex04_speech`, `ex05_marketing`, `desafio_3d` |
| [lab/shared/](lab/shared/) | Módulos compartilhados: cliente Gemini, S3, pgvector, extração de PDF, roteador HTTP + modo assíncrono |
| [lab/prompts/](lab/prompts/) | Prompts de sistema (chunking, RAG, NER, avaliação de atendimento, campanha) |
| [lab/data/](lab/data/) | Arquivos de exemplo (matrícula escaneada, áudio, imagens de produto) — enviados ao S3 pelo Terraform |
| [exercicios.md](exercicios.md) | Após o lab — exercícios em 3 níveis (🟢/🟡/🔴) |

## Mapa dos exercícios

| Exercício | Endpoint | Serviços | Depende de |
|-----------|----------|----------|------------|
| **01 — Chunker** | `POST /process` | S3, Gemini, RDS/pgvector | — |
| **02 — RAG** | `POST /rag/query` | Gemini, RDS/pgvector | Ex01 |
| **03 — NER** | `POST /ner` | S3, Gemini, DynamoDB | — |
| **04 — Speech** | `POST /transcribe` | S3, Gemini (áudio), DynamoDB | — |
| **05 — Marketing** | `POST /campaign` | S3, Gemini (visão + imagem) | — |
| **Desafio — 2D→3D** | `POST /convert3d` ou upload em `images-3d/` | S3, HuggingFace (TRELLIS) | — |

## Pré-requisitos

- ✅ Sessão ativa no AWS Academy Learner Lab (usa o **AWS CloudShell**, sem instalar nada)
- ✅ Chave gratuita do Google Gemini (uma por grupo)
- ✅ Token gratuito do Hugging Face (`hf_token`, uma por grupo) para o Ex05 e o Desafio

> **Atenção ao tempo e ao custo:** com `habilitar_rag = true` (padrão) o RDS
> demora ~10–15 min e, junto com o NAT Gateway, é o que mais custa por hora.
> Se o grupo só vai fazer os Exercícios 03–05 e o Desafio, suba com
> `-var="habilitar_rag=false"` — deploy em ~2 min, sem RDS nem NAT.
> **Sempre encerre com `terraform destroy`.**
