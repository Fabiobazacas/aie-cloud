# Como rodar cada exercício no AWS CloudShell

Guia rápido e direto para a Aula 7 (AWS). Para a explicação conceitual de cada
etapa, veja o [lab/guia-lab.md](lab/guia-lab.md); aqui só estão os comandos, o
que esperar de cada um e o que fazer quando algo dá errado.

---

## 0. Antes de começar

| O que | Onde conseguir | Observação |
|-------|----------------|------------|
| Sessão do **AWS Academy Learner Lab** ativa | Painel do curso → Start Lab | O CloudShell usa a role da sessão automaticamente |
| **Chave do Gemini** (`GEMINI_API_KEY`) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Gratuita, sem cartão. **Uma por grupo** |
| **Token do Hugging Face** (`HF_TOKEN`) | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → New token → tipo **Read** | Gratuito. **Um por grupo.** Necessário para o Ex05 (imagem) e o Desafio (3D) |

> **Limites das contas gratuitas**
> - **Gemini (free tier):** não tem cota de **geração de imagem**; texto, visão, áudio e embeddings funcionam.
> - **Hugging Face (conta gratuita):** os Spaces usam GPU compartilhada (ZeroGPU) com cota diária pequena (alguns minutos). Cada edição de imagem usa ~1 min e cada modelo 3D ~2 min. **Não repita o teste à toa** e use um token por grupo. Sem token, a cota anônima acaba na primeira ou segunda chamada.

---

## 1. Preparar o CloudShell (uma vez por sessão)

Abra o CloudShell (ícone `>_` na barra superior do console AWS, região **us-east-1**) e rode:

```bash
# 1) chaves do grupo (só nesta sessão — não vão para nenhum arquivo)
export GEMINI_API_KEY="cole-a-chave-do-gemini"
export HF_TOKEN="cole-o-token-do-hugging-face"

# 2) repositório
rm -rf aie-cloud
git clone https://github.com/fabiobazacas/aie-cloud.git
cd aie-cloud/aulas/07-function-aws/lab/terraform

# 3) Terraform (se ainda não existir)
command -v terraform >/dev/null || {
  curl -sSL -o /tmp/tf.zip https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip
  unzip -o /tmp/tf.zip -d ~/bin && export PATH=$HOME/bin:$PATH
}
terraform -version

# 4) evita "no space left on device" (o $HOME do CloudShell tem só ~1 GB)
export TF_DATA_DIR=/tmp/tf-data-aula7 && mkdir -p $TF_DATA_DIR
```

---

## 2. Subir a infraestrutura

```bash
cd ~/aie-cloud/aulas/07-function-aws/lab/terraform
terraform init

terraform apply -auto-approve \
  -var="gemini_api_key=$GEMINI_API_KEY" \
  -var="hf_token=$HF_TOKEN"
```

| Quer fazer... | Use |
|---------------|-----|
| **Tudo** (Ex01–Ex05 + Desafio) | o comando acima (~15 min — o RDS é o gargalo) |
| **Só Ex03, Ex04, Ex05 e Desafio** | acrescente `-var="habilitar_rag=false"` (~2 min, sem RDS e sem NAT Gateway) |

Depois do `apply`, guarde as variáveis usadas em todos os exercícios:

```bash
export API_URL=$(terraform output -raw api_gateway_url)
export BUCKET=$(terraform output -raw bucket)
echo "$API_URL  $BUCKET"

curl -s "$API_URL/health"        # {"service":"ex01-chunker","status":"ok"}
```

> Se o `curl` devolver `{"message":"Service Unavailable"}` logo no começo, espere ~30 s e repita: é a Lambda em VPC anexando a rede pela primeira vez.

### Como acompanhar um job assíncrono

`/process`, `/ner` e `/campaign` respondem na hora com `202` e um `job_id`
(a API Gateway corta qualquer chamada em 30 s). O resultado aparece no S3:

```bash
aws s3 cp s3://$BUCKET/jobs/<JOB_ID>.json -
# {"status":"running"}  ->  repita até virar  {"status":"ok", ...}  ou  {"status":"erro", ...}
```

Logs de qualquer função (troque o nome pelo da saída de `terraform output lambdas`):

```bash
terraform output lambdas
aws logs tail /aws/lambda/aula2-ex01_chunker-<SUFIXO> --follow
```

---

