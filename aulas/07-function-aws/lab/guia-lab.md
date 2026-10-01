# Guia de Laboratório — Aula 7 (AWS): Pipelines Cognitivos Serverless

**Tema:** Lambda + API Gateway + S3 + Gemini — do PDF ao modelo 3D
**Plataforma:** AWS Academy Learner Lab + Google Gemini (free tier)
**Ambiente:** **AWS CloudShell** — tudo no browser, sem instalar nada

---

## Visão geral do lab

```
Preparação — chave do Gemini + Terraform no CloudShell                  ~10 min
LAB 1 — Provisionamento (S3 + Lambdas + API + DynamoDB + RDS/NAT)       ~20 min (RDS é o gargalo)
LAB 2 — Ex01: chunking semântico + indexação no pgvector                ~15 min
LAB 3 — Ex02: RAG (pergunta -> resposta com fontes)                     ~10 min
LAB 4 — Ex03: NER de documento escaneado + DynamoDB                     ~10 min
LAB 5 — Ex04: transcrição de áudio + avaliação de atendimento           ~10 min
LAB 6 — Ex05: campanha de marketing (visão + image-to-image)            ~15 min
LAB 7 — Desafio: imagem 2D -> modelo 3D (event-driven)                  ~15 min
Wrap-up — terraform destroy + verificação de custo zero                 ~5 min
```

> **Regra de ouro:** sempre encerrar com `terraform destroy`. RDS e NAT
> Gateway são os recursos mais caros por hora — não deixe rodando de um dia
> pro outro.

> **Só vai fazer Ex03–Ex05 e o Desafio?** Pule o RDS: no LAB 1 use
> `-var="habilitar_rag=false"`. O deploy cai de ~15 para ~2 minutos e não
> cria NAT Gateway. Os LABs 2 e 3 (Ex01/Ex02) ficam indisponíveis.

---

## Preparação

### 1. Crie a chave gratuita do Gemini (uma por GRUPO)

