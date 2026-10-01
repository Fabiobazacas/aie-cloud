# Exercícios — Aula 7 (AWS): Pipelines Cognitivos Serverless

**Tema:** Lambda + API Gateway + S3 + Gemini — chunking, RAG, NER, voz, campanha e 3D
**Formato:** exercícios para depois do lab (individual ou em grupo — combine com o professor)

---

## Instruções gerais

**Faça o [lab/guia-lab.md](lab/guia-lab.md) primeiro.** Ele já sobe os 6
pipelines com um `terraform apply` só. Os exercícios abaixo **partem do lab já
no ar**: não é para reconstruir a infraestrutura, é para rodar, quebrar,
medir e estender o que já existe.

- 🟢 **Nível 1 — Básico:** rodar com arquivos próprios e explicar o código
- 🟡 **Nível 2 — Intermediário:** alterar prompts/parâmetros e medir o efeito
- 🔴 **Nível 3 — Avançado (bônus):** estender o pipeline (custo, novo serviço, agente)

> **Política "no install":** tudo no AWS CloudShell. Para alterar o código de uma
> Lambda, edite o arquivo e rode `terraform apply` de novo — o Terraform detecta
> a mudança, reconstrói o zip e atualiza só a função afetada.

Antes de começar, defina as variáveis de ambiente do guia:

```bash
cd ~/aie-cloud/aulas/07-function-aws/lab/terraform
export API_URL=$(terraform output -raw api_gateway_url)
export BUCKET=$(terraform output -raw bucket)
```

---

## 🟢 Nível 1 — Básico

### Exercício 1.1 — Traga o seu próprio documento (Ex01 + Ex03)

Escolha um PDF seu (contrato, nota fiscal, manual) — de preferência um
**escaneado**, sem camada de texto. Suba para o bucket e rode o chunker e o NER:

```bash
aws s3 cp meu-documento.pdf s3://$BUCKET/documents/meu-documento.pdf
curl -s -X POST "$API_URL/process" -H "Content-Type: application/json" -d '{"bucket_key":"documents/meu-documento.pdf"}'
curl -s -X POST "$API_URL/ner"     -H "Content-Type: application/json" -d '{"bucket_key":"documents/meu-documento.pdf"}'
```

a) Os chunks fazem sentido? Algum corta uma frase ou uma tabela no meio?
b) O NER extraiu os campos certos? O prompt `lab/prompts/ner_system.md` foi escrito
   para **matrículas de imóvel** — o que aconteceu com os campos que não existem no seu documento?
c) Quanto tempo levou o job (compare `jobs/<id>.json` com os logs)? O que dominou o tempo?

### Exercício 1.2 — Leia e explique o código

Abra [lab/shared/pdf.py](lab/shared/pdf.py) e [lab/shared/web.py](lab/shared/web.py) e responda:

a) Por que páginas escaneadas viram **imagem** (PNG) antes de ir ao Gemini, em vez de tentar extrair texto?
b) Por que o OCR roda em **paralelo** (`ThreadPoolExecutor`)? O que aconteceria com um PDF de 40 páginas?
c) Por que `/process` responde `202` e não o resultado? Que limite da AWS causa isso?
d) Por que a função de job grava `{"status":"erro"}` no S3 em vez de só deixar a exceção subir?

### Exercício 1.3 — O mapa Azure → AWS

Sem olhar a tabela do README, preencha o equivalente AWS de cada serviço do laboratório
original: Azure Functions, Blob Storage, Azure AI Search, Cosmos DB, Azure Speech,
GPT-image-2, Blob Trigger, SAS URL. Depois aponte **um** ponto em que a versão AWS é
**pior ou mais cara** que a versão Azure e **um** em que é melhor.

**✅ Checkpoint N1:** você rodou os pipelines com um documento próprio e respondeu 1.1–1.3?

---

## 🟡 Nível 2 — Intermediário

### Exercício 2.1 — Chunking muda a resposta (Ex01 + Ex02)

O chunking define o que o RAG consegue achar.

a) Rode o RAG com 3 perguntas sobre a matrícula (ex.: "Qual a área total do imóvel?",
   "Existe alguma hipoteca vigente?", "Quem é o cartório responsável?") e anote resposta,
   `confidence` e `chunks_scores`.
b) Edite `lab/prompts/chunking_system.md` para pedir chunks **bem menores** (ex.: 50–100 palavras)
   e reaplique (`terraform apply`). Reindexe (`/process`) e repita as 3 perguntas.
c) Agora peça chunks **bem maiores**. Compare as três configurações numa tabela:
   acertou? com que score? a fonte citada era o chunk certo?
d) Explique por que o tamanho do chunk afeta (ou não) a chance de responder errado sobre
   um detalhe específico (um valor, uma data, uma exceção numa tabela).

### Exercício 2.2 — Busca vetorial vs. palavra-chave vs. híbrida

Em `lab/shared/db.py`, `busca_hibrida` funde duas listas. Troque, em `lab/lambda/ex02_rag/lambda_function.py`,
`db.busca_hibrida(...)` por `db.busca_vetorial(...)` e depois por `db.busca_texto(...)`.