## 3. Exercício 01 — Chunking semântico + indexação (RDS/pgvector)

Lê o PDF escaneado do S3, faz OCR com o Gemini, quebra em chunks por significado, gera embeddings e grava no PostgreSQL com pgvector.

```bash
curl -s -X POST "$API_URL/process" \
  -H "Content-Type: application/json" \
  -d '{"bucket_key": "documents/matricula.pdf"}'
# -> 202 {"status":"accepted","job_id":"..."}

aws s3 cp s3://$BUCKET/jobs/<JOB_ID>.json -
```

**Esperado:** `"status": "ok"`, `"total_chunks"` (em torno de 5) e `"indexed": true`.

Conferir:

```bash
aws s3 cp s3://$BUCKET/chunks/matricula/chunks.json - | head -40   # chunks no S3
curl -s "$API_URL/rag/chunks"                                      # chunks no pgvector
```

Tempo: ~30–90 s (OCR de 5 páginas + embeddings).
Precisa de `habilitar_rag=true`.

---

## 4. Exercício 02 — RAG (pergunta → resposta com fonte)

Depende do Ex01 (os chunks precisam estar indexados).

```bash
curl -s -X POST "$API_URL/rag/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Quem é o proprietário do imóvel?"}'
```

**Esperado:** `answer` com a resposta, `confidence`, `sources` (de qual chunk veio) e `chunks_scores`.

Teste também uma pergunta **fora** do documento:

```bash
curl -s -X POST "$API_URL/rag/query" -H "Content-Type: application/json" \
  -d '{"question": "Qual a capital da França?"}'
```

**Esperado:** `"found_in_context": false` e a mensagem "Não encontrei essa informação...".

Resposta síncrona (~3–8 s).

---

## 5. Exercício 03 — NER + DynamoDB

Extrai entidades estruturadas (matrícula, proprietários, ônus, averbações) do documento.

```bash
curl -s -X POST "$API_URL/ner" \
  -H "Content-Type: application/json" \
  -d '{"bucket_key": "documents/matricula.pdf"}'

aws s3 cp s3://$BUCKET/jobs/<JOB_ID>.json -
```

**Esperado:** `"status": "ok"`, `entities_path` e `dynamodb_id`.

Conferir:

```bash
aws s3 cp s3://$BUCKET/entities/matricula/entities.json - | head -60
aws dynamodb scan --table-name $(terraform output -raw dynamodb_entities) --max-items 1
```

---

## 6. Exercício 04 — Transcrição de áudio + avaliação de atendimento

```bash
curl -s -X POST "$API_URL/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"bucket_key": "audios/test_audio.wav"}'
```

**Esperado (síncrono, ~10 s):** `transcription` (começo da fala), `analysis_path` e `dynamodb_id`.

Conferir a avaliação completa:

```bash
aws s3 cp s3://$BUCKET/transcriptions/test_audio/analysis.json - | head -60
aws dynamodb scan --table-name $(terraform output -raw dynamodb_transcriptions) --max-items 1
```

O áudio vai direto ao Gemini (limite ~14 MB por arquivo).

---

## 7. Exercício 05 — Campanha de marketing (image-to-image)

O Gemini lê a **embalagem** e cria a campanha (nome, slogan, textos, hashtags e um prompt de cena **ambientado no tema impresso na embalagem**). Depois a foto do produto é editada em modo **image-to-image** num Space do Hugging Face (FLUX.1 Kontext), preservando o produto.

```bash
curl -s -X POST "$API_URL/campaign" \
  -H "Content-Type: application/json" \
  -d '{"bucket_key": "images/sabonete.png"}'

aws s3 cp s3://$BUCKET/jobs/<JOB_ID>.json -
```

**Esperado:** `"status": "ok"`, `"image_source": "hf"` (ou `"gemini"` se a sua chave tiver cota de imagem) e `generated_image` preenchido.

```bash
aws s3 ls s3://$BUCKET/campaigns/sabonete/
aws s3 cp s3://$BUCKET/campaigns/sabonete/campaign.json - | head -60
```

**Ver a imagem:** no CloudShell, menu **Actions → Download file** e informe o caminho depois de copiar:

```bash
aws s3 cp s3://$BUCKET/campaigns/sabonete/campaign_image.webp ~/campaign_image.webp
```

