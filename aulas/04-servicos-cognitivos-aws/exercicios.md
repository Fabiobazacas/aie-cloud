# Exercícios — Aula 4 (AWS): Pipeline de RAG

**Tema:** RAG (Retrieval-Augmented Generation) — do PDF ao endpoint
**Formato:** **Entrega obrigatória por grupo** — ZIP no Portal FIAP
**Vale:** 10% da nota final ([rubrica completa](../../entregas/rubrica.md))
**Prazo:** 1 dia antes da Aula 5
**Como entregar:** ver [entregas/entrega-04/INSTRUCOES.md](../../entregas/entrega-04/INSTRUCOES.md)

---

## Instruções gerais

**O problema de negócio, primeiro:** o time de atendimento da Quantum
Commerce recebe centenas de perguntas por dia sobre política de troca,
garantia e catálogo — muitas com resposta certa em algum PDF (manual,
política, contrato de fornecedor) que ninguém tem tempo de abrir. Pior:
uma resposta errada sobre prazo de troca vira uma promessa que a empresa
não pode cumprir. O pipeline desta aula é a base de conhecimento que um
agente da QC usa pra responder **com base no documento real**, citando a
fonte — não "no que o modelo lembra de treino".

**Faça o [lab/guia-lab.md](lab/guia-lab.md) primeiro.** Ele já sobe o
pipeline inteiro — S3, RDS/pgvector, rede (NAT Gateway), Lambda com as 6
rotas (`/health`, `/setup-db`, `/status`, `/transcrever`, `/indexar`,
`/perguntar`) — com um
`terraform apply` só. Os exercícios abaixo **partem desse lab já no ar** e
giram em torno de problemas que a QC teria de verdade com esse pipeline —
não é pra reconstruir a infraestrutura do zero, é pra rodar, colocar
documentos e perguntas reais da QC contra ele, e resolver onde ele falha.

- 🟢 **Nível 1 — Básico:** rodar a ingestão/transcrição com um PDF próprio do grupo, entender o código
- 🟡 **Nível 2 — Intermediário:** rodar o chunking/indexação, testar estratégias diferentes, entender o banco vetorial
- 🔴 **Nível 3 — Avançado:** **bônus opcional** — estender o endpoint de RAG (métricas, reranking/streaming/citação)

**Mínimo obrigatório:** N1 + N2 cobertos. **N3 é bônus** (até +2 pts extras).

### Distribuição entre membros (sugerida)

- Iniciantes: N1 — rodar o pipeline, trocar o PDF, entender a transcrição
- Intermediários: N2 — chunking, embeddings, pgvector
- Experientes: N3 — estender o endpoint de RAG + métricas

> **Rodízio:** quem fez N1 nas Aulas 1-3 deve assumir N2 ou N3 agora.

### Template obrigatório

Use o [template em `entregas/template-entrega-grupo.md`](../../entregas/template-entrega-grupo.md) para o `entrega-grupo-aula04.md` dentro do ZIP.

> **Política "no install":** Tudo no AWS CloudShell (que já tem Docker e AWS CLI — só falta instalar o Terraform, como nas aulas anteriores).

---

## Atividade 0 — Suba o lab (se ainda não subiu)

