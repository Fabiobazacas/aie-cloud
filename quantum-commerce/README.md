# Projeto Integrado — Case Quantum Commerce

A **Quantum Commerce** é o case integrador da disciplina **Cloud & Cognitive Environments**, parte do MBA AI Engineering & Multi-Agents da FIAP.

A contribuição da disciplina para o case é:

> **Selecionar os principais componentes de cloud da Quantum Commerce, apresentar as camadas e como elas se comunicam para suportar os agentes conversacionais (considerando bases vetoriais e APIs serverless). Gerar estimativa de custo via calculadora de cloud e apresentar em visão executiva.**

O briefing detalhado do case (negócio, personas, requisitos) será disponibilizado pela coordenação no início do módulo.

---

## Como o projeto evolui ao longo da disciplina

Cada aula contribui com um bloco do projeto integrado. Esses blocos são entregues como **ZIPs no Portal FIAP** (uma entrega por grupo por aula). Detalhes da política de entrega, rubrica e template em [entregas/](../entregas/).

| Aula | Contribuição para o projeto |
|------|------------------------------|
| 1 | Definir a arquitetura cloud de alto nível (diagrama) e provisionar o resource group base |
| 2 | Provisionar storage e bancos (catálogo, transações, clientes) |
| 3 | Implantar microserviços/funções do backend (Function HTTP, container) |
| 4 | Integrar capacidades cognitivas (busca por imagem, sentimento de reviews, voz) |
| 5 | Construir pipeline de MLOps para o modelo de recomendação |
| 6 | Análise FinOps + trabalho assistido no projeto integrado final (entrega ZIP 1 semana depois — **sem apresentação oral**) |

> **Trilha AWS desta turma:** as aulas 1, 2 e 5 acima descrevem o desenho original (Azure) e nunca ganharam um equivalente AWS — ver [`entregas/DIVERGENCIA-TRILHA-AWS.md`](../entregas/DIVERGENCIA-TRILHA-AWS.md). Na prática, quem seguiu AWS teve o trabalho prático real em dois trabalhos entregues em aula (exercícios de pipeline serverless + Gemini), que junto com o trabalho final substituem as entregas intermediárias — ver [Avaliação](#avaliação) abaixo.

---

## Estrutura desta pasta

- `arquitetura/` — Diagrama-alvo da arquitetura cloud (será disponibilizado)

---

## Avaliação

A nota da disciplina vem **inteiramente** deste projeto integrado em grupo. A composição depende da trilha seguida:

**Trilha Azure (desenho original):**

| Componente | Peso |
|------------|------|
| 5 entregas intermediárias (Aulas 1-5, 10% cada) | 50% |
| Projeto integrado final (entrega 1 semana após a Aula 6) | 50% |
| **Total** | **100%** |

Rubrica completa em [entregas/rubrica.md](../entregas/rubrica.md).

**Trilha AWS (esta turma):** como as entregas intermediárias não foram cobradas de forma consistente durante a transição Azure→AWS, a nota vem de:

| Componente | Peso |
|------------|------|
| Dois trabalhos práticos já entregues em aula | 30% |
| Trabalho Final AWS (entrega 1 semana após a Aula 6) | 70% |
| **Total** | **100%** |

Instruções e rubrica completas em [entregas/trabalho-final-aws/](../entregas/trabalho-final-aws/).

Não há prova individual em nenhuma das duas trilhas.

---

## Como o grupo se organiza

- Os grupos são formados **no início da Aula 1**.
- Cada grupo cria **um repositório privado** no GitHub para trabalhar (não fork do `aie-cloud`).
- Cada entrega vira um ZIP gerado via `git archive` desse repo privado.
- Os 3 níveis de exercícios (🟢/🟡/🔴) são **divisão de trabalho** dentro do grupo, com rodízio entre aulas (vale ponto da rubrica).

Tutorial completo em [pos-aula-git.md da Aula 1](../aulas/01-fundamentos-iac/pos-aula-git.md).