a) Encontre uma pergunta que **só a busca vetorial** acerta (sinônimos, paráfrase).
b) Encontre uma pergunta que **só a busca por palavra-chave** acerta (número de matrícula, CPF, nome próprio).
c) Por que a busca híbrida é a escolha padrão em produção?

### Exercício 2.3 — O prompt é o contrato (Ex03 e Ex04)

a) No Ex03, troque o prompt de NER por um para **nota fiscal** (campos: emitente, CNPJ, itens, total, impostos)
   e rode contra uma nota real. O que o `response_format`/`json_mode` garante e o que **não** garante
   (o JSON é válido? os campos são os pedidos? os valores estão corretos?)
b) No Ex04, grave um áudio seu de 30–60 s simulando um atendimento ruim (grosseiro, sem protocolo).
   A `nota_geral` caiu? A lista de `pontos_melhoria` faz sentido? O que o modelo não tem como avaliar só pela fala?

### Exercício 2.4 — Campanha com restrições (Ex05)

Rode o Ex05 com duas imagens diferentes (`images/sabonete.png` e `images/tenis.jpg`) e depois
com uma imagem sua. Altere `lab/prompts/marketing_campaign.md` para impor uma restrição de marca
(ex.: "nunca use superlativos", "tom formal", "público 60+") e compare. Em quais casos a imagem
gerada **perdeu a identidade do produto**? O que no prompt de edição (`prompt_de_edicao`) tenta evitar isso?

**✅ Checkpoint N2:** você mediu o efeito de ao menos 2 alterações (chunking e prompt) com evidência?

---

## 🔴 Nível 3 — Avançado (bônus)

### Exercício 3.1 — Custo e latência de verdade

Instrumente `ex02_rag` para devolver no JSON a **latência de cada etapa** (embedding da pergunta,
busca no pgvector, geração) com `time.perf_counter()`. Rode 10 perguntas e calcule média e p95.
Depois estime o custo mensal de 100 mil perguntas: chamadas ao Gemini (veja a
[página de preços](https://ai.google.dev/gemini-api/docs/pricing) — ainda cabe no free tier?)
**mais** RDS ocioso 24/7 **mais** NAT Gateway (~US$0,045/h + US$0,045/GB). Qual componente domina?

### Exercício 3.2 — Tirar o NAT Gateway

O NAT Gateway existe só porque as Lambdas de RAG estão na VPC (por causa do RDS) e o Gemini é externo.

a) Desenhe duas alternativas que eliminam o NAT: (i) trocar RDS+pgvector por um armazenamento
   alcançável sem VPC (ex.: DynamoDB/S3 com similaridade calculada na Lambda), (ii) separar em duas
   Lambdas — uma na VPC só para o banco, outra fora da VPC só para o Gemini.
b) Quais os trade-offs de cada uma (latência, complexidade, limite de escala dos vetores)?
c) Implemente a (i) para um conjunto pequeno de chunks e compare a latência.

### Exercício 3.3 — Transcrição com AWS Transcribe

O Ex04 usa o Gemini para transcrever. Escreva `ex04b_transcribe` usando **Amazon Transcribe**
(job assíncrono: `start_transcription_job` → polling de `get_transcription_job`) e compare com o
Gemini em: qualidade em pt-BR, suporte a vários falantes (`ShowSpeakerLabels`), custo e latência.
(Confirme antes se o Transcribe está liberado na sua conta do Learner Lab.)

### Exercício 3.4 — Um agente que escolhe a ferramenta

No laboratório original (Ex07), um agente do Azure AI Foundry orquestrava os exercícios 01, 02, 03 e 05 via
*function calling*. Implemente a versão AWS: uma nova Lambda `agente` que usa **Gemini com function
calling** (`tools` → `functionDeclarations`) e declara como ferramentas `index_document`,
`query_knowledge_base`, `extract_entities` e `create_marketing_campaign`, cada uma chamando o endpoint
correspondente de `$API_URL`. Teste com: *"Indexe a matrícula e me diga quem é o proprietário."*
O que muda entre **você** orquestrar (chamar cada endpoint) e o **modelo** orquestrar?
(Veja também a [Aula 5 — AI Agents](../05-ai-agents-aws/).)

### Exercício 3.5 — Desafio estendido (3D)

Antes de enviar a imagem ao TRELLIS, use o Gemini (visão) para **validar** se ela é adequada
(objeto único, fundo limpo). Só dispare a conversão se passar; senão grave um `error.json` explicando
o motivo. Isso reduz fila e custo em um serviço externo e instável.

---

## Wrap-up — Destroy obrigatório

```bash
cd ~/aie-cloud/aulas/07-function-aws/lab/terraform
terraform destroy -auto-approve -var="gemini_api_key=$GEMINI_API_KEY"
```

> **Atenção especial ao RDS e ao NAT Gateway:** uma instância RDS rodando cobra por hora mesmo sem uso, e um
> NAT Gateway esquecido ligado cobra por hora e por GB. Confirme que foram removidos
> (`aws rds describe-db-instances` / `aws ec2 describe-nat-gateways`).