Siga [lab/guia-lab.md](lab/guia-lab.md), seção **Preparação** + **LAB 1**:
crie sua chave gratuita do Google Gemini (uma por GRUPO —
[aistudio.google.com/apikey](https://aistudio.google.com/apikey), sem
cartão), clone o repo, e rode:

```bash
cd ~/aie-cloud/aulas/04-servicos-cognitivos-aws/lab/terraform
terraform init
terraform apply -auto-approve -var="gemini_api_key=$GEMINI_API_KEY"
```

> **Sobre o Bedrock:** já confirmamos, numa sessão real do Learner Lab,
> que ele **não é liberado** nesta conta (`AccessDeniedException` por falta
> de policy, não por modelo desabilitado) — por isso o lab inteiro usa
> Google Gemini. Se a sua conta for uma exceção e liberar Bedrock de
> verdade, a arquitetura não muda — só a chamada ao modelo em
> `lab/lambda/lambda_function.py` mudaria de `urllib`/Gemini pra
> `boto3`/`bedrock-runtime`. Não é exigido pra esta entrega.

**✅ Checkpoint:** `terraform output api_gateway_url` retorna uma URL, e `curl "$(terraform output -raw api_gateway_url)/health"` devolve `{"status": "ok", ...}`?

---

## 🟢 Nível 1 — Básico: Ingestão e Transcrição via LLM

### Exercício 1.1 — Traga um documento que a QC realmente teria

O `lab/data/catalogo_qc.pdf` do Lab 1 é fictício e pequeno de propósito
(pra rodar rápido em sala) — mas a QC de verdade recebe **manuais de
fornecedor, contratos e políticas de categorias inteiras**, quase sempre em
PDF, e boa parte digitalizada sem camada de texto (é assim que chega da
gráfica ou do fornecedor). Sua tarefa: suba um documento desse perfil —
manual de produto, política de outra categoria, um PDF **escaneado/só-imagem**
de verdade — simulando o que o time de conteúdo da QC realmente jogaria
nesse pipeline.

```bash
export DOCS_BUCKET=$(cd ~/aie-cloud/aulas/04-servicos-cognitivos-aws/lab/terraform && terraform output -raw rag_docs_bucket)
aws s3 cp seu-documento.pdf "s3://$DOCS_BUCKET/seu-documento.pdf"
```

Rode `/transcrever` contra ele e confira que o texto saiu certo — imagine
que é o time de atendimento da QC conferindo se pode confiar nesse texto
pra responder cliente.

### Exercício 1.2 — Leia e explique o código de transcrição

Abra [lab/scripts/transcrever_pdf.py](lab/scripts/transcrever_pdf.py) (versão local,
mais fácil de ler) e a rota `rota_transcrever` em
[lab/lambda/lambda_function.py](lab/lambda/lambda_function.py) (versão
deployada — mesma lógica, lendo do S3 em vez de um arquivo local).

No `entrega-grupo-aula04.md`, explique em suas palavras:

a) Por que a página do PDF é convertida pra **imagem** (PNG) antes de
   mandar pro Gemini, em vez de mandar o PDF inteiro ou tentar extrair
   texto primeiro?
b) O prompt pede explicitamente "não resuma, não comente — só a
   transcrição". Imagine que a página é a política de troca de
   eletrodomésticos da QC, com prazo de 12 meses por defeito. Se o modelo
   "resumisse" em vez de transcrever, e resumo cortasse a exceção de prazo,
   um cliente poderia receber a resposta errada (ex.: 90 dias em vez de 12
   meses) — e a QC teria prometido algo que não devia. Por que esse é
   especificamente um problema de **retrieval** (o Exercício 3.x busca só
   pedaços do texto, não a página inteira), e não só "o resumo ficou pior"?
c) Rode o mesmo PDF duas vezes seguidas com `/transcrever`. O resultado é
   idêntico nas duas vezes? Por quê (ou por que não)?

> **Alternativa sem chave nenhuma — AWS Textract (confirmado disponível
> nesta conta):** diferente do Bedrock, já testamos e o **Textract
> funciona** nesta conta do Learner Lab, sem precisar de `GEMINI_API_KEY`
> — só a `LabRole` que a Lambda/CloudShell já usa. Ele resolve **só a
> extração de texto** (não gera embeddings nem responde perguntas), então
> mesmo usando Textract, os Exercícios 2.x e 3.x continuam precisando do
> Gemini. Se seu grupo quiser comparar as duas abordagens de verdade,
> escreva um script `scripts/transcrever_textract.py` próprio:
> ```python
> import boto3
> textract = boto3.client("textract", region_name="us-east-1")
>
> def transcrever_pagina_textract(imagem_bytes: bytes) -> str:
>     resp = textract.detect_document_text(Document={"Bytes": imagem_bytes})
>     linhas = [b["Text"] for b in resp["Blocks"] if b["BlockType"] == "LINE"]
>     return "\n".join(linhas)
> ```
> (reaproveite `pagina_para_base64_png`/`fitz.open` de `transcrever_pdf.py`
> pra virar bytes de imagem — só troca o `data:` base64 por bytes crus, que
> é o que o Textract espera).

