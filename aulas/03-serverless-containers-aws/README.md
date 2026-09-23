# Aula 3 (AWS) — Compute Avançado: Serverless, VMs e Containers

> **Versão AWS Academy Learner Lab** desta aula. A versão original (Azure) está em
> [../03-serverless-containers/](../03-serverless-containers/). Os objetivos de
> aprendizagem e a lógica de negócio são os mesmos — só a nuvem e os serviços mudam.

## Objetivos de aprendizagem

Ao final desta aula, você será capaz de:

- Comparar os 3 modelos de compute: EC2 (VMs), Containers e Serverless (Lambda).
- Decidir qual modelo usar para cada tipo de workload da QC.
- Provisionar uma **AWS Lambda** com **API Gateway HTTP API** via Terraform (deploy embutido no `apply` — sem CLI extra).
- Acessar recursos da AWS **sem credenciais no código** usando uma **IAM Role** (`LabRole`) anexada à função — o equivalente do Managed Identity do Azure.
- Empacotar uma aplicação Python (FastAPI) em **container Docker** e rodar no **AWS Elastic Beanstalk** (plataforma Docker) — a alternativa disponível no Academy à falta de ECS/Fargate/EKS.
- Entender por que um orquestrador completo de containers (ECS/EKS) **não está disponível** no Learner Lab e quando ele faria sentido fora dele.

---

## Por que esta aula importa para um AI Engineer

A camada de **compute** é onde os agentes da QC vão **rodar** (Lambdas chamadas pelos modelos como tools) e onde as **APIs** que eles consomem ficam expostas. Lambda + API Gateway + IAM Role é o padrão AWS para tornar um endpoint **utilizável por um agente** sem vazar credenciais — o mesmo problema que Function + Managed Identity resolve no Azure.

---

## Conexão com o Quantum Commerce

Nesta aula você implanta a **API de catálogo** da Quantum Commerce — primeira **tool** que os agentes da QC vão chamar. Dois sabores:

1. **Lambda HTTP (Python)** — pay-per-execution, escala a zero, cold start menor.
2. **Container (FastAPI + Elastic Beanstalk)** — mesma lógica de negócio empacotada em container.

Ambas leem `produtos.csv` de um bucket S3 **criado nesta própria aula** — **sem credenciais hardcoded**, via IAM Role.

---

## Restrições do AWS Academy Learner Lab que moldam esta aula

| Restrição | Impacto |
|-----------|---------|
| Só `us-east-1`/`us-west-2` | Terraform valida a região; qualquer outra é rejeitada |
| Sem console IAM de usuário próprio; não pode criar roles novas | Lambda e Elastic Beanstalk usam as roles **pré-criadas** `LabRole`/`LabInstanceProfile` — nunca criamos uma role nova |
| Sessão de 4h, conta temporária a cada "Start Lab" | Nada pressupõe estado de uma sessão anterior; credenciais (Access Key + Secret + **Session Token**) mudam a cada sessão |
| **Sem ECS/Fargate/EKS/App Runner** | Container roda em **Elastic Beanstalk** (Docker de container único) — mais parecido com ACI/App Service do que com um orquestrador completo |

Ver o levantamento completo de serviços liberados no [guia do lab](lab/guia-lab.md#recursos-disponíveis-no-learner-lab).

---

## Material da aula

| Arquivo | Quando usar |
|---------|-------------|
| [lab/guia-lab.md](lab/guia-lab.md) | Durante a aula — 3 atividades intercaladas |
| [lab/terraform/](lab/terraform/) | Código IaC: Lambda + API Gateway + S3 + Elastic Beanstalk + IAM (data sources) |
| [lab/lambda/v1-mock/](lab/lambda/v1-mock/) | Versão 1 da Lambda (mock data) — L₁ |
| [lab/lambda/v2-s3/](lab/lambda/v2-s3/) | Versão 2 da Lambda (S3 + IAM Role) — L₂ |
| [lab/docker/](lab/docker/) | Versão FastAPI containerizada — L₃ |
| [exercicios.md](exercicios.md) | Após a aula — exercícios em 3 níveis (🟢/🟡/🔴) |

## Entrega de grupo

Mesma entrega da versão Azure desta aula: instruções em [entregas/entrega-03/](../../entregas/entrega-03/). Rubrica em [entregas/rubrica.md](../../entregas/rubrica.md). Combine com seu grupo/professor qual das duas versões (Azure ou AWS) vale como entrega.

---

## Pré-requisitos

- ✅ Conta ativa no **AWS Academy Learner Lab** (curso Cloud Developing) e sessão iniciada ("Start Lab")
- ✅ Repositório `aie-cloud` clonado no **AWS CloudShell**

> **Aula independente da Aula 2.** O Terraform desta aula cria seu próprio
> bucket S3 de catálogo e já sobe o `produtos.csv` ([lab/data/produtos.csv](lab/data/produtos.csv))
> no `apply`. Nenhum passo da Aula 2 é necessário.