(ou abra o `generated_image_url` do resultado do job — expira em 1 hora e só funciona com a sessão do Lab ativa).

Outras imagens de exemplo: `images/tenis.jpg`, `images/R.png`.

Se `generated_image` vier vazio, leia `image_error`: normalmente é a **cota diária do Hugging Face** (`exceeded your ZeroGPU quota`). A campanha em texto continua sendo entregue. Aguarde a cota renovar ou use o token de outro membro do grupo.

---

## 8. Desafio — Imagem 2D → modelo 3D (event-driven)

Aqui você **não chama a API**: fazer upload de uma imagem no prefixo `images-3d/` dispara a Lambda sozinha, via S3 Event Notification.

```bash
# copia uma imagem de exemplo para o prefixo que dispara o evento
aws s3 cp s3://$BUCKET/images/tenis.jpg s3://$BUCKET/images-3d/tenis.jpg

# acompanhe (leva 1–5 min: fila + GPU do Space TRELLIS)
aws logs tail /aws/lambda/$(terraform output -json lambdas | python3 -c "import sys,json;print(json.load(sys.stdin)['desafio_3d'])") --follow
```

Quando terminar (Ctrl+C para sair dos logs):

```bash
aws s3 ls s3://$BUCKET/models3d/tenis/          # model.glb + metadata.json  (ou error.json)
aws s3 cp s3://$BUCKET/models3d/tenis/model.glb ~/model.glb
```

Baixe pelo CloudShell (**Actions → Download file**) e visualize em [gltf-viewer.donmccurdy.com](https://gltf-viewer.donmccurdy.com/).

Dicas: use **um objeto com fundo limpo**; se aparecer `error.json`, leia o motivo (cota do ZeroGPU, Space fora do ar, fila cheia).

---

## 9. Encerrar — obrigatório

```bash
cd ~/aie-cloud/aulas/07-function-aws/lab/terraform
terraform destroy -auto-approve \
  -var="gemini_api_key=$GEMINI_API_KEY" \
  -var="hf_token=$HF_TOKEN"
```

Confirme que o que mais custa sumiu (RDS e NAT Gateway cobram por hora mesmo sem uso):

```bash
aws rds describe-db-instances --query 'DBInstances[].DBInstanceIdentifier'
aws ec2 describe-nat-gateways --filter Name=state,Values=available --query 'NatGateways[].NatGatewayId'
```

Se tiver aplicado com `habilitar_rag=false`, repita o mesmo `-var` no `destroy`.

---

## 10. Problemas comuns

| Sintoma | Causa / o que fazer |
|---------|---------------------|
| `no space left on device` | Faltou o passo 4 do item 1 (`TF_DATA_DIR` em `/tmp`). Rode-o e repita `terraform init`. |
| `AccessDenied` / `ExpiredToken` | A sessão do Learner Lab expirou. Reinicie o Lab e reabra o CloudShell. |
| `Service Unavailable` na 1ª chamada de Ex01/Ex02 | Lambda em VPC ainda criando a rede. Espere ~30 s. |
| `Gemini respondeu 429` | Rate limit do free tier. Confirme que o grupo usa a **própria** chave e espere 1 min. |
| `Gemini respondeu 404` | Modelo aposentado. Liste os da sua chave: `curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"` e ajuste `MODELO_TEXTO` em `lab/shared/gemini.py`. |
| `exceeded your ZeroGPU quota` (Ex05/Desafio) | Cota diária gratuita do Hugging Face acabou. Aguarde ou use outro token. |
| Job fica `"running"` para sempre | A Lambda estourou o timeout. Veja `aws logs tail ...` e procure `Task timed out`. |
| `terraform destroy` fica 10–30 min "Still destroying" em `aws_subnet` / `aws_security_group` | **Normal.** As Lambdas de RAG (Ex01/Ex02) ficam numa VPC e a AWS demora a liberar as interfaces de rede delas depois que as funções são apagadas. Não cancele: espere. Se estourar o timeout, rode o mesmo `terraform destroy` de novo. |
| `archive_file` reclama de diretório de build | O `/tmp` do CloudShell foi limpo. Rode `terraform destroy` e depois `apply` de novo. |
| Space do Hugging Face fora do ar | Troque pelo nome de outro Space compatível: `-var="hf_edit_space=..."` (Ex05) ou `-var="trellis_space=..."` (Desafio). |