**✅ Checkpoint L₁:** você trocou o PDF, confirmou a transcrição de um documento próprio, e respondeu as 3 perguntas do 1.2?

### Exercício 1.3 — A decisão que o time de engenharia da QC precisa tomar

A QC tem **200 catálogos de fornecedores** (~15 páginas cada) esperando
pra entrar nesse pipeline, e o time de engenharia precisa decidir: usar
Textract (mais barato, mais rápido, mas OCR puro) ou Gemini (mais caro,
entende contexto e tabelas, mas depende de uma API externa)? Responda no
`entrega-grupo-aula04.md`, como se fosse essa decisão de verdade:

a) Rode o script do Textract (acima) contra o mesmo PDF do Exercício 1.1 e
   compare com a saída de `/transcrever` (Gemini) — cole os dois resultados
   lado a lado. Cite 2 cenários (entre os documentos reais da QC: manuais,
   políticas, contratos de fornecedor) onde o Textract resolve bem e mais
   barato, e 2 onde só o Gemini resolve (ex.: tabelas de prazo por
   categoria, texto de formatação irregular).
b) Estime o custo de transcrever os **200 catálogos de fornecedores da QC**
   (~15 páginas cada, em média) com o modelo que você usou. Confira se seu
   volume ainda cabe no free tier do Gemini (rate limit por minuto/dia) ou
   se passaria pro tier pago — use a
   [página de pricing do Gemini API](https://ai.google.dev/gemini-api/docs/pricing)
   pra estimar o custo além do free tier.

---

## 🟡 Nível 2 — Intermediário: Chunking, Embeddings e pgvector

### Exercício 2.1 — Entenda o banco vetorial já provisionado

A base de conhecimento da QC vai guardar política de troca, contrato de
fornecedor e manual de produto — documentos que a empresa não quer
vazando nem expostos na internet. O Lab 1 já criou o RDS PostgreSQL
(`lab/terraform/rds.tf`), privado, e o Lab 1.1 já rodou
`scripts/criar_tabela.py`, que habilita a extensão `pgvector` e cria a
tabela `documentos_qc` — **isso não é feito pelo Terraform**, é SQL
direto, porque `pgvector` é uma extensão do banco, não um recurso da AWS.

No `entrega-grupo-aula04.md`, responda:

a) Abra `lab/terraform/rds.tf` — por que `manage_master_user_password = true`
   em vez de definir uma senha fixa? O que o Terraform mostra (ou não
   mostra) sobre essa senha depois do `apply`?
b) Abra `lab/terraform/network.tf` — por que a Lambda precisa de uma
   **subnet própria com rota pra um NAT Gateway**, e não basta colocar ela
   numa das subnets default da VPC? (Dica: pense em quem tem rota direta
   pra um Internet Gateway vs. quem precisa de NAT.)
c) O RDS é privado — não dá pra rodar `psql` direto do CloudShell (ver
   LAB 1.1 em `lab/guia-lab.md`). Depois do Exercício 2.2 abaixo, confirme
   via `curl "$API_URL/status"` (rota que roda de dentro da Lambda) e cole
   o `total_chunks` e `total_fontes` retornados.

### Exercício 2.2 — Ache o chunking que quebra a resposta certa

`lab/data/catalogo_qc.pdf` (página 2) tem uma tabela real de prazos por
categoria:

```
Categoria         | Prazo troca | Prazo defeito
Moveis            | 7 dias      | 90 dias
Eletronicos       | 7 dias      | 90 dias
Eletrodomesticos  | 7 dias      | 12 meses
```

Eletrodomésticos é a **exceção** da tabela (12 meses, não 90 dias). Se o
chunking cortar essa linha no meio ou juntar linhas de categorias
diferentes no mesmo chunk, o retrieval pode trazer o pedaço errado — e o
agente responde 90 dias pra um cliente que comprou um eletrodoméstico.
Isso é um bug de chunking virando uma resposta errada pra cliente.

