# Nota — Divergência entre `entregas/` (Azure) e a trilha AWS

**Status:** a linha "Projeto Final" da tabela abaixo foi resolvida —
ver [`entregas/trabalho-final-aws/`](trabalho-final-aws/) (INSTRUCOES.md +
rubrica.md), que substitui `projeto-final/` para quem seguiu a trilha AWS.
A nota final da trilha AWS passou a ser **30% Aula 7 (dois trabalhos práticos
já entregues) + 70% Trabalho Final AWS**, em vez dos 50%/50% originais —
decisão tomada porque as entregas intermediárias das Aulas 1-5 não foram
cobradas de forma consistente durante a transição para AWS. As linhas 1, 2,
5 e 6 da tabela (aulas sem conteúdo AWS) continuam como pendência em aberto,
nenhuma ação tomada ainda.

## O achado

O repositório tem duas trilhas paralelas:

- **Azure** (original): `01-fundamentos-iac`, `02-storage-bancos`,
  `03-serverless-containers`, `04-servicos-cognitivos`, `05-mlops`,
  `06-finops-projeto-final`.
- **AWS** (criada depois, por limitação real de ambiente — contas AWS
  Academy Learner Lab, Bedrock indisponível, etc.): `03-serverless-containers-aws`,
  `04-servicos-cognitivos-aws`, `05-ai-agents-aws`.

A pasta `entregas/` (instruções de cada entrega + `rubrica.md` +
`projeto-final/INSTRUCOES.md`) nunca foi adaptada para a trilha AWS — todo
o conteúdo aponta exclusivamente para os arquivos e a arquitetura da
trilha Azure.

## Tabela comparativa

| Aula | `entregas/` aponta pra | Existe versão AWS? | Divergência | Esforço estimado |
|------|------------------------|---------------------|--------------|-------------------|
| 1 | `01-fundamentos-iac/exercicios.md` | Não tem sufixo `-aws` (conteúdo já é cloud-neutro; cita Terraform/Bicep como opções) | Baixa | Revisão leve |
| 2 | `02-storage-bancos/exercicios.md` (Cosmos DB, Key Vault, Synapse) | **Não existe `02-storage-bancos-aws`** | Crítica — falta o conteúdo da aula em si, não só a entrega | Alto (criar aula + entrega do zero) |
| 3 | `03-serverless-containers/exercicios.md` (Function, ACI, Managed Identity) | `03-serverless-containers-aws/` existe e **espelha exercício por exercício** (Lambda, Elastic Beanstalk, IAM Role, CloudWatch/X-Ray) | Baixa — mesma numeração de exercícios, só terminologia/serviço mudam | Baixo (trocar link + termos) |
| 4 | `04-servicos-cognitivos/exercicios.md` (Speech + Language + Vision como 3 serviços Azure separados, Azure OpenAI p/ embeddings) | `04-servicos-cognitivos-aws/` — **pipeline único de RAG via Gemini multimodal** (transcrever → indexar → perguntar contra RDS+pgvector). Exercícios completamente diferentes (1.1 trazer PDF real, 2.2 chunking que quebra resposta, 3.3 orçamento de NAT Gateway, etc.) | **Alta — reescrita completa** | Alto |
| 5 | `05-mlops/exercicios.md` (Azure ML Workspace, recomendador, Model Registry, drift monitoring) | `05-ai-agents-aws/` — **agente "Deva" com memória e fila de exceção** (arquivar regra, rastreabilidade, segunda opinião de outro agente). Tema não relacionado a MLOps/modelos de ML | **Alta — reescrita completa** | Alto |
| Projeto Final | 5 tools de referência: `/produtos /transcrever /analisar-reviews /analisar-imagem /recomendar`; arquitetura com Azure SQL, Cosmos DB, AI Search, Azure ML Workspace | Nada disso existe na trilha AWS construída (é S3, RDS+pgvector, Lambda, API Gateway, SQS) | **Alta — spec de tools e arquitetura de referência erradas para quem seguiu AWS** | Alto |
| 6 (FinOps) | Cost Management + Azure Advisor + Azure Pricing Calculator | **Não existe `06-finops-projeto-final-aws`** | Crítica — falta o lab de FinOps em AWS inteiro (equivalente seria Cost Explorer + Trusted Advisor + AWS Pricing Calculator) | Alto (criar aula do zero) |

## Consequência prática

Um grupo seguindo a trilha AWS (ambiente real disponível nesta disciplina,
confirmado ao longo desta sessão: AWS Academy Learner Lab, Bedrock
indisponível, Gemini como LLM) está sendo avaliado, na prática, contra uma
rubrica e uma lista de entregáveis que descrevem uma arquitetura e
exercícios que o grupo nunca fez — e cobrando tools (`/analisar-reviews`,
`/recomendar` via Azure ML) que não existem no que foi de fato construído.

## Opções discutidas (nenhuma executada ainda)

1. **Criar `entregas-aws/` paralela** — espelha a estrutura atual de
   `entregas/`, mas reescrita para o pipeline AWS real de cada aula
   (opção que o usuário sinalizou como preferida, a confirmar).
2. Corrigir só 01 e 03 agora (menor esforço) e deixar 02/04/05/06/projeto
   final como pendência documentada.
3. Reescrever `entregas/` no próprio lugar, assumindo que a turma não usa
   mais a trilha Azure.
4. Manter só esta nota por enquanto (opção escolhida nesta rodada).

## Gaps que precisam de decisão antes de qualquer reescrita

- **Aula 2 AWS não existe.** Antes de escrever uma `entrega-02-aws`,
  precisa existir o conteúdo da aula (`02-storage-bancos-aws/`: RDS ou
  DynamoDB, Secrets Manager, S3 com lifecycle, etc.) — não é só questão
  de entrega.
- **Aula 6 AWS não existe.** Mesma situação: falta o lab de FinOps em AWS
  (Cost Explorer, Trusted Advisor, AWS Pricing Calculator) antes de
  qualquer entrega/projeto final fazer sentido nesse formato.
- **Projeto final consolidado** depende de decidir as 5 tools reais da
  trilha AWS (hoje: `/produtos` da aula 3, `/transcrever` `/indexar`
  `/perguntar` da aula 4 — já são 4 rotas RAG só na aula 4 — mais o que
  vier da aula 5, que é sobre memória de agente, não sobre uma 5ª tool de
  recomendação). A lista de 5 tools do projeto final Azure não se traduz
  1:1 para AWS.
