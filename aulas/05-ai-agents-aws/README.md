# Aula 5 (AWS) — AI Agents com Continuidade: o Deva Contínuo

> **Material adicional/suplementar**, adaptado para AWS a partir do deck "Criando
> Agentes com Azure Foundry AI" (consolidação da disciplina Cloud & Cognitive
> Environments). **Não substitui** a Aula 5 oficial deste repositório
> ([../05-mlops/](../05-mlops/), com entrega própria em
> [entregas/entrega-05/](../../entregas/entrega-05/)) — os dois materiais
> cobrem temas diferentes e coexistem sob o mesmo número por causa de como o
> conteúdo original está organizado. Combine com o professor se/como este
> material entra na avaliação.

## Objetivos de aprendizagem

Ao final deste material, você será capaz de:

- Diferenciar os 5 "degraus da continuidade" de um agente: sessão com
  contexto → memória entre sessões → iniciativa (gatilho por evento) → fila
  de exceções.
- Implementar **memória revisável**: o agente propõe, só um humano aprova —
  e a linha aprovada carrega sempre o nome de quem assinou, nunca do agente.
- Implementar uma **fila de exceções com transição proibida em código**
  (não em prompt): o agente não pode liberar sua própria exceção.
- Restringir o que um agente **enxerga** via um subconjunto do OpenAPI da
  API (5 de 14 operações) — a mesma fronteira reforçada de novo no lado da
  API, via header `X-Auditor`.
- Reconhecer e bloquear uma **tentativa de prompt injection** vinda de texto
  processado automaticamente pelo agente, sem bloquear o mesmo pedido
  quando vem de um humano de verdade.
- Trocar o "gatilho por evento no Blob + Event Grid + Logic App" do Azure
  pelo equivalente AWS: **S3 Event Notification → SQS**.

---

## Por que esta aula importa para um AI Engineer

Um agente que só responde não é o problema difícil — o problema difícil é um
agente que **continua**: que lembra entre execuções, que começa sozinho
quando um evento acontece, e que sabe quando **não** deve decidir sozinho.
Esses três comportamentos (memória, iniciativa, fronteira) são exatamente o
que separa uma demonstração de um sistema auditável em produção — e são
independentes de qual nuvem ou qual modelo está por trás.

---

## Conexão com o Quantum Commerce

O "Deva Contínuo" processa notas fiscais de despesas, propõe regras de
categorização quando encontra um caso novo, e só aprende de verdade quando um
humano assina a proposta. É o mesmo padrão que qualquer agente contínuo da QC
vai precisar — atendimento que aprende exceções de política, um agente de
reconciliação financeira, etc.

---

## O que muda de Azure para AWS

| Conceito | Azure (deck original) | AWS (este material) |
|----------|------------------------|----------------------|
| Gatilho por evento | Blob Storage + Event Grid → Logic App | S3 + S3 Event Notification → SQS |
| Modelo do agente | Azure AI Foundry Agent Service (modelo por trás) | Amazon Bedrock (`anthropic.claude-3-haiku-20240307-v1:0`), com fallback `--mock` local |
| Memória revisável | `MEMORY.md`/`MEMORIA-PENDENTE.md` em Storage Account | Os mesmos dois arquivos — local por padrão, ou S3 (`ARMAZENAMENTO=s3`) |
| Custo | "Local: US$ 0,00. Na Azure: menos de US$ 1,00 por aluno" | Local: US$ 0,00. Camada opcional em AWS (S3+SQS): centavos |

A lógica de negócio (memória, fila, fronteira, OpenAPI restrito) **não
muda** — só a infraestrutura por trás do gatilho e do modelo.

---

## Material da aula

| Arquivo | Quando usar |
|---------|-------------|
| [lab/guia-lab.md](lab/guia-lab.md) | Passo a passo guiado — 7 atividades + 1 opcional em AWS |
| [lab/api/](lab/api/) | FastAPI: 14 operações, memória revisável, fila de exceções |
| [lab/web/aplicacao.py](lab/web/aplicacao.py) | Painel Streamlit — 4 abas |
| [lab/gatilho/](lab/gatilho/) | `disparador.py` (semear/observar) e `ciclo_do_agente.py` (uma volta) |
| [lab/agente/](lab/agente/) | `openapi-agente.json` (5 de 14 operações) + cliente Bedrock (com `--mock`) |
| [lab/terraform/](lab/terraform/) | Camada **opcional**: bucket S3 + fila SQS do gatilho por evento |
| [exercicios.md](exercicios.md) | Após o lab — 4 exercícios em 3 níveis (🟢/🟡/🔴) |

## Pré-requisitos

- ✅ Python 3.11+ local (o lab inteiro roda sem nenhuma conta de nuvem)
- ✅ Opcional: sessão ativa no AWS Academy Learner Lab, só para a Atividade
  extra (gatilho via S3+SQS) ou para rodar o agente com Bedrock de verdade
  (`--mock=false`)

> **Aula independente.** Não depende de nenhuma aula anterior deste
> repositório — nem mesmo do bucket S3 criado nas Aulas 3/4.
