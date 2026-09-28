# Exercícios — Aula 4 (AWS): Pipeline de RAG

**Tema:** RAG (Retrieval-Augmented Generation) — do PDF ao endpoint
**Formato:** **Entrega obrigatória por grupo** — ZIP no Portal FIAP
**Vale:** 10% da nota final ([rubrica completa](../../entregas/rubrica.md))
**Prazo:** 1 dia antes da Aula 5
**Como entregar:** ver [entregas/entrega-04/INSTRUCOES.md](../../entregas/entrega-04/INSTRUCOES.md)

---

## Instruções gerais

Ao contrário das aulas anteriores, aqui **não existe um lab guiado em sala separado dos exercícios** — o exercício **é** o lab. Os 3 níveis constroem, em sequência, um pipeline de RAG completo: um PDF vira texto, o texto vira vetores, os vetores ficam pesquisáveis, e um endpoint Lambda responde perguntas com base neles.

- 🟢 **Nível 1 — Básico:** ingestão do PDF e transcrição via LLM multimodal (Google Gemini — ver Atividade 0)
- 🟡 **Nível 2 — Intermediário:** chunking, embeddings e banco vetorial (RDS + pgvector)
- 🔴 **Nível 3 — Avançado:** **bônus opcional** — endpoint Lambda de RAG completo, com métricas de custo/latência

**Mínimo obrigatório:** N1 + N2 cobertos. **N3 é bônus** (até +2 pts extras).

### Distribuição entre membros (sugerida)

- Iniciantes: N1 — ingestão e transcrição
- Intermediários: N2 — chunking, embeddings, pgvector
- Experientes: N3 — Lambda de RAG + VPC/networking

> **Rodízio:** quem fez N1 nas Aulas 1-3 deve assumir N2 ou N3 agora.

### Template obrigatório

Use o [template em `entregas/template-entrega-grupo.md`](../../entregas/template-entrega-grupo.md) para o `entrega-grupo-aula04.md` dentro do ZIP.

> **Política "no install":** Tudo no AWS CloudShell (que já tem Docker e AWS CLI — só falta instalar o Terraform, como nas aulas anteriores).

---

## Atividade 0 — Crie sua chave gratuita do Google Gemini (faça isso primeiro)

**Já confirmamos, numa sessão real do AWS Academy Learner Lab, que o Bedrock
não é liberado nesta conta** — `aws bedrock list-foundation-models` devolve
`AccessDeniedException` por **falta de policy** (não é questão de habilitar
um modelo específico no console; a API inteira está fora da permissão da
sessão). Se quiser confirmar isso na sua própria conta:

```bash
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[].modelId" --output table
```

Por isso este pipeline usa **Google Gemini** como provedor padrão — free
tier sem cartão de crédito, cobre visão (transcrição), texto (geração) e
embeddings num único provedor:

1. Cada **grupo** cria sua própria chave em
   [aistudio.google.com/apikey](https://aistudio.google.com/apikey) (login
   com conta Google, ~2 minutos, sem cartão).
2. **Não compartilhe a chave entre grupos** — o rate limit do free tier é
   por chave; se a turma inteira usar a mesma chave ao mesmo tempo, todo
   mundo toma `429 Too Many Requests`.
3. No CloudShell, exporte a chave (vale só pro terminal atual — refaça se
   abrir um terminal novo):
   ```bash
   export GEMINI_API_KEY="sua-chave-aqui"
   ```
4. Teste com uma chamada simples:
   ```bash
   curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$GEMINI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"responda só OK"}]}]}'
   ```

> **Se a sua conta do Academy for uma exceção e liberar Bedrock de
> verdade**, nada impede de usar `bedrock-runtime`/Titan Embeddings em vez
> de Gemini nos scripts abaixo — a arquitetura (S3, RDS/pgvector, Lambda,
> API Gateway) não muda, só o transporte da chamada ao modelo. Mas o padrão
> deste material, a partir daqui, é Gemini.

**✅ Checkpoint:** o `curl` acima devolve um JSON com `"text": "OK"` (ou parecido) dentro de `candidates`? Guarde a `GEMINI_API_KEY` — vai precisar dela nos exercícios seguintes.

---

## 🟢 Nível 1 — Básico: Ingestão e Transcrição via LLM

### Exercício 1.1 — Provisionar o bucket e subir o PDF

Crie um bucket S3 pra esta aula (pode reaproveitar o padrão de `random_string.sufixo` das aulas anteriores) e suba um PDF de teste — pode ser um manual de produto, uma política de troca fictícia da QC, ou qualquer PDF de 3-10 páginas que você tenha à mão (inclusive um PDF **escaneado/só-imagem**, sem camada de texto — é justamente o caso que o OCR tradicional erra e o LLM multimodal resolve bem).