Acesse [aistudio.google.com/apikey](https://aistudio.google.com/apikey), faça
login com uma conta Google, clique em **"Create API key"** → **"new project"**
(não pede cartão de crédito).

```bash
export GEMINI_API_KEY="sua-chave-aqui"
```

> **Não compartilhe a chave entre grupos** — o rate limit do free tier é por
> chave; se a turma inteira usar a mesma, todo mundo toma `429 Too Many
> Requests` no meio da aula.

### 1.1. Crie o token gratuito do Hugging Face (um por GRUPO)

O Ex05 (edição de imagem) e o Desafio (3D) rodam em **Spaces do Hugging Face**,
em GPU compartilhada (ZeroGPU). Crie um token em
[huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
(**New token → tipo Read**, gratuito):

```bash
export HF_TOKEN="seu-token-aqui"
```

> **Cota diária pequena.** Numa conta gratuita a GPU compartilhada rende só
> alguns minutos por dia: uma edição de imagem usa ~1 min e um modelo 3D ~2 min.
> Sem token a cota anônima acaba na primeira ou segunda chamada. Um token por
> grupo, e não repita o teste à toa.

### 2. Clonar o repositório e instalar o Terraform

```bash
rm -rf aie-cloud   # se já tiver clonado antes numa sessão anterior
git clone https://github.com/fabiobazacas/aie-cloud.git
cd aie-cloud/aulas/07-function-aws/lab/terraform

command -v terraform >/dev/null || {
  curl -sSL -o /tmp/tf.zip https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip
  unzip -o /tmp/tf.zip -d ~/bin && export PATH=$HOME/bin:$PATH
}
terraform -version
```

### 3. Evitar "no space left on device"

O `$HOME` do CloudShell tem só ~1 GB. O estado de trabalho do Terraform vai
para `/tmp`:

```bash
echo 'export TF_DATA_DIR=/tmp/tf-data-aula7' >> ~/.bashrc
export TF_DATA_DIR=/tmp/tf-data-aula7
mkdir -p $TF_DATA_DIR
```

---

## LAB 1 — Provisionamento (Terraform)

**Objetivo:** subir bucket S3 (já com os arquivos de exemplo), 6 Lambdas, a API
Gateway, 2 tabelas DynamoDB e — opcionalmente — o RDS com pgvector e a rede
(NAT Gateway).

```bash
cd ~/aie-cloud/aulas/07-function-aws/lab/terraform

terraform init
terraform apply -auto-approve \
  -var="gemini_api_key=$GEMINI_API_KEY" -var="hf_token=$HF_TOKEN"
# sem RAG (Ex03-Ex05 + Desafio, ~2 min): acrescente -var="habilitar_rag=false"
```

Enquanto espera, abra os `.tf` no VS Code (`code .`):

| Arquivo | O que define |
|---------|--------------|
| `main.tf` | Providers, sufixo aleatório, tags, nome do bucket |
| `variables.tf` | `gemini_api_key`, `habilitar_rag`, `hf_token`, ... |
| `iam.tf` | `data` source para a `LabRole` (nunca cria role nova) |
| `s3.tf` | Bucket (via CLI — ver comentário), upload dos arquivos de exemplo, **S3 Event Notification** do Desafio |
| `lambda.tf` | Build de cada Lambda (wheels manylinux) + as 6 funções, uma por exercício |
| `api.tf` | API Gateway HTTP API + rotas (o equivalente aos HTTP Triggers) |
| `dynamodb.tf` | Tabelas `entities` e `transcriptions` (o equivalente ao Cosmos DB) |
| `network.tf` / `rds.tf` | NAT Gateway, subnet das Lambdas de RAG, RDS PostgreSQL 16 (só com `habilitar_rag`) |
| `outputs.tf` | Valores usados nos passos seguintes |

Defina as variáveis usadas no resto do guia:

```bash
cd ~/aie-cloud/aulas/07-function-aws/lab/terraform
export API_URL=$(terraform output -raw api_gateway_url)
export BUCKET=$(terraform output -raw bucket)
echo $API_URL $BUCKET
aws s3 ls s3://$BUCKET --recursive      # confira: documents/, audios/, images/
```

**✅ Checkpoint L₁:** `curl "$API_URL/health"` devolve `{"service": "ex01-chunker", "status": "ok"}`?

> **A primeira chamada a uma Lambda em VPC (Ex01/Ex02) pode devolver
> `{"message":"Service Unavailable"}`.** É a API Gateway, não o nosso código
> (que sempre responde `{"erro": "..."}` quando falha): a AWS ainda está
> anexando a interface de rede (ENI) na subnet. Espere ~30 s e repita.

### Como funciona o modo assíncrono

A API Gateway corta qualquer requisição em **30 s**. Pipelines com OCR/LLM
passam disso — então `/process`, `/ner` e `/campaign` respondem **na hora**
com `202` e um `job_id`, e continuam rodando em segundo plano. O resultado
final aparece em `s3://$BUCKET/jobs/<job_id>.json`:

```bash
aws s3 cp s3://$BUCKET/jobs/<job_id>.json -      # {"status": "running"} -> "ok" ou "erro"
```

Para forçar o modo síncrono (só funciona se terminar em < 30 s), mande
`"async": false` no body. Acompanhe os logs de qualquer função com:

```bash
aws logs tail /aws/lambda/$(terraform output -json lambdas | python3 -c "import sys,json;print(json.load(sys.stdin)['ex01_chunker'])") --follow
```

---

## LAB 2 — Exercício 01: Chunking semântico + indexação

**Objetivo:** ler um PDF do S3, quebrar em chunks por significado (LLM),
gerar embeddings e indexar no pgvector.

> O `matricula.pdf` é um documento **escaneado, sem camada de texto**. O
> pipeline detecta isso e usa o Gemini como "OCR por LLM" (em paralelo, página
> a página) — leia `lab/shared/pdf.py`.

```bash
curl -s -X POST "$API_URL/process" \
  -H "Content-Type: application/json" \
  -d '{"bucket_key": "documents/matricula.pdf"}'
# {"status": "accepted", "job_id": "a1b2c3...", "consultar": "aws s3 cp ..."}

aws s3 cp s3://$BUCKET/jobs/<job_id>.json -       # repita até "status": "ok"
```

Resultado esperado:

```json
{
  "status": "ok",
  "resultado": {
    "bucket_key": "documents/matricula.pdf",
    "chunks_path": "chunks/matricula/chunks.json",
    "total_chunks": 8,
    "indexed": true
  }
}
```

Confira os dois destinos:

```bash
aws s3 cp s3://$BUCKET/chunks/matricula/chunks.json - | head -40   # chunks gerados
curl -s "$API_URL/rag/chunks"                                      # chunks no pgvector
```

**✅ Checkpoint L₂:** `/rag/chunks` lista os chunks e `chunks.json` existe no S3?

---

## LAB 3 — Exercício 02: RAG

**Objetivo:** responder perguntas **somente** com base nos chunks indexados.

```bash
curl -s -X POST "$API_URL/rag/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Quem é o proprietário do imóvel?"}'
```

A resposta traz `answer`, `confidence`, `sources` (de quais chunks veio) e
`chunks_scores` (o score de cada chunk recuperado). Teste também uma pergunta
**fora** do documento ("Qual a capital da França?") — o esperado é
`found_in_context: false`.

Abra `lab/shared/db.py`, função `busca_hibrida`: ela funde a busca vetorial
com a busca por palavra-chave (full-text do Postgres) usando **Reciprocal Rank
Fusion**.

**✅ Checkpoint L₃:** a pergunta sobre o proprietário foi respondida com fonte, e a pergunta fora do contexto foi recusada?

---

## LAB 4 — Exercício 03: NER + DynamoDB

**Objetivo:** extrair entidades estruturadas (matrícula, proprietários, ônus,
averbações...) do mesmo documento.

```bash
curl -s -X POST "$API_URL/ner" \
  -H "Content-Type: application/json" \
  -d '{"bucket_key": "documents/matricula.pdf"}'

aws s3 cp s3://$BUCKET/jobs/<job_id>.json -
aws s3 cp s3://$BUCKET/entities/matricula/entities.json - | head -60
aws dynamodb scan --table-name $(terraform output -raw dynamodb_entities) --max-items 1
```

Compare o item no DynamoDB com o JSON no S3: o mesmo dado, em dois lugares com
propósitos diferentes (arquivo de auditoria vs. consulta por chave).

**✅ Checkpoint L₄:** o item aparece na tabela DynamoDB com `documentName = matricula`?

---

## LAB 5 — Exercício 04: Transcrição + avaliação de atendimento

**Objetivo:** transcrever uma ligação e avaliar a qualidade do atendimento.

```bash
curl -s -X POST "$API_URL/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"bucket_key": "audios/test_audio.wav"}'

aws s3 cp s3://$BUCKET/transcriptions/test_audio/analysis.json - | head -60
aws dynamodb scan --table-name $(terraform output -raw dynamodb_transcriptions) --max-items 1
```

Aqui **não há** serviço dedicado de fala: o Gemini recebe o áudio direto
(base64) e transcreve. Veja `lab/lambda/ex04_speech/lambda_function.py`.

**✅ Checkpoint L₅:** a resposta traz `transcription` e `analysis_path`, e o JSON de análise tem `avaliacao.nota_geral`?

---

## LAB 6 — Exercício 05: Campanha de marketing

**Objetivo:** a partir da foto de um produto, criar uma campanha completa
(visão) e uma nova peça visual em **image-to-image**: o Gemini lê a embalagem e
descreve uma cena ambientada no tema impresso nela (ingredientes, frutas,
cores); depois um Space do Hugging Face (FLUX.1 Kontext) edita a foto do
produto para essa cena, **preservando o produto**.

```bash
curl -s -X POST "$API_URL/campaign" \
  -H "Content-Type: application/json" \
  -d '{"bucket_key": "images/sabonete.png"}'

aws s3 cp s3://$BUCKET/jobs/<job_id>.json -
aws s3 ls s3://$BUCKET/campaigns/sabonete/
aws s3 cp s3://$BUCKET/campaigns/sabonete/campaign.json - | head -60
```

O job leva ~1–2 min (visão + fila e GPU do Space). O resultado traz
`image_source` (`hf` ou `gemini`) e `generated_image`. Para ver a imagem:

```bash
aws s3 cp s3://$BUCKET/campaigns/sabonete/campaign_image.webp ~/campaign_image.webp
```

No CloudShell, **Actions → Download file**; ou abra o `generated_image_url`
(presigned URL) do resultado do job — expira em 1 hora e só funciona com a
sessão do Learner Lab ativa.

Compare a imagem com `data/images/sabonete.png` e leia o prompt de cena em
`campaign.json` (`image_generation.prompt`): as frutas e ingredientes da cena
vêm do que está **escrito e ilustrado na embalagem**.

> **Como a imagem é gerada.** `IMAGE_PROVIDERS` (padrão `gemini,hf`) define a
> ordem: o Gemini é tentado primeiro, mas o **free tier não tem cota de geração
> de imagem** (`429, limit: 0`), então na prática quem edita é o Space do
> Hugging Face (`shared/hf.py`). Com uma chave do Gemini com faturamento
> ativado, o Gemini passa a ser usado automaticamente.

> **Sem imagem?** Se `generated_image` vier vazio, leia `image_error`. O caso
> mais comum é `exceeded your ZeroGPU quota` (cota diária gratuita do Hugging
> Face): a campanha em texto continua sendo entregue; aguarde a cota renovar ou
> use o token de outro membro do grupo. Se o Space estiver fora do ar, aponte
> para outro compatível com `-var="hf_edit_space=<usuario/space>"`.

**✅ Checkpoint L₆:** `campaign.json` existe, tem `campanha.slogan` e `image_generation.prompt`, e `campaign_image.webp` foi gerada?

---

## LAB 7 — Desafio: imagem 2D → modelo 3D (event-driven)

**Objetivo:** subir uma imagem e deixar o **S3 disparar a Lambda sozinho** (nada
de chamar a API) — o "Blob Trigger" do laboratório original.

```bash
# copia uma imagem de exemplo para o prefixo que dispara o evento
aws s3 cp s3://$BUCKET/images/tenis.jpg s3://$BUCKET/images-3d/tenis.jpg

# acompanhe a Lambda (leva 1-5 min: fila + GPU do Space TRELLIS)
aws logs tail /aws/lambda/$(terraform output -json lambdas | python3 -c "import sys,json;print(json.load(sys.stdin)['desafio_3d'])") --follow

aws s3 ls s3://$BUCKET/models3d/tenis/        # model.glb + metadata.json (ou error.json)
aws s3 cp s3://$BUCKET/models3d/tenis/model.glb ~/model.glb
```

Visualize o `.glb` em [gltf-viewer.donmccurdy.com](https://gltf-viewer.donmccurdy.com/)
(baixe pelo CloudShell: **Actions → Download file**).

> **É um desafio.** O Space padrão é o `trellis-community/TRELLIS` (o
> `microsoft/TRELLIS` original está em `CONFIG_ERROR`, fora do ar). Ele roda em
> GPU compartilhada com fila e cota diária: um modelo 3D usa ~2 min da cota do
> seu token. Se aparecer `error.json`, leia a mensagem (cota do ZeroGPU, Space
> fora do ar, interface Gradio que mudou) — depurar é parte do exercício. Use
> imagens de **objeto único com fundo limpo**. Para trocar de Space:
> `-var="trellis_space=<usuario/space>"`.

**✅ Checkpoint L₇:** existe `models3d/<nome>/model.glb`?

---

## Wrap-up — Destroy obrigatório

```bash
cd ~/aie-cloud/aulas/07-function-aws/lab/terraform
terraform destroy -auto-approve \
  -var="gemini_api_key=$GEMINI_API_KEY" -var="hf_token=$HF_TOKEN"
# se aplicou com habilitar_rag=false, repita o mesmo -var no destroy
```

Confirme que o que mais custa sumiu de verdade:

```bash
aws rds describe-db-instances --query 'DBInstances[].DBInstanceIdentifier'
aws ec2 describe-nat-gateways --filter Name=state,Values=available --query 'NatGateways[].NatGatewayId'
aws s3 ls | grep aula2-cognitivo || echo "bucket removido"
```

---

## Troubleshooting

| Sintoma | Causa / solução |
|---------|-----------------|
| `no space left on device` no `apply` | Faltou o passo 3 da Preparação (`TF_DATA_DIR` em `/tmp`). Rode-o e repita `terraform init`. |
| `{"message":"Service Unavailable"}` na 1ª chamada de Ex01/Ex02 | Lambda em VPC ainda criando a ENI. Espere ~30 s. |
| `{"message":"Service Unavailable"}` **persistente** em Ex01/Ex02 | Lambda sem saída para a internet (NAT). Veja os logs; cheque `aws ec2 describe-nat-gateways`. |
| `Gemini respondeu 429` | Rate limit do free tier — confirme que o grupo usa a **própria** chave; espere 1 min. |
| `Gemini respondeu 404` | Modelo aposentado. Liste os da sua chave: `curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"` e ajuste `MODELO_TEXTO` em `lab/shared/gemini.py`. |
| `job` fica em `"running"` para sempre | A Lambda estourou o timeout — veja `aws logs tail` e procure `Task timed out`. |
| `archive_file`: diretório de build não existe | O `/tmp` do CloudShell foi limpo entre sessões. Force o rebuild: `terraform apply -replace='null_resource.lambda_build["ex01_chunker"]' ...` (repita para cada Lambda) ou rode `terraform destroy` + `apply`. |
| `terraform destroy` fica 10–30 min "Still destroying" em `aws_subnet` / `aws_security_group` | Normal: a AWS demora a liberar as interfaces de rede (ENIs) das Lambdas em VPC (Ex01/Ex02) depois que as funções são apagadas. Espere; se estourar o timeout, rode o `destroy` de novo. |
| `InvalidSubnet.Conflict` | Sobrou uma subnet de um apply anterior que falhou. Rode `terraform destroy`, confira `aws ec2 describe-subnets` e repita. |
| `AccessDenied` ao criar bucket / ler S3 | Credenciais do Learner Lab expiradas — copie de novo o **AWS Details** (os 3 valores, incluindo o session token). |
