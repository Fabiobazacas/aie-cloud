# Exercícios — Aula 3 (AWS)

**Tema:** Serverless & Containers — versão AWS Academy Learner Lab
**Formato:** **Entrega obrigatória por grupo** — ZIP no Portal FIAP
**Vale:** 10% da nota final ([rubrica completa](../../entregas/rubrica.md))
**Prazo:** 1 dia antes da Aula 4
**Como entregar:** ver [entregas/entrega-03/INSTRUCOES.md](../../entregas/entrega-03/INSTRUCOES.md)

> Versão adaptada dos exercícios de [../03-serverless-containers/exercicios.md](../03-serverless-containers/exercicios.md)
> para os serviços disponíveis no AWS Academy Learner Lab. Combine com seu
> grupo/professor qual das duas versões (Azure ou AWS) vale como entrega —
> não é para fazer as duas.

---

## Instruções gerais

Esta é a **3ª entrega de grupo** da disciplina. Os 3 níveis são **divisão de trabalho dentro do grupo**:

- 🟢 **Nível 1 — Básico:** serverless, IAM Role, Lambda vs Container, Dockerfile review
- 🟡 **Nível 2 — Intermediário:** segunda tool (cálculo de frete), CloudWatch/X-Ray e observabilidade, endurecimento/dimensionamento do Elastic Beanstalk
- 🔴 **Nível 3 — Avançado:** **bônus opcional** — spec de tool para agente AI, benchmark de carga, CI/CD com GitHub Actions

**Mínimo obrigatório:** N1 + N2 cobertos. **N3 é bônus** (até +2 pts extras).

### Distribuição entre membros (sugerida)

- Iniciantes: N1 (consolidação dos conceitos de serverless + IAM Role)
- Intermediários: N2 (estender a Lambda da aula com nova tool e observabilidade)
- Experientes: N3 (bônus) — design de tool de agente, benchmark, CI/CD

> **Rodízio:** quem fez N1 nas Aulas 1-2 deve assumir N2 ou N3 agora. Vale Critério 4 da rubrica.

### Template obrigatório

Use o [template em `entregas/template-entrega-grupo.md`](../../entregas/template-entrega-grupo.md) para o `entrega-grupo-aula03.md` dentro do ZIP.

> **Política "no install":** Tudo no AWS CloudShell.

---

## 🟢 Nível 1 — Básico: Consolidando os Fundamentos

### Exercício 1.1 — Quando usar Serverless?

Para cada cenário da Quantum Commerce, marque **Lambda**, **Elastic
Beanstalk** ou **❌ sem equivalente no Learner Lab** e justifique em uma frase:

| Cenário | Escolha | Justificativa |
|---------|---------|---------------|
| API de busca de produtos (1M chamadas/mês, picos na Black Friday) | | |
| Worker que processa pedidos da fila (1000 pedidos/dia, picos noturnos) | | |
| API legado em Java Spring Boot (não pode reescrever, time conhece) | | |
| Pipeline de processamento de imagens de produtos (chega 1 hora por noite) | | |
| Microserviço de pagamentos (regulado, precisa logs detalhados, 100 req/s constante) | | |
| Plataforma com 25 microserviços + service mesh (Itaú-like) | | |
| Container que extrai dados uma vez por dia e morre | | |

<details>
<summary>Sugestões de gabarito</summary>

- API de busca (1M/mês, picos): **Lambda** — pay-per-call, escala automático, free tier cobre
- Worker de fila: **Lambda com trigger SQS** — event-driven, escala a zero (SQS está disponível no Sandbox)
- Java Spring Boot legado: **Elastic Beanstalk** (Docker ou plataforma Java nativa) — Lambda tem custom runtime mas é overhead pra reescrever o empacotamento
- Pipeline batch de 1h/noite: **Lambda agendada via EventBridge** — pay-per-segundo, sem manter nada ligado
- Pagamentos com tráfego constante e regulado: **❌ sem equivalente real no Learner Lab** — em produção seria ECS/Fargate ou EKS (controle fino, sem cold start), nenhum dos dois liberado aqui
- 25 microserviços + service mesh: **❌ sem equivalente** — precisaria de EKS, que não existe no Academy
- Container one-shot: **Lambda (com container image, até 10GB)** ou um Elastic Beanstalk que sobe e é destruído — Lambda é o mais natural

**Reflexão adicional:** repare que 2 dos 7 cenários não têm resposta boa no
Learner Lab. Isso é intencional — é exatamente a lacuna que a tabela
"Mapeamento rápido" do guia aponta (Bloco 4).

</details>

---

### Exercício 1.2 — IAM Role vs alternativas