```hcl
resource "aws_s3_bucket" "rag_docs" {
  bucket = "qc-rag-docs-${random_string.sufixo.result}"
}
```

> Lembrete do que já vimos na Aula 3: não use o recurso `aws_s3_bucket` puro se a leitura dele disparar `GetBucketObjectLockConfiguration` e a `LabRole` negar — se acontecer de novo aqui, aplique a mesma solução (criar o bucket via CLI num `null_resource`).

### Exercício 1.2 — Transcrever o PDF com um LLM multimodal

Em vez de Textract ou Tesseract, transcreva cada página do PDF **enviando a imagem da página pra um modelo com visão** (Google Gemini, ver Atividade 0). Isso é o que a indústria vem chamando de "LLM-based OCR" — funciona melhor que OCR tradicional em documentos com tabelas, formatação irregular ou baixa qualidade de digitalização.

Passo a passo do script (`transcrever_pdf.py`):

```python
import base64
import os

import fitz  # PyMuPDF — pip install pymupdf
import requests  # pip install requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]  # criada na Atividade 0
MODEL_ID = "gemini-2.0-flash"  # confira o nome atual em ai.google.dev/gemini-api/docs/models
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent"


def pagina_para_base64_png(pagina, zoom=2.0):
    pix = pagina.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")


def transcrever_pagina(imagem_b64: str) -> str:
    corpo = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/png", "data": imagem_b64}},
                {"text": "Transcreva TODO o texto visível nesta página, na ordem de leitura. Preserve tabelas como texto estruturado. Não resuma, não comente — só a transcrição."},
            ]
        }],
        "generationConfig": {"maxOutputTokens": 2000},
    }
    resp = requests.post(URL, params={"key": GEMINI_API_KEY}, json=corpo, timeout=30)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def transcrever_pdf(caminho_pdf: str) -> list[str]:
    doc = fitz.open(caminho_pdf)
    paginas_texto = []
    for pagina in doc:
        img_b64 = pagina_para_base64_png(pagina)
        paginas_texto.append(transcrever_pagina(img_b64))
    return paginas_texto


if __name__ == "__main__":
    textos = transcrever_pdf("catalogo_qc.pdf")
    for i, texto in enumerate(textos, 1):
        print(f"--- Página {i} ---\n{texto}\n")
```

> Se sua conta liberar Bedrock de verdade, o equivalente é
> `bedrock.invoke_model(modelId="anthropic.claude-3-haiku-...", body=...)`
> com `{"type": "image", "source": {...}}` no lugar de `inline_data` — mesma
> ideia, formato de payload diferente.

Rode isso no CloudShell (`pip install --user pymupdf requests` primeiro) contra o seu PDF de teste.

**✅ Checkpoint L₁:** o script imprime a transcrição de cada página? Salve o resultado — o Exercício 2.2 usa esse texto.

### Exercício 1.3 — Reflexão: LLM de visão vs OCR tradicional

Responda no `entrega-grupo-aula04.md`:

a) Cite 2 cenários onde OCR tradicional (Textract, Tesseract) ainda ganha do LLM de visão em custo, e 2 onde o LLM de visão ganha em qualidade.
b) O prompt do Exercício 1.2 pede pra "não resumir, não comentar". O que acontece com o pipeline de RAG se o modelo resumir a página em vez de transcrever? Por que isso é um problema pra retrieval?
c) Estime o custo de transcrever os **200 catálogos de fornecedores da QC** (~15 páginas cada, em média) com o modelo que você usou. Confira se seu volume ainda cabe no free tier do Gemini (rate limit por minuto/dia) ou se passaria pro tier pago — use a [página de pricing do Gemini API](https://ai.google.dev/gemini-api/docs/pricing) pra estimar o custo além do free tier.

---

## 🟡 Nível 2 — Intermediário: Chunking, Embeddings e pgvector

### Exercício 2.1 — Provisionar RDS PostgreSQL com pgvector

```hcl
resource "aws_db_instance" "rag_db" {
  identifier             = "qc-rag-db-${random_string.sufixo.result}"
  engine                 = "postgres"
  engine_version         = "16.4"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  db_name                = "ragdb"
  username               = "ragadmin"
  manage_master_user_password = true  # senha gerada e guardada no Secrets Manager — sem senha hardcoded
  publicly_accessible    = false
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.rag_db.id]
}

resource "aws_security_group" "rag_db" {
  name   = "qc-rag-db-${random_string.sufixo.result}"
  vpc_id = data.aws_vpc.default.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.rag_lambda.id]  # só a Lambda do Exercício 3.1 acessa — ver mais abaixo
  }
}

data "aws_vpc" "default" {
  default = true
}
```

> `manage_master_user_password = true` deixa o RDS criar e guardar a senha no **Secrets Manager** automaticamente — sem senha em variável nem hardcoded. `terraform output` não vai mostrar a senha; leia-a com `aws secretsmanager get-secret-value` usando o ARN que o Terraform expõe em `aws_db_instance.rag_db.master_user_secret[0].secret_arn`.

Depois do `apply` (lembre: RDS demora ~10-15 min), conecte via CloudShell (`psql`, já vem instalado) e habilite a extensão:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documentos_qc (
    id SERIAL PRIMARY KEY,
    fonte TEXT NOT NULL,
    pagina INT NOT NULL,
    chunk_texto TEXT NOT NULL,
    embedding VECTOR(768)  -- dimensão do text-embedding-004 do Gemini; ajuste se usar outro modelo
);

CREATE INDEX ON documentos_qc USING hnsw (embedding vector_cosine_ops);
```

### Exercício 2.2 — Chunking e embeddings

O texto transcrito no Exercício 1.2 precisa ser dividido em **chunks** antes de virar embedding — um LLM de embeddings não deveria receber uma página inteira sem critério.

a) Implemente uma função de chunking simples (por parágrafo ou por tamanho fixo com overlap, ex: 500 caracteres com 50 de overlap).

b) Para cada chunk, gere o embedding via Gemini (`text-embedding-004`):

```python
def gerar_embedding(texto: str) -> list[float]:
    resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent",
        params={"key": GEMINI_API_KEY},
        json={"content": {"parts": [{"text": texto}]}},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]  # lista de 768 floats
```

c) Insira cada chunk + embedding na tabela `documentos_qc` (via `psycopg2`, usando a senha do Secrets Manager do Exercício 2.1).

d) **Reflexão:** teste 2 estratégias de chunking diferentes (ex: 300 vs 800 caracteres) no mesmo documento. Faça uma busca por similaridade manual (`SELECT ... ORDER BY embedding <=> '[...]' LIMIT 3`) com uma pergunta de teste nas duas versões. Qual trouxe chunks mais úteis? Por quê?

**Entrega:** código de chunking + inserção, e a tabela `documentos_qc` populada (screenshot de um `SELECT COUNT(*)` no `entrega-grupo-aula04.md`).

### Exercício 2.3 — Custo e escala

A QC quer indexar **500 mil produtos**, com descrição média de 200 caracteres cada.

a) Estime quantos chunks isso gera e o custo total de embeddings no modelo que você usou.
b) O índice `hnsw` do Exercício 2.1 tem parâmetros (`m`, `ef_construction`) que trocam velocidade de indexação por qualidade de busca. Pesquise o que cada um faz e proponha valores pra esse volume.
c) Em que ponto faria mais sentido migrar de RDS+pgvector pra um serviço de vector search dedicado (ex: OpenSearch)? Considere volume, latência e custo de RDS ocioso 24/7.

---

## 🔴 Nível 3 — Avançado: Endpoint Lambda de RAG (bônus)

### Exercício 3.1 — A Lambda de RAG

Construa uma Lambda + API Gateway com uma rota `/perguntar` que implementa o ciclo completo de RAG:

1. Recebe `{"pergunta": "..."}` no body.
2. Gera o embedding da pergunta (Gemini `text-embedding-004` — mesmo modelo do Exercício 2.2, embeddings de perguntas e documentos **precisam** vir do mesmo modelo).
3. Busca os top-k chunks mais similares no `documentos_qc` (RDS/pgvector).
4. Monta um prompt com a pergunta + os chunks recuperados como contexto.
5. Chama um modelo de texto do Gemini (`gemini-2.0-flash`) pra responder **só com base no contexto fornecido**.
6. Retorna `{"resposta": "...", "fontes": [{"fonte": ..., "pagina": ...}, ...]}`.

**Sobre a Lambda estar numa VPC:** como o RDS não é público (`publicly_accessible = false`, correto — nunca exponha um banco), a Lambda **precisa estar na mesma VPC** pra alcançá-lo:

```hcl
resource "aws_lambda_function" "rag_query" {
  # ... demais argumentos ...
  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.rag_lambda.id]
  }
}