a) Rode `/indexar` contra `catalogo_qc.pdf` e confirme via `curl
   "$API_URL/status"` que os chunks entraram na tabela.

b) Rode `/indexar` de novo, no MESMO documento — confirme que
   `chunks_indexados` vem **zero** na segunda vez (idempotência: veja a
   checagem de duplicata em `rota_indexar`, em
   `lab/lambda/lambda_function.py`).

c) Pergunte via `/perguntar`: **"Qual o prazo de troca por defeito de um
   eletrodoméstico?"** A resposta veio certa (12 meses) ou confundiu com
   90 dias? Cole a resposta e as fontes retornadas.

d) Abra `lab/lambda/lambda_function.py` e troque as constantes
   `TAMANHO_CHUNK` e `SOBREPOSICAO_CHUNK` (hoje `500`/`50`) por um valor
   BEM menor (ex.: `80`/`10` — pequeno o bastante pra cortar a tabela no
   meio de propósito) — reaplique só a Lambda:

   ```bash
   cd ~/aie-cloud/aulas/04-servicos-cognitivos-aws/lab/terraform
   terraform apply -auto-approve -var="gemini_api_key=$GEMINI_API_KEY"
   ```

   Reindexe num documento novo (a idempotência do item b pula o mesmo
   arquivo) e repita a pergunta do item c. Piorou, melhorou, ou não fez
   diferença? Por quê?

**Entrega:** a resposta da pergunta do item c com o chunking original, a
resposta com o chunking menor do item d, e sua explicação de por que o
tamanho do chunk afeta (ou não) a chance de responder errado sobre uma
exceção numa tabela — no `entrega-grupo-aula04.md`.

### Exercício 2.3 — Custo e escala

A QC quer indexar **500 mil produtos**, com descrição média de 200 caracteres cada.

a) Estime quantos chunks isso gera e o custo total de embeddings no modelo que você usou.
b) O índice `hnsw` (criado em `scripts/criar_tabela.py`) tem parâmetros
   (`m`, `ef_construction`) que trocam velocidade de indexação por
   qualidade de busca — hoje o script usa os valores padrão do Postgres.
   Pesquise o que cada parâmetro faz e proponha valores pra esse volume.
c) Em que ponto faria mais sentido migrar de RDS+pgvector pra um serviço de vector search dedicado (ex: OpenSearch)? Considere volume, latência e custo de RDS ocioso 24/7.

---

## 🔴 Nível 3 — Avançado: Estender o Endpoint de RAG (bônus)

### Exercício 3.1 — O endpoint aguenta o volume real da QC?

O endpoint `/perguntar` (`rota_perguntar` em
`lab/lambda/lambda_function.py`) já está no ar desde o Lab 1 — mas hoje só
foi testado com uma pergunta de cada vez. Antes de sugerir isso como tool
de um agente de atendimento da QC (que recebe milhares de conversas por
dia), o time de engenharia precisa saber o custo e a latência de verdade.
Sua tarefa: **instrumente** o código pra medir, e devolva no JSON de
resposta:

a) Latência de cada etapa — embedding da pergunta, busca no pgvector,
   geração da resposta (use `time.perf_counter()` em volta de cada
   chamada).
b) Rode 10 perguntas de teste e calcule a latência média e o custo por
   pergunta (tokens de embedding da pergunta + tokens de input/output da
   geração — a resposta do Gemini traz contagem de tokens em
   `usageMetadata`, se disponível).
c) Compare: se a QC receber 100 mil perguntas/mês nesse endpoint, esse
   volume ainda cabe no free tier do Gemini, ou passaria pro tier pago?
   Qual o custo mensal estimado (chamadas ao modelo + o NAT Gateway
   rodando 24/7)?

### Exercício 3.2 — Bônus extra: o que o jurídico da QC pediria

Escolha **um** e implemente em `rota_perguntar`:

- **Citação verificável (o mais pedido pelo jurídico/compliance):** se um
  cliente contesta uma resposta do agente, a QC precisa mostrar exatamente
  de qual documento/página ela veio — "confiar no que o modelo disse" não
  é auditável. Faça o prompt pedir que o modelo cite explicitamente de
  qual chunk (ex.: `[fonte p.N]`) cada afirmação da resposta veio, não só
  listar as fontes num campo separado.