Para cada estratégia de credencial, marque **vulnerabilidade alta**, **média** ou **baixa** e justifique:

| Estratégia | Vulnerabilidade | Por quê |
|------------|-----------------|---------|
| Connection string hardcoded no `lambda_function.py` | | |
| Connection string em variável de ambiente da Lambda | | |
| Connection string no Secrets Manager, lida via Access Key de um usuário IAM | | |
| Connection string no Secrets Manager, lida via IAM Role (execution role da própria Lambda) | | |
| Sem connection string — IAM Role diretamente no recurso (S3) | | |

**Pergunta adicional:** Em uma das estratégias acima, **um vazamento do código no GitHub continua sendo problema**? Em quais não é? Por quê?

---

### Exercício 1.3 — Cold start na prática

Faça **3 chamadas** à sua Lambda (do lab L₂), com intervalo de:

- Chamada 1: **agora** (Lambda provavelmente fria)
- Chamada 2: **5 segundos depois**
- Chamada 3: **30 minutos depois** (Lambda provavelmente fria de novo — o
  container de execução é reciclado após alguns minutos sem uso)

Use `time curl "$API_URL/produtos"` para medir.

Preencha:

| Chamada | Tempo decorrido | Observação |
|---------|-----------------|------------|
| 1 (fria) | | |
| 2 (quente) | | |
| 3 (fria de novo) | | |

**Pergunta:** Se o agente da QC chamar essa Lambda 1 vez a cada hora durante
o dia (24 chamadas), quantas serão "frias"? Como você mitigaria isso se a UX
dos usuários exige resposta em < 500ms? (Pesquise: **Provisioned Concurrency**.)

---

### Exercício 1.4 — Dockerfile review

Considere este `Dockerfile` para a API da QC:

```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```

Liste **5 problemas** com este Dockerfile (segurança, tamanho, eficiência, boas práticas) e proponha melhorias.

<details>
<summary>Sugestões</summary>

1. Usa `python:3.11` (imagem completa ~1GB) em vez de `python:3.11-slim` (~150MB) → trocar para slim
2. `COPY . .` copia TUDO incluindo `.git`, `__pycache__`, etc. → usar `.dockerignore`
3. `pip install -r requirements.txt` sem `--no-cache-dir` → infla a imagem
4. Não usa multi-stage build → builders + libs grandes ficam no runtime
5. Roda como root → `USER appuser` (não-root) para segurança
6. `CMD ["python", "app.py"]` para web service → deveria usar uvicorn/gunicorn explicitamente
7. Não declara EXPOSE → menos legível
8. Sem `HEALTHCHECK` → orquestrador (ou o próprio Elastic Beanstalk) não sabe se está saudável

</details>

---

## 🟡 Nível 2 — Intermediário: Decisões de Design + IaC

### Exercício 2.1 — Adicionar segunda tool no agente: cálculo de frete

A QC tem outro caso de uso para Lambda: **calcular frete**. Specs:

- Input: CEP origem, CEP destino, peso (kg)
- Output: valor em R$ + tempo estimado de entrega
- Lógica: cálculo simples (R$ por km + R$ por kg). Pode ser determinístico.
- 50.000 chamadas/mês esperadas

**Sua tarefa:**

a) Decida: nova rota (`GET /frete`) na mesma Lambda/API Gateway, ou uma Lambda + API Gateway separados?
b) Implemente a rota `calcular_frete` no mesmo `lambda_function.py` da Aula 3 (continue a aplicação — adicione o roteamento em `handler()`).
c) Atualize o Terraform se necessário (adicionar `aws_apigatewayv2_route` para `GET /frete` — a Lambda e a integration já existem).
d) Documente como "tool" no formato JSON Schema (parecido com o catálogo no wrap-up da aula).
e) Reflexão: quando você criaria **uma Lambda diferente** vs **adicionar rotas na mesma função**?

---

### Exercício 2.2 — CloudWatch e X-Ray: observabilidade

A Lambda da Aula 3 não tinha X-Ray habilitado (foi desativado para simplificar). Em produção, você quer observabilidade.

**Sua tarefa:**

a) Estenda o `lambda.tf` da Aula 3 para habilitar tracing ativo (`tracing_config { mode = "Active" }` no `aws_lambda_function`) — X-Ray está disponível no Sandbox.
b) Após aplicar, faça 20 chamadas variadas à Lambda e abra o console → **X-Ray → Service Map**. Tire **um print** da tela mostrando o mapa de serviço.
c) Use o **CloudWatch Logs Insights** para responder (query sugerida: `fields @timestamp, @duration | filter @type = "REPORT" | stats avg(@duration), pct(@duration, 95) by bin(5m)`):
   - Quanto % das suas chamadas falhou (se houver)?
   - Qual o p95 de latência da Lambda?
   - Onde está o "gargalo" (tempo de inicialização/cold start vs execução)?
