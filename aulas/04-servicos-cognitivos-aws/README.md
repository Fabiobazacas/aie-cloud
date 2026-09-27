# Aula 4 (AWS) — RAG Pipeline: do PDF ao Endpoint

## Objetivos de aprendizagem

Ao final desta aula, você será capaz de:

- Transcrever um PDF (inclusive digitalizado/escaneado) usando um **LLM multimodal** via **Amazon Bedrock**, em vez de OCR tradicional.
- Gerar **embeddings** de texto com Bedrock (Titan Embeddings) e entender trade-offs de chunking.
- Provisionar e consultar um **banco vetorial** com **Amazon RDS PostgreSQL + pgvector**.
- Construir um **endpoint de RAG** (Retrieval-Augmented Generation) numa **Lambda** por trás de API Gateway: recebe uma pergunta, busca o contexto relevante no banco vetorial e usa um LLM pra responder com base nesse contexto.
- Entender as implicações de rodar Lambda dentro de uma VPC pra acessar RDS e Bedrock (endpoints, custo, latência).

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

## ⚠️ Pré-requisito crítico: confirme o acesso ao Bedrock ANTES de tudo

O **Amazon Bedrock não estava na lista original de serviços levantados** para este Learner Lab (a mesma usada nas aulas 1-3). Ele pode estar disponível, ou pode não estar — **confirme isso na primeira atividade da aula**, antes de montar qualquer coisa em cima dele. Ver [exercicios.md](exercicios.md), Atividade 0.

Se o Bedrock **não** estiver disponível na sua conta, o professor vai indicar a alternativa (API externa com chave própria) — a arquitetura do pipeline (ingestão → chunking → embeddings → pgvector → RAG) não muda, só troca de onde vem o LLM.

---

## Material da aula

| Arquivo | Quando usar |
|---------|-------------|
| [exercicios.md](exercicios.md) | Exercício único em 3 níveis — pipeline de RAG completo, do PDF ao endpoint |

## Entrega de grupo

Esta aula gera a **4ª entrega de grupo** (10% da nota): instruções em [entregas/entrega-04/](../../entregas/entrega-04/). Rubrica em [entregas/rubrica.md](../../entregas/rubrica.md).

---

## Pré-requisitos

- ✅ Sessão ativa no AWS Academy Learner Lab
- ✅ Acesso a modelos no Amazon Bedrock **confirmado** (ver Atividade 0 do exercício)
- ✅ Nenhuma dependência das aulas anteriores — esta aula é autossuficiente (cria seu próprio S3, RDS e Lambda)

> **Atenção ao tempo:** RDS demora ~10-15 min pra ficar disponível depois do `terraform apply`. Comece por aí antes de fazer qualquer outra coisa na sessão.
