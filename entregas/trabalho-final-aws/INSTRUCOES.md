# Trabalho Final — Quantum Commerce (trilha AWS)

**Vale:** 70% da nota total (os outros 30% vêm das duas entregas práticas da Aula 7 — ver [composição da nota](#composição-da-nota))
**Formato:** Entrega via ZIP no Portal FIAP — **sem apresentação oral**
**Prazo:** 1 semana após a Aula 6
**Rubrica:** [rubrica.md](rubrica.md), nesta mesma pasta

> **Esta pasta substitui `entregas/projeto-final/` para quem seguiu a trilha AWS.**
> O `entregas/projeto-final/INSTRUCOES.md` original e a `entregas/rubrica.md` descrevem uma arquitetura Azure (Cosmos DB, Azure SQL, AI Search, Azure ML Online Endpoint) que esta turma não construiu. O motivo e o mapeamento completo da divergência estão em [`entregas/DIVERGENCIA-TRILHA-AWS.md`](../DIVERGENCIA-TRILHA-AWS.md).

---

## Composição da nota

| Componente | Peso | O que é |
|---|---|---|
| Trabalho 1 — Aula 7 | 15% | Primeira entrega prática feita durante a Aula 7 (exercícios AWS/Gemini) |
| Trabalho 2 — Aula 7 | 15% | Segunda entrega prática feita durante a Aula 7 |
| **Trabalho Final (esta pasta)** | **70%** | Projeto integrado Quantum Commerce, versão AWS, formato leve |
| **Total** | **100%** | |

> Os critérios do Trabalho 1 e 2 estão na [rubrica.md](rubrica.md). Se a divisão real dos dois trabalhos da Aula 7 foi diferente da descrita ali, ajuste os critérios — o que importa é fechar 30% com o que já foi de fato entregue, sem reabrir trabalho para o aluno.

---

## Por que este trabalho é "light"

O desenho original do projeto final (Azure) pedia um ZIP com 9 artefatos obrigatórios e uma arquitetura completa provisionada via Terraform (banco relacional + NoSQL + busca vetorial + 5 rotas de API + endpoint de ML). Para a trilha AWS isso não se sustenta por dois motivos:

1. **As aulas 1, 2 e 5 nunca foram convertidas para AWS** — não existe uma base ensinada e testada em aula para esses serviços nesta trilha.
2. **O objetivo pedagógico deste momento do curso é raciocínio arquitetural, não operação de infraestrutura.** A Aula 7 já provou que o grupo sabe rodar Lambda + API Gateway + S3 + Gemini. O trabalho final não precisa reprovar isso — precisa testar se o grupo sabe **desenhar e justificar** uma arquitetura maior a partir disso.

Por isso, o trabalho final pede **um documento de arquitetura e decisão** (peso maior) + **uma prova de conceito pequena** (peso menor), em vez de um sistema inteiro funcionando.

---

## O que é

Consolidação do que o grupo aprendeu (principalmente na Aula 7) em um projeto coerente para a Quantum Commerce, demonstrando:

1. **Arquitetura AWS proposta** para os principais domínios da QC (catálogo, busca/RAG, extração de dados, atendimento, marketing)
2. **Decisões técnicas justificadas** (por que cada serviço, não só qual serviço)
3. **Uma prova de conceito funcionando** — pelo menos 1 das tools de referência, rodando de verdade
4. **Análise de custo** (estimativa + onde cortar)
5. **Reflexão estratégica curta** — próximos passos e lições aprendidas

---

## Conteúdo obrigatório do ZIP

Nome do arquivo: `trabalho-final-aws-grupo-NN.zip`

```
trabalho-final-aws-grupo-NN/
├── projeto.md              # ⭐ documento único: arquitetura + decisões + finops + reflexão
├── diagrama.png             # diagrama da arquitetura proposta
├── tools-spec.json          # ⭐ spec das 5 tools de referência (ver abaixo)
└── poc/                     # ⭐ prova de conceito — só 1 ou 2 tools implementadas
    ├── lambda_function.py   # (ou a pasta do seu código da Aula 7, reaproveitada)
    └── terraform/           # reaproveita o padrão já usado na Aula 7
```

**Tamanho do ZIP:** < 10 MB. **Não incluir:** `terraform.tfstate*`, `.env`, `__pycache__/`, imagens/áudios de exemplo grandes (reaproveite os da Aula 7 por referência, não precisa reempacotar).

**Como gerar o ZIP** (mesmo padrão das entregas anteriores):

```bash
cd ~/qc-grupo-NN
git archive --format=zip --prefix=trabalho-final-aws-grupo-NN/ \
  -o ~/trabalho-final-aws-grupo-NN.zip HEAD:trabalho-final-aws
```

---

## Detalhes de cada peça

### 1. `projeto.md` — documento único

Um arquivo markdown com estas seções (não precisa ser mais de 3-4 páginas no total):

#### Arquitetura proposta
Diagrama + uma tabela de serviços AWS por domínio, com justificativa curta:

| Domínio | Serviço AWS | Justificativa |
|---|---|---|
| Catálogo de produtos | | |
| Busca / perguntas de cliente (RAG) | | |
| Extração de dados de documentos | | |
| Atendimento (transcrição + avaliação) | | |
| Geração de campanha/imagem | | |
| Onde os dados vivem (S3 / RDS+pgvector / DynamoDB) | | |

Ferramentas aceitas pro diagrama: Excalidraw, draw.io, Mermaid, foto de quadro branco legível.

#### 3 decisões técnicas
Formato ADR curto (decisão → contexto → alternativas → trade-off). Exemplos de decisões que valem a pena documentar: *por que Lambda e não ECS/Fargate*, *por que RDS+pgvector e não um serviço de busca vetorial gerenciado*, *por que Gemini direto e não um catálogo de modelos gerenciado (Bedrock)* — esta última em particular conecta direto com o que a Aula 7 já discutiu sobre a conta do AWS Academy.

#### FinOps light
Uma tabela de estimativa mensal (pode ser calculada manualmente a partir dos preços unitários já vistos na Aula 7 — Lambda, NAT Gateway, RDS, DynamoDB) + 2 propostas de otimização, um parágrafo cada. Não é exigido export formal da AWS Pricing Calculator, mas é um diferencial se o grupo quiser fazer.

#### Reflexão estratégica (curta)
- Próximos 2 trimestres: o que a QC precisaria resolver primeiro e depois
- 3-5 linhas de lições aprendidas do módulo inteiro

### 2. `tools-spec.json` — as 5 tools de referência

A arquitetura da QC se apoia em 5 capacidades, mapeadas direto dos exercícios da Aula 7:

| Tool | Deriva de | O que faz |
|---|---|---|
| `buscar_produtos` | Aula 3 (Lambda + S3) | Busca no catálogo por categoria/nome |
| `responder_duvida` | Chunker + RAG | Responde pergunta do cliente citando a fonte (RAG sobre pgvector) |
| `extrair_dados_documento` | NER | Extrai dados estruturados de um documento (nota fiscal, cadastro) |
| `avaliar_atendimento` | Call Center Analytics | Transcreve e avalia uma ligação de atendimento |
| `gerar_campanha` | Campanha de Marketing | Gera texto + imagem de campanha a partir da foto de um produto |

Especifique as 5 no formato de function calling (nome, descrição que ensine o agente quando usar, schema de entrada, pelo menos 1 exemplo de uso cada) — **não precisa que as 5 estejam implementadas**, só bem especificadas.

### 3. `poc/` — prova de conceito

Escolha **pelo menos 1** (idealmente 2) das 5 tools acima e implemente de verdade, reaproveitando o código e o Terraform que o grupo já fez na Aula 7 — não é pra escrever do zero. Documente no `README.md` dentro de `poc/` como rodar.

**Critério de aceitação:** a tool escolhida responde a uma chamada real (`curl`) e isso está documentado (comando + saída, print ou texto colado).

---

## O que NÃO é mais exigido (em relação ao projeto final original)

- Terraform único provisionando toda a infraestrutura de uma vez
- As 5 tools implementadas e publicadas
- Endpoint de ML/recomendação publicado (vira só uma linha de design em `projeto.md`, se o grupo quiser mencionar)
- Managed Identity / IAM por tool — o LabRole compartilhado da Aula 7 é aceitável, com a ressalva já discutida em aula sobre revogação não ser por agente
- `distribuicao-do-trabalho.md` separado — vira um parágrafo dentro do `projeto.md`

---

## Perguntas frequentes

**Q: Precisamos rodar as 5 tools?**
A: Não. Pelo menos 1 rodando de verdade (2 é melhor), as outras 4 só especificadas em `tools-spec.json`.

**Q: Podemos reaproveitar o código da Aula 7 quase inteiro?**
A: Sim — é esperado. O trabalho final testa se vocês conseguem **encaixar** o que já fizeram numa arquitetura maior e justificá-la, não reescrever do zero.

**Q: E se o grupo quiser fazer mais do que o mínimo (ex: as 5 tools rodando)?**
A: Ótimo, vale como diferencial na nota de Arquitetura e Conexão com Agentes — mas não é exigido nem traz pontos extras automáticos além do que a rubrica já cobre.

**Q: O Terraform precisa rodar sem erro?**
A: Só o da(s) tool(s) que estiver em `poc/` — reaproveitado da Aula 7, já deve rodar.

**Q: Podemos usar repositório público?**
A: Não. Entrega via ZIP no Portal FIAP, mesma regra das entregas anteriores.

---

## Lembrete final

Entrega via **Portal FIAP**, um único membro do grupo faz o upload. Avaliação por esta rubrica + revisão humana, nota e comentários devolvidos no Portal.