- **Reranking:** o time de atendimento reclama que, às vezes, a resposta
  usa um chunk pouco relevante em vez do certo (o problema do Exercício
  2.2, em maior escala). Troque `LIMIT %s` (hoje `TOP_K = 5`, direto do
  pgvector) por uma busca mais ampla (top-20) seguida de um segundo passo
  de reordenação (ex: o próprio Gemini pontuando relevância de cada chunk)
  e mantenha só os top-5 antes de montar o prompt final.
- **Streaming:** pra um chat de atendimento ao vivo, esperar a resposta
  inteira antes de mostrar qualquer coisa piora a experiência do cliente.
  Faça a Lambda retornar a resposta em streaming (Lambda response
  streaming + API Gateway) em vez de esperar a resposta completa do
  Gemini.

Documente qual você escolheu, o código alterado, e por que esse era o
problema mais urgente pra QC resolver primeiro — no `entrega-grupo-aula04.md`.

### Exercício 3.3 — O orçamento de infraestrutura da QC

Releia o comentário no topo de `lab/terraform/network.tf` sobre o NAT
Gateway. Ele existe só porque a QC decidiu usar o Gemini (externo à AWS)
em vez do Bedrock — uma decisão de arquitetura com custo mensal recorrente,
não uma taxa única. Compare o custo mensal de um NAT Gateway (~US$0,045/h
+ US$0,045/GB) rodando 24/7 com o custo de simplesmente reduzir o volume
de chamadas externas (ex.: cache de respostas repetidas, ou — se a conta
da QC um dia liberar — trocar pra um provedor acessível via VPC Endpoint).
Pra um endpoint de baixo tráfego, qual estratégia você recomendaria pro
time de FinOps da QC?

---

## Wrap-up — Destroy obrigatório

```bash
cd ~/aie-cloud/aulas/04-servicos-cognitivos-aws/lab/terraform
terraform destroy -auto-approve -var="gemini_api_key=$GEMINI_API_KEY"
```

> **Atenção especial ao RDS e ao NAT Gateway:** diferente de Lambda/S3, uma instância RDS parada ainda cobra armazenamento, uma instância RODANDO cobra por hora mesmo sem uso, e um NAT Gateway esquecido ligado cobra por hora e por GB. Confirme que `aws_db_instance.rag` e `aws_nat_gateway.saida_gemini` foram removidos de verdade (`aws rds describe-db-instances` / `aws ec2 describe-nat-gateways`) — são os dois recursos mais caros desta aula se esquecidos ligados.

---

## Critérios de entrega

A entrega é **um ZIP por grupo** (`entrega-grupo-NN-aula04.zip`) no Portal FIAP. Estrutura completa, prazo e dicas de geração do ZIP em [entregas/entrega-04/INSTRUCOES.md](../../entregas/entrega-04/INSTRUCOES.md).

| Item | Obrigatório? | Pontos máximos |
|------|--------------|-----------------|
| Cabeçalho do grupo + distribuição do trabalho | ✅ Sim | 1 pt (Critério 4) |
| 🟢 N1 — Atividade 0 (lab no ar) + 1.1 (PDF próprio), 1.2 (leitura de código), 1.3 (reflexão OCR vs LLM) | ✅ Sim | 3 pts (Critério 1) |
| 🟡 N2 — 2.1 (entender o banco/rede), 2.2 (chunking vs. resposta certa), 2.3 (custo/escala) | ✅ Sim | 3 pts (Critério 2) + 2 pts qualidade técnica (Critério 3) |
| 🔴 N3 — 3.1 (métricas de volume), 3.2 (bônus: citação/reranking/streaming), 3.3 (orçamento de rede) | 🎁 Bônus | até +2 pts extras |
| Reflexão coletiva ao final | ✅ Sim | 1 pt (Critério 5) |
| **Total da entrega** | | **10 pts** (10% da nota final) |

**Prazo:** 1 dia antes da Aula 5.
**Onde:** upload do ZIP no Portal FIAP. Apenas 1 membro do grupo faz o upload.