d) Pergunta de arquitetura: para um sistema multi-agente em produção, qual a estratégia ideal de logs/métricas/traces? Pesquise sobre **OpenTelemetry** e como ele se relaciona com X-Ray.

---

### Exercício 2.3 — Endurecer e dimensionar o Elastic Beanstalk da QC

O lab (Atividade 3) subiu um Elastic Beanstalk **básico** (`SingleInstance`,
`t3.micro`). Aqui você evolui esse mesmo ambiente no Terraform para cenários
mais próximos de produção da QC.

**Sua tarefa (partindo do `beanstalk.tf` do lab):**

a) **Padrão de execução para job batch** — o Elastic Beanstalk do lab é
   sempre-on (bom para um serviço web). Para um **job batch** da QC (ex.:
   recalcular recomendações à noite e terminar), esse não é o padrão certo.
   Proponha (não precisa implementar) uma alternativa usando **Lambda +
   EventBridge Scheduler**. Explique em uma frase por que Elastic Beanstalk
   sempre-on seria desperdício de custo para esse caso.

b) **Right-sizing + custo** — o ambiente do lab usa `t3.micro`. Suba uma
   variante com `t3.small` (mude `var.ec2_key_pair_name`... não, mude a
   `InstanceType` no `setting` de `aws:autoscaling:launchconfiguration`). No
   [AWS Pricing Calculator](https://calculator.aws/), estime o custo/hora de
   cada uma e o custo de deixar **1 instância 24/7** vs a **Lambda
   equivalente** (que escala a zero).

c) **Segredo via Secrets Manager** — mova ao menos uma configuração (ex.:
   uma chave de API fictícia) para o **AWS Secrets Manager** em vez de
   variável de ambiente em texto plano no `aws:elasticbeanstalk:application:environment`.
   Mostre como a aplicação leria esse segredo via `boto3` + `LabInstanceProfile`
   (mesmo princípio do S3: sem credenciais no código).

d) **Limite de réplica única** — o ambiente roda `EnvironmentType =
   "SingleInstance"`, sem autoscale nativo. Explique o que isso significa
   para um pico de tráfego da QC (ex.: Black Friday) e o que mudaria se você
   trocasse para `EnvironmentType = "LoadBalanced"` (Application Auto
   Scaling + ELB, ambos disponíveis no Sandbox).

e) **Reflexão:** Para a QC, em quais workloads você levaria **Elastic
   Beanstalk** e em quais levaria **Lambda**? Considere custo idle, HTTPS,
   escala e complexidade operacional — e o que mudaria se ECS/Fargate
   estivessem disponíveis.

---

## 🔴 Nível 3 — Avançado: Tool de Agente + Benchmark + CI/CD

### Exercício 3.1 — Lambda como Tool de um Agente AI (conceitual + código)

Você é arquiteto de um agente conversacional da QC. O agente usa um modelo de função (function calling) e precisa decidir quando chamar `buscar_produtos`.

**Sua tarefa:**

a) Escreva a **descrição completa** da tool no formato OpenAI Function Calling / Anthropic Tool Use:

```json
{
  "name": "buscar_produtos_qc",
  "description": "...",
  "input_schema": {
    "type": "object",
    "properties": {
      "categoria": {"type": "string", "description": "..."},
      "nome": {"type": "string", "description": "..."}
    }
  }
}
```

A descrição **deve ensinar o agente quando usar a tool**. Inclua exemplos.

b) Escreva 3 exemplos de **conversas usuário-agente** onde o agente decide chamar a tool:
   - "Tem cadeira boa para home office?"
   - "Quanto custa o Samsung S24?"
   - "Preciso de algo para café"

   Para cada, mostre: pergunta → call à tool (quais parâmetros) → resposta do agente.

c) Identifique 2 casos onde o agente **NÃO deve chamar a tool** mesmo o usuário falando de produto. Justifique.

d) **Reflexão:** Como você manteria a descrição da tool sincronizada com mudanças no endpoint? (Versionamento, contract testing, OpenAPI spec via API Gateway)

---

### Exercício 3.2 — Benchmark de carga

