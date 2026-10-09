# Trabalho Final — Quantum Commerce (trilha AWS)

**Vale:** 70% da nota total (os outros 30% vêm dos dois trabalhos práticos já entregues em aula — ver [composição da nota](#composição-da-nota))
**Formato:** Entrega via ZIP no Portal FIAP — **sem apresentação oral**
**Prazo:** 1 semana após a Aula 6
**Rubrica:** [rubrica.md](rubrica.md), nesta mesma pasta

> **Esta pasta substitui `entregas/projeto-final/` para quem seguiu a trilha AWS.**
> O `entregas/projeto-final/INSTRUCOES.md` original e a `entregas/rubrica.md` descrevem uma arquitetura Azure (Cosmos DB, Azure SQL, AI Search, Azure ML Online Endpoint) que esta turma não construiu. O motivo e o mapeamento completo da divergência estão em [`entregas/DIVERGENCIA-TRILHA-AWS.md`](../DIVERGENCIA-TRILHA-AWS.md).

---

## Composição da nota

| Componente | Peso | O que é |
|---|---|---|
| Trabalho 1 | 15% | Primeira entrega prática já feita em aula (exercícios AWS/Gemini) |
| Trabalho 2 | 15% | Segunda entrega prática já feita em aula |
| **Trabalho Final (esta pasta)** | **70%** | Projeto integrado Quantum Commerce, versão AWS, com foco em arquitetura e decisão técnica |
| **Total** | **100%** | |

> Os critérios do Trabalho 1 e 2 estão na [rubrica.md](rubrica.md). Se a divisão real dos dois trabalhos foi diferente da descrita ali, ajuste os critérios — o que importa é fechar 30% com o que já foi de fato entregue, sem reabrir trabalho para o aluno.

---

## O foco deste trabalho: arquitetura, não deploy complexo

O desenho original do projeto final (Azure) pedia um ZIP com 9 artefatos obrigatórios e uma arquitetura completa provisionada via Terraform (banco relacional + NoSQL + busca vetorial + 5 rotas de API + endpoint de ML). Para a trilha AWS, o foco muda de propósito:

1. **As aulas 1, 2 e 5 nunca foram convertidas para AWS** — não existe uma base ensinada e testada em aula para esses serviços nesta trilha.
2. **O objetivo pedagógico deste momento do curso é raciocínio arquitetural, não operação de infraestrutura.** Os trabalhos práticos já entregues provaram que o grupo sabe rodar Lambda + API Gateway + S3 + Gemini. O trabalho final não precisa repetir essa prova — precisa testar se o grupo sabe **desenhar e justificar** uma arquitetura maior a partir disso.

Por isso, o trabalho final pede **um documento de arquitetura e decisão** (peso maior, é o que de fato está sendo avaliado) + **as 5 funcionalidades de referência rodando, reaproveitadas da Aula 3 e dos trabalhos práticos já entregues** (peso menor, só para ancorar o desenho em algo real) — em vez de exigir infraestrutura nova e complexa provisionada do zero para toda a Quantum Commerce.

> **Isso não é implementação nova.** 4 das 5 tools (RAG, NER, Call Center Analytics, Campanha de Marketing) já rodam hoje atrás de **um único API Gateway**, no mesmo stack Terraform que o grupo já construiu nos trabalhos práticos — a integração entre elas já existe. A 5ª (`buscar_produtos`) vem de um stack separado, da Aula 3. "Reaproveitar" aqui significa, literalmente, rodar `terraform apply` de novo nesses dois stacks e confirmar que ainda respondem — não escrever nada do zero.
>
> **Reprovisionem com alguns dias de antecedência, não nos últimos 2 dias.** O ambiente foi destruído ao fim daquele momento prático (regra de ouro de custo), então os grupos vão reprovisionar do zero. Se todo mundo deixar pra última hora, o grupo pode esbarrar nos mesmos limites já conhecidos desse material — rate limit do Gemini por chave compartilhada, cota diária do ZeroGPU no Hugging Face (usada pela tool de Campanha). Esses limites se resolvem com tempo, não com pressa.

---

## O que é

Consolidação do que o grupo aprendeu nos trabalhos práticos já entregues em um projeto coerente para a Quantum Commerce, demonstrando:

1. **Arquitetura AWS proposta** para os principais domínios da QC (catálogo, busca/RAG, extração de dados, atendimento, marketing)
2. **Decisões técnicas justificadas** (por que cada serviço, não só qual serviço)
3. **As 5 tools de referência rodando**, reaproveitadas da Aula 3 e dos trabalhos práticos já entregues
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
└── poc/                     # ⭐ as 5 tools rodando, reaproveitadas da Aula 3 e dos trabalhos práticos
    ├── lambda_function.py   # (ou a pasta do seu código dos trabalhos práticos, reaproveitada)
    └── terraform/           # reaproveita o padrão já usado na Aula 3 e nos trabalhos práticos
```

**Tamanho do ZIP:** < 10 MB. **Não incluir:** `terraform.tfstate*`, `.env`, `__pycache__/`, imagens/áudios de exemplo grandes (reaproveite os dos trabalhos práticos por referência, não precisa reempacotar).

**Como gerar o ZIP** (mesmo padrão das entregas anteriores):

```bash
cd ~/qc-grupo-NN
git archive --format=zip --prefix=trabalho-final-aws-grupo-NN/ \
  -o ~/trabalho-final-aws-grupo-NN.zip HEAD:trabalho-final-aws
```

---

## Guia de componentes AWS

Referência rápida pra preencher a tabela de arquitetura e as decisões técnicas do `projeto.md`. Separado em dois blocos: o que já foi testado nesta trilha (base sólida, pode citar com confiança) e o que não foi testado mas é válido considerar no desenho (o Critério A avalia a justificativa da escolha, não exige experiência prática com o serviço).

### Já testado nesta trilha (Aula 3 e trabalhos práticos)

| Categoria | Serviço AWS | Onde foi usado |
|---|---|---|
| Compute serverless | Lambda | Todas as 5 tools de referência |
| API | API Gateway (HTTP API) | Expõe as Lambdas por rota HTTP |
| Armazenamento de objetos | S3 | Documentos, áudios, imagens de entrada e saída |
| Banco relacional + vetorial | RDS PostgreSQL + pgvector | Chunker (indexação) e RAG (busca híbrida) |
| Banco NoSQL | DynamoDB | NER (entidades) e Call Center Analytics (avaliações) |
| Segredos | Secrets Manager | Senha do RDS |
| Rede de saída | NAT Gateway | Rota da Lambda (dentro da VPC) até o Gemini |
| Identidade | IAM (LabRole compartilhado) | Execução de todas as Lambdas |
| Observabilidade | CloudWatch Logs | Logs de cada Lambda |
| IA generativa (externa, não é AWS) | Gemini API (Google) | Texto, visão, áudio, embeddings — em todas as tools |
| IA generativa (externa, não é AWS) | Hugging Face Spaces | Edição de imagem (FLUX) e geração de modelo 3D (TRELLIS) |

### Outros componentes AWS a considerar (não testados em aula, mas válidos no desenho)

A QC tem domínios que os labs não cobriram. Pode citá-los na arquitetura e nos ADRs como decisão de design — não precisa ter sido implementado para valer no Critério A.

| Domínio | Opções AWS | Quando faria sentido |
|---|---|---|
| Compute para cargas longas/contínuas | ECS/Fargate, EC2 | Quando o teto de 15 min da Lambda não serve (ex: processamento em lote grande) |
| CDN | CloudFront | Servir imagens de produto com baixa latência global |
| Mensageria/filas | SQS, SNS | Desacoplar picos de carga (ex: campanha disparada em massa) |
| Cache | ElastiCache (Redis) | Sessão de usuário, carrinho de compras ativo |
| Identidade de cliente final | Cognito | Login do cliente da QC — diferente do LabRole, que é só para as Lambdas |
| Observabilidade distribuída | X-Ray | Rastrear uma requisição que passa por várias Lambdas |
| Segurança de borda | WAF | Proteger a API Gateway de abuso |
| Catálogo de modelos gerenciado | Bedrock | Indisponível nesta conta AWS Academy — citar como opção conceitual, é exatamente o que embasa a decisão de usar Gemini direto |
| ML gerenciado (treino/serving) | SageMaker | Seria o caminho pra um endpoint de recomendação de verdade — o equivalente ao `/recomendar` do projeto original; pode aparecer como decisão de design, sem exigir implementação |

---

## Detalhes de cada peça

### 1. `projeto.md` — documento único

Um arquivo markdown com estas seções (não precisa ser mais de 3-4 páginas no total):

#### Arquitetura proposta
Diagrama + uma tabela de serviços AWS por domínio, com justificativa curta. Use o [Guia de componentes AWS](#guia-de-componentes-aws) abaixo como referência:

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
Formato ADR curto (decisão → contexto → alternativas → trade-off). Exemplos de decisões que valem a pena documentar: *por que Lambda e não ECS/Fargate*, *por que RDS+pgvector e não um serviço de busca vetorial gerenciado*, *por que Gemini direto e não um catálogo de modelos gerenciado (Bedrock)* — esta última em particular conecta direto com o que já foi discutido em aula sobre a conta do AWS Academy.

#### FinOps essencial
Uma tabela de estimativa mensal (pode ser calculada manualmente a partir dos preços unitários já vistos nos trabalhos práticos — Lambda, NAT Gateway, RDS, DynamoDB) + 2 propostas de otimização, um parágrafo cada. Não é exigido export formal da AWS Pricing Calculator, mas é um diferencial se o grupo quiser fazer.

#### Reflexão estratégica (curta)
- Próximos 2 trimestres: o que a QC precisaria resolver primeiro e depois
- 3-5 linhas de lições aprendidas do módulo inteiro

### 2. `tools-spec.json` — as 5 tools de referência

> **Não é preciso Bedrock, AgentCore ou qualquer agente rodando de verdade.** Esta trilha não teve uma aula aprofundada sobre agentes em cloud, e isso é esperado — orquestração de agente é tema de outra disciplina do MBA. Aqui, "tool" é só a forma de descrever um serviço AWS que **um agente poderia chamar**: nome, quando usar, schema de entrada, um exemplo de pergunta que dispararia. É documento, não infraestrutura.
>
> **"Tool" é apenas uma API comum, descrita de um jeito específico — nada além disso.** Toda tool que vocês já construíram nos trabalhos práticos (a rota `/process` da Lambda do Chunker, o `POST /rag/query`, etc.) **já é** uma tool, no sentido estrito: um endpoint HTTP com entrada e saída definidas. A única diferença entre "API" e "tool" é a camada de descrição em cima:
>
> | Pergunta que a descrição responde | Onde isso já existe hoje |
> |---|---|
> | Qual é o endpoint? | A URL do API Gateway + rota da Lambda (já existe desde os trabalhos práticos) |
> | O que ele faz? | A docstring da função, ou o `README.md` do exercício |
> | Quais parâmetros aceita? | O corpo do `POST` que vocês já montam no `curl` |
> | Quando alguém (ou um agente) deveria chamá-lo? | A única pergunta nova — é o `description` do JSON Schema, escrito em linguagem natural |
>
> Ou seja: pra virar uma "tool", uma API só precisa ganhar uma descrição em linguagem natural de **quando usá-la**, pensada do ponto de vista de quem decide chamar (hoje, um humano rodando `curl`; amanhã, um LLM decidindo sozinho). Não tem SDK, protocolo ou infraestrutura nova envolvida.

A arquitetura da QC se apoia em 5 capacidades, mapeadas direto dos exercícios práticos já feitos:

| Tool | Deriva de | O que faz |
|---|---|---|
| `buscar_produtos` | Aula 3 (Lambda + S3) | Busca no catálogo por categoria/nome |
| `responder_duvida` | Chunker + RAG | Responde pergunta do cliente citando a fonte (RAG sobre pgvector) |
| `extrair_dados_documento` | NER | Extrai dados estruturados de um documento (nota fiscal, cadastro) |
| `avaliar_atendimento` | Call Center Analytics | Transcreve e avalia uma ligação de atendimento |
| `gerar_campanha` | Campanha de Marketing | Gera texto + imagem de campanha a partir da foto de um produto |

Especifique as 5 no formato de function calling (nome, descrição que ensine o agente quando usar, schema de entrada, pelo menos 1 exemplo de uso cada).

### 3. `poc/` — as 5 tools rodando

Reaproveite o código e o Terraform que o grupo já fez na Aula 3 e nos trabalhos práticos — não é pra escrever nada do zero:

- **4 tools (RAG, NER, Call Center Analytics, Campanha de Marketing):** `terraform apply` no stack único já construído nos trabalhos práticos (já expõe todas atrás de um único API Gateway)
- **1 tool (`buscar_produtos`):** `terraform apply` no stack da Aula 3

Documente no `README.md` dentro de `poc/` como rodar os dois.

**Critério de aceitação:** as 5 tools respondem a uma chamada real (`curl`) e isso está documentado (comando + saída, print ou texto colado) para cada uma.

**Se alguma tool não rodar por limitação externa documentada** (ex: cota do ZeroGPU no Hugging Face esgotada, rate limit do Gemini), isso é aceitável — descreva a tentativa, cole o erro, e explique o que travou. Não precisa ficar tentando até funcionar.

---

## O que NÃO é mais exigido (em relação ao projeto final original)

- Terraform novo provisionando camadas nunca ensinadas nesta trilha (Cosmos DB, Azure SQL, AI Search) — o Terraform exigido é só o que já existe da Aula 3 e dos trabalhos práticos
- Endpoint de ML/recomendação publicado (vira só uma linha de design em `projeto.md`, se o grupo quiser mencionar)
- Managed Identity / IAM por tool — o LabRole compartilhado usado nos trabalhos práticos é aceitável, com a ressalva já discutida em aula sobre revogação não ser por agente
- `distribuicao-do-trabalho.md` separado — vira um parágrafo dentro do `projeto.md`

---

## Perguntas frequentes

**Q: Precisamos rodar as 5 tools?**
A: Sim — mas reaproveitando o que já foi construído na Aula 3 e nos trabalhos práticos, não implementando do zero. Se alguma travar por limitação externa documentada (cota, rate limit), documentem a tentativa — não precisam ficar tentando até funcionar.

**Q: Podemos reaproveitar o código dos trabalhos práticos quase inteiro?**
A: Sim — é esperado, e é basicamente o ponto. O trabalho final testa se vocês conseguem **encaixar** o que já fizeram numa arquitetura maior e justificá-la, não reescrever do zero.

**Q: Quando devemos reprovisionar o ambiente?**
A: Com alguns dias de antecedência do prazo, não nos últimos 2 dias — veja o aviso em [O foco deste trabalho](#o-foco-deste-trabalho-arquitetura-não-deploy-complexo).

**Q: O Terraform precisa rodar sem erro?**
A: Sim, para os dois stacks reaproveitados (Aula 3 e os trabalhos práticos) — já devem rodar, porque já rodaram antes.

**Q: Podemos usar repositório público?**
A: Não. Entrega via ZIP no Portal FIAP, mesma regra das entregas anteriores.

---

## Lembrete final

Entrega via **Portal FIAP**, um único membro do grupo faz o upload. Avaliação por esta rubrica + revisão humana, nota e comentários devolvidos no Portal.
