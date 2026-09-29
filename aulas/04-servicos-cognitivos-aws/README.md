# Aula 4 (AWS) — RAG Pipeline: do PDF ao Endpoint

## Objetivos de aprendizagem

Ao final desta aula, você será capaz de:

- Transcrever um PDF (inclusive digitalizado/escaneado) usando um **LLM multimodal** (Google Gemini), em vez de OCR tradicional.
- Gerar **embeddings** de texto (Gemini `gemini-embedding-001`) e entender trade-offs de chunking.
- Provisionar e consultar um **banco vetorial** com **Amazon RDS PostgreSQL + pgvector**.
- Construir um **endpoint de RAG** (Retrieval-Augmented Generation) numa **Lambda** por trás de API Gateway: recebe uma pergunta, busca o contexto relevante no banco vetorial e usa um LLM pra responder com base nesse contexto.
- Entender as implicações de rodar Lambda dentro de uma VPC pra acessar RDS **e uma API externa** (endpoints AWS vs. NAT Gateway, custo, latência).

---

## Por que esta aula importa para um AI Engineer

RAG é o padrão mais usado hoje pra dar **conhecimento próprio** a um agente sem precisar treinar/fine-tunar modelo nenhum. Entender o pipeline completo — ingestão, chunking, embeddings, busca vetorial, geração aumentada — é pré-requisito pra qualquer sistema de agentes que precise responder com base em documentos da empresa (contratos, catálogos, políticas, manuais).

---

## Conexão com o Quantum Commerce

Esta aula constrói a **base de conhecimento** que os agentes da QC vão consultar:

| Componente | Capacidade |
|------------|------------|
| Ingestão (PDF → texto) | Transcreve catálogos, políticas de troca, manuais de produto em PDF |
| Embeddings + pgvector | Torna esse conteúdo pesquisável por similaridade semântica |
| `/perguntar` (Lambda + RAG) | Tool que um agente da QC chama pra responder perguntas com base nos documentos reais da empresa — não só no que o modelo "sabe" de treino |

---

## ⚠️ Bedrock confirmado indisponível — use Gemini (free tier)

**Já confirmamos, numa sessão real deste Learner Lab, que o Amazon Bedrock
não é liberado** (`aws bedrock list-foundation-models` nega por falta de
policy, não por modelo desabilitado). Por isso este pipeline usa **Google
Gemini** como provedor padrão — free tier sem cartão de crédito, cobre
visão, texto e embeddings num único lugar. Cada grupo cria sua própria
chave gratuita antes de começar — ver [exercicios.md](exercicios.md),
Atividade 0.

Se a sua conta do Academy for uma exceção e liberar Bedrock de verdade, a
arquitetura do pipeline (ingestão → chunking → embeddings → pgvector → RAG)
não muda — só troca de onde vem o LLM (ver notas em cada exercício).

---

## Material da aula

| Arquivo | Quando usar |
|---------|-------------|
| [lab/guia-lab.md](lab/guia-lab.md) | Passo a passo guiado em sala — LAB 1 a 4, do provisionamento ao endpoint de RAG |
| [lab/terraform/](lab/terraform/) | Código IaC completo e pronto pra `terraform apply`: S3 + RDS/pgvector + rede (NAT Gateway) + Lambda + API Gateway |
| [lab/lambda/lambda_function.py](lab/lambda/lambda_function.py) | As 6 rotas do pipeline: `/health`, `/setup-db`, `/status`, `/transcrever`, `/indexar`, `/perguntar` |
| [lab/scripts/](lab/scripts/) | `criar_tabela.py` (com a falha de segurança proposital) e `transcrever_pdf.py` (versão local pra explorar antes de testar o endpoint) |
| [lab/data/catalogo_qc.pdf](lab/data/catalogo_qc.pdf) | PDF de teste (política de troca fictícia da QC) já usado pelo Terraform |
| [exercicios.md](exercicios.md) | Após o lab — exercício em 3 níveis, construindo sobre o lab guiado |

## Entrega de grupo

Esta aula gera a **4ª entrega de grupo** (10% da nota): instruções em [entregas/entrega-04/](../../entregas/entrega-04/). Rubrica em [entregas/rubrica.md](../../entregas/rubrica.md).

---

## Pré-requisitos

- ✅ Sessão ativa no AWS Academy Learner Lab
- ✅ Chave gratuita do Google Gemini criada (ver Atividade 0 do exercício — uma por grupo)
- ✅ Nenhuma dependência das aulas anteriores — esta aula é autossuficiente (cria seu próprio S3, RDS e Lambda)

> **Atenção ao tempo:** RDS demora ~10-15 min pra ficar disponível depois do `terraform apply`. Comece por aí antes de fazer qualquer outra coisa na sessão.