resource "aws_security_group" "rag_lambda" {
  name   = "qc-rag-lambda-${random_string.sufixo.result}"
  vpc_id = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
```

> **Ponto de atenção real (não é detalhe cosmético):** uma Lambda dentro de uma VPC **não tem acesso à internet por padrão** — só alcança o que está na própria VPC (como o RDS), a menos que a subnet tenha rota pra um **NAT Gateway**.
>
> Se sua Lambda chamasse o **Bedrock**, a solução mais barata seria um **VPC
> Interface Endpoint** pra `com.amazonaws.<região>.bedrock-runtime` (sem
> custo de NAT Gateway) — mas isso só funciona pra **serviços da própria
> AWS**. O **Gemini é uma API externa** (`generativelanguage.googleapis.com`),
> então essa opção não existe aqui: a Lambda **precisa de um NAT Gateway**
> pra alcançar a internet de dentro da VPC.
>
> Isso é um custo real que o desenho original (100% dentro da AWS, via
> Bedrock) evitava e que o fallback pra uma API externa introduz — cobra por
> hora **e** por GB trafegado. Para o volume de um lab, o custo é pequeno,
> mas é o tipo de coisa que muda a conta em produção. Adicione o NAT Gateway
> no Terraform (`aws_nat_gateway` + rota na tabela de rotas da subnet
> privada) e teste antes de assumir que "devia funcionar".
>
> **Reflexão:** compare o custo mensal de um NAT Gateway (~$0,045/h + $0,045/GB)
> rodando 24/7 com o custo de simplesmente reduzir o volume de chamadas
> externas (ex.: cache de respostas repetidas). Pra um endpoint de baixo
> tráfego, qual estratégia você recomendaria pra QC?

### Exercício 3.2 — Métricas de custo e latência

Rode 10 perguntas de teste contra o endpoint e meça:

a) Latência ponta a ponta (embedding da pergunta + busca pgvector + geração da resposta) — quebre por etapa.
b) Custo por pergunta (tokens de embedding da pergunta + tokens de input/output do modelo de geração).
c) Compare: se a QC receber 100 mil perguntas/mês nesse endpoint, esse volume ainda cabe no free tier do Gemini, ou passaria pro tier pago? Qual o custo mensal estimado (chamadas ao modelo + o NAT Gateway rodando 24/7)?

### Exercício 3.3 — Bônus extra

Escolha **um**:

- **Reranking:** depois de buscar top-20 no pgvector, reordene com um segundo passo (ex: um modelo de reranking, ou o próprio LLM pontuando relevância) e mantenha só os top-5 antes de montar o prompt final.
- **Streaming:** faça a Lambda retornar a resposta em streaming (Lambda response streaming + API Gateway) em vez de esperar a resposta completa do modelo.
- **Citação verificável:** faça o modelo de geração citar explicitamente de qual chunk cada afirmação da resposta veio (não só listar as fontes no fim).

Documente qual você escolheu e por quê no `entrega-grupo-aula04.md`.

---

## Wrap-up — Destroy obrigatório

```bash
terraform destroy -auto-approve
```

> **Atenção especial ao RDS:** diferente de Lambda/S3, uma instância RDS parada ainda cobra armazenamento, e uma instância RODANDO cobra por hora mesmo sem uso. Confirme no `terraform destroy` que o `aws_db_instance.rag_db` foi removido de verdade (ou confira `aws rds describe-db-instances` depois) — é o recurso mais caro dessa aula se esquecido ligado.

---

## Critérios de entrega

A entrega é **um ZIP por grupo** (`entrega-grupo-NN-aula04.zip`) no Portal FIAP. Estrutura completa, prazo e dicas de geração do ZIP em [entregas/entrega-04/INSTRUCOES.md](../../entregas/entrega-04/INSTRUCOES.md).

| Item | Obrigatório? | Pontos máximos |
|------|--------------|-----------------|
| Cabeçalho do grupo + distribuição do trabalho | ✅ Sim | 1 pt (Critério 4) |
| 🟢 N1 — Atividade 0 (chave do Gemini) + 1.1, 1.2, 1.3 | ✅ Sim | 3 pts (Critério 1) |
| 🟡 N2 — 2.1 (RDS + pgvector), 2.2 (chunking + embeddings), 2.3 (custo/escala) | ✅ Sim | 3 pts (Critério 2) + 2 pts qualidade técnica (Critério 3) |
| 🔴 N3 — 3.1 (Lambda de RAG), 3.2 (métricas), 3.3 (bônus escolhido) | 🎁 Bônus | até +2 pts extras |
| Reflexão coletiva ao final | ✅ Sim | 1 pt (Critério 5) |
| **Total da entrega** | | **10 pts** (10% da nota final) |

**Prazo:** 1 dia antes da Aula 5.
**Onde:** upload do ZIP no Portal FIAP. Apenas 1 membro do grupo faz o upload.