Use a ferramenta `hey` (instale com `go install` ou baixe o binário — ver
[README do hey](https://github.com/rakyll/hey)) para fazer load test na sua Lambda da Aula 3:

```bash
hey -n 1000 -c 50 "$API_URL/produtos?categoria=moveis"
```

**Reporte:**

- Latência média, p50, p95, p99
- Throughput (req/s)
- Taxa de erro
- Custo total (calcule com os valores atuais da [página de pricing do Lambda](https://aws.amazon.com/lambda/pricing/) — em geral na faixa de $0.20 por milhão de execuções + $0.0000166667 por GB-segundo; confirme os valores vigentes, eles mudam)

Faça o mesmo benchmark contra o Elastic Beanstalk da Aula 3. Compare:

| Métrica | Lambda | Elastic Beanstalk |
|---------|--------|--------------------|
| Latência média | | |
| p95 | | |
| Throughput | | |
| Erros | | |
| Custo aprox por 1M req | | |

**Reflexão (escrever):**

a) Qual aguentou melhor a carga? Por quê?
b) Em qual cenário a Lambda venceria? Em qual o Elastic Beanstalk venceria?
c) Como você arquitetaria a API da QC para suportar Black Friday (10x tráfego)?

---

### Exercício 3.3 — Pipeline CI/CD para a Lambda

Crie um workflow do **GitHub Actions** em `.github/workflows/deploy-lambda.yml` no repo privado do seu grupo que:

a) Roda em cada push para `main` que altere arquivos em `aula03-aws/lambda/**`
b) Faz lint do código Python (`ruff`)
c) Roda testes (criar pelo menos 1 teste com `pytest`)
d) Faz `aws lambda update-function-code` automaticamente

**Sobre autenticação — leia antes de implementar:**

A versão Azure deste exercício pede **OIDC** (autenticar sem secrets, via
federação de identidade). No AWS Academy Learner Lab isso **não é possível**:
o padrão OIDC do GitHub Actions para AWS exige criar uma **IAM OIDC identity
provider** e uma **IAM Role nova** com trust policy para o GitHub — e o
Academy **bloqueia a criação de roles** (só libera `LabRole`/`LabInstanceProfile`
pré-criadas, que não têm essa trust policy).

**Sua tarefa então é diferente:** use as credenciais temporárias da sessão
(`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` — as
mesmas 3 do painel "AWS Details") como **GitHub Secrets** normais (não OIDC).

**Reflexão obrigatória (substitui o "ponto extra de OIDC" da versão Azure):**

- Por que essa abordagem (secrets de sessão) seria **inaceitável em
  produção real**, fora do Academy?
- O que o Academy bloquear a criação de roles te ensina sobre o tradeoff
  entre "ambiente de sandbox restrito para aprendizado" e "segurança de
  produção"? Em uma conta AWS real seria a única real barreira, ou você
  identificaria outros riscos na abordagem de secrets estáticos vs OIDC?
- Sessões do Learner Lab duram só 4h e as credenciais mudam a cada "Start
  Lab" — o que isso implica para um pipeline de CI/CD que precise rodar
  fora do horário da aula?

> **Pontos extras:** Adicione um step de deploy para um **alias** da Lambda
> (`aws lambda update-alias`), simulando o conceito de slot deployment do
> Azure (deploy numa versão, promove depois).

> **Tudo via GitHub UI / github.dev** — sem instalar localmente.

---

## Critérios de entrega

A entrega é **um ZIP por grupo** (`entrega-grupo-NN-aula03.zip`) no Portal FIAP. Estrutura completa, prazo e dicas de geração do ZIP em [entregas/entrega-03/INSTRUCOES.md](../../entregas/entrega-03/INSTRUCOES.md).

| Item | Obrigatório? | Pontos máximos |
|------|--------------|----------------|
| Cabeçalho do grupo + distribuição do trabalho | ✅ Sim | 1 pt (Critério 4) |
| 🟢 N1 — Exercícios 1.1, 1.2, 1.3, 1.4 | ✅ Sim | 3 pts (Critério 1) |
| 🟡 N2 — 2.1 (segunda tool), 2.2 (CloudWatch/X-Ray), 2.3 (Beanstalk: padrão de execução/sizing/Secrets Manager) | ✅ Sim | 3 pts (Critério 2) + 2 pts qualidade técnica (Critério 3) |
| 🔴 N3 — 3.1 (tool spec), 3.2 (benchmark), 3.3 (CI/CD) | 🎁 Bônus | até +2 pts extras |
| Reflexão coletiva ao final | ✅ Sim | 1 pt (Critério 5) |
| **Total da entrega** | | **10 pts** (10% da nota final) |

**Prazo:** 1 dia antes da Aula 4.
**Onde:** upload do ZIP no Portal FIAP. Apenas 1 membro do grupo faz o upload.
