# Rubrica — Trabalho Final AWS (Quantum Commerce)

Esta rubrica substitui, para a trilha AWS, a seção "Rubrica do Projeto Integrado Final" de `entregas/rubrica.md`. O motivo está em [`entregas/DIVERGENCIA-TRILHA-AWS.md`](../DIVERGENCIA-TRILHA-AWS.md).

## Composição da nota final (100 pts = 100%)

| Componente | Pontos | Peso |
|---|---|---|
| Trabalho 1 | 15 | 15% |
| Trabalho 2 | 15 | 15% |
| Trabalho Final (esta pasta) | 70 | 70% |
| **Total** | **100** | **100%** |

> Ajuste os critérios do Trabalho 1/2 abaixo se a divisão real dos dois trabalhos cobriu outros exercícios ou outro recorte — o objetivo é fechar os 30% com o que já foi entregue, não redefinir o que já foi feito.

---

## Parte 1 — Trabalhos práticos já entregues (30 pts)

Cada trabalho vale **15 pontos**.

### Critério 1 — Implementação funcional (8 pts)

| Pontos | Descrição |
|---|---|
| 7-8 | Exercício(s) rodando no CloudShell, com evidência (comando + saída) |
| 4-6 | Roda parcialmente ou com ajuda, pequenos erros não corrigidos |
| 1-3 | Tentativa registrada mas não funcional |
| 0 | Ausente |

### Critério 2 — Entendimento da arquitetura (5 pts)

| Pontos | Descrição |
|---|---|
| 5 | Grupo explica corretamente o papel de cada componente (Lambda, S3, Gemini, banco) e por que o fluxo é síncrono ou assíncrono |
| 3-4 | Explicação correta com lacunas pontuais |
| 1-2 | Explicação superficial ou decorada sem entendimento |
| 0 | Ausente |

### Critério 3 — Documentação da entrega (2 pts)

| Pontos | Descrição |
|---|---|
| 2 | Passos reproduzíveis, sem segredo hardcoded |
| 1 | Funciona mas documentação confusa ou incompleta |
| 0 | Sem documentação |

---

## Parte 2 — Trabalho Final (70 pts)

### Critério A — Arquitetura AWS proposta (25 pts)

Peso maior porque é aqui que mora o raciocínio arquitetural — o que este momento do curso realmente quer testar.

| Pontos | Descrição |
|---|---|
| 21-25 | Arquitetura coerente para todos os domínios da QC, escolhas de serviço bem fundamentadas, diagrama claro, conexões entre componentes explícitas |
| 14-20 | Arquitetura coerente com lacunas de justificativa em 1-2 domínios |
| 7-13 | Arquitetura incompleta ou com escolhas pouco justificadas |
| 0-6 | Arquitetura superficial ou desconectada do case QC |

### Critério B — As 5 tools funcionando (10 pts)

As 5 tools são reaproveitadas dos stacks da Aula 3 e dos trabalhos práticos (não é implementação nova), então o padrão é as 5 rodando. Uma tool que não rodou por limitação externa documentada (cota do Hugging Face, rate limit do Gemini) e tem a tentativa registrada **não é contada como ausente**.

| Pontos | Descrição |
|---|---|
| 9-10 | As 5 tools respondem a uma chamada real, com evidência (comando + saída) para cada uma |
| 6-8 | 4 de 5 tools funcionando com evidência; a que falta tem limitação documentada ou pequeno ajuste pendente |
| 3-5 | 2-3 de 5 tools funcionando, ou evidência incompleta nas demais |
| 0-2 | 0-1 tool funcionando, sem evidência de tentativa nas demais |

### Critério C — Análise de custo (FinOps essencial) (10 pts)

| Pontos | Descrição |
|---|---|
| 9-10 | Estimativa plausível por serviço, com pelo menos 2 propostas de otimização concretas |
| 6-8 | Estimativa presente, otimizações genéricas |
| 3-5 | Estimativa incompleta ou com números implausíveis |
| 0-2 | Sem análise de custo |

### Critério D — Conexão explícita com AI/Agentes (20 pts)

Segundo maior peso — é a outra metade do raciocínio que o trabalho quer testar: cada peça da arquitetura existe para alguma razão ligada ao agente, não só "porque dá pra fazer".

> **Isso é avaliado só pelo `tools-spec.json` e pelo texto de `projeto.md` — não exige Bedrock Agents, AgentCore ou qualquer orquestração de agente rodando de verdade.** Esta trilha não teve uma aula aprofundada sobre agentes em cloud nem acesso ao Bedrock, e o critério não pressupõe isso. O que se avalia é se o grupo sabe projetar um serviço AWS **como uma ferramenta que um agente (construído em outra disciplina do MBA) poderia chamar** — nome, descrição de quando usar, schema de entrada e um exemplo de pergunta que dispararia a tool. É raciocínio de design de API, não implementação de agente. "Tool" aqui é só uma API com uma descrição de quando usá-la em cima — ver a explicação completa em [INSTRUCOES.md](INSTRUCOES.md#2-tools-specjson--as-5-tools-de-referência).

| Pontos | Descrição |
|---|---|
| 17-20 | Cada uma das 5 tools tem descrição clara de quando o agente a usaria, com exemplo de conversa/consulta que a dispararia |
| 11-16 | Conexão presente mas genérica em algumas tools |
| 5-10 | Conexão fraca, tools parecem listadas sem propósito de agente |
| 0-4 | Sem conexão com o contexto agentic |

### Critério E — Documentação e clareza (5 pts)

| Pontos | Descrição |
|---|---|
| 5 | `projeto.md` claro, diagrama legível, instruções do `poc/` reproduzíveis |
| 3-4 | Presente com lacunas pontuais |
| 1-2 | Fragmentado — leitor externo precisa de esforço grande para entender |
| 0 | Sem documentação coerente |
