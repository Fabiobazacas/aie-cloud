# Exercícios — Aula 5 (AWS): Deva Contínuo

**Tema:** Continuidade de agentes — memória revisável, rastreabilidade, taxa de devolução, segunda opinião
**Formato:** material suplementar — **não tem ZIP/portal próprio** (não é a Aula 5 oficial deste repositório, ver [README.md](README.md)). Combine com o professor se algum destes exercícios entra na avaliação.

> Os 4 exercícios abaixo são os "quatro exercícios de depois" do deck
> original ("AI Agents — Azure Foundry"), adaptados para a base de código em
> [lab/](lab/). Todos partem do lab já funcionando (rode
> [lab/guia-lab.md](lab/guia-lab.md) primeiro) — nenhum deles está
> pré-implementado de propósito.

---

## Instruções gerais

- 🟢 **Nível 1 — Básico:** Esquecimento (arquivar uma regra aprovada)
- 🟡 **Nível 2 — Intermediário:** Rastreabilidade + Taxa de devolução
- 🔴 **Nível 3 — Avançado (bônus):** Segunda opinião

Cada exercício parte de um ponto específico do código que **já existe, mas
está incompleto de propósito** — leia o comentário no arquivo indicado antes
de começar.

---

## 🟢 Nível 1 — Esquecimento

### Exercício 1 — `POST /memoria/{regra_id}/arquivar`

**Pergunta que abre o exercício:** uma regra de 12 meses sem uso continua
valendo? Quem decide?

O endpoint já existe em [lab/api/principal.py](lab/api/principal.py)
(`arquivar_memoria`), mas devolve `501 Not Implemented` de propósito. Sua tarefa:

a) Em [lab/api/servicos/memoria.py](lab/api/servicos/memoria.py), implemente
   `arquivar(regra_id: str, auditor: str) -> None`:
   - Localize a linha em `MEMORY.md` que contém `regra: {regra_id}` (o
     sufixo que `aprovar()` já grava em cada linha aprovada).
   - Não apague a linha — **mova-a** para uma seção `## Arquivadas` no fim do
     mesmo arquivo (ou um arquivo separado `MEMORY-ARQUIVADAS.md`, sua
     escolha — documente qual no README do exercício). Uma regra arquivada
     **não deve mais** aparecer em `listar_aprovadas()` (ela não pode mais
     influenciar `ciclo_do_agente.py`), mas o histórico não pode sumir —
     pense em por que isso importa numa auditoria.
   - Registre quem arquivou e quando, no mesmo formato de assinatura que
     `aprovar()` usa.

b) Ligue essa função no endpoint `arquivar_memoria` (troque o
   `HTTPException(501, ...)` pela chamada de verdade).

c) **Reflexão:** proponha uma regra de negócio pra "quando" uma regra pode
   ser arquivada automaticamente (ex.: sem uso — nenhuma nota aplicou essa
   `regra_aplicada` — há N dias). Você implementaria isso como um cron/job
   separado, ou dentro do próprio `ciclo_do_agente.py`? Por quê?

**✅ Checkpoint:** `curl -X POST .../memoria/<id>/arquivar -H "X-Auditor: Você"` funciona, e a regra arquivada some de `GET /memoria` mas continua rastreável em algum lugar?

---

## 🟡 Nível 2 — Rastreabilidade e Taxa de Devolução

### Exercício 2 — Rastreabilidade: quem dependia da regra que você arquivou?

O endpoint `GET /rastreamento/{nota_id}` já existe e devolve
`regra_aplicada` de uma nota específica — mas não existe o caminho inverso:
"dado o id de uma regra, quais notas dependeram dela".

**Sua tarefa:**

a) Em [lab/api/servicos/fila.py](lab/api/servicos/fila.py), implemente
   `notas_por_regra(regra_id: str) -> list[dict]` — varre `notas.json` e
   devolve todas as notas cujo `regra_aplicada` referencia essa regra (o
   `regra_id` aparece dentro da string `regra_aplicada` guardada em cada
   nota processada — confira o formato exato que `marcar_processada` grava
   hoje e ajuste se precisar de um campo próprio `regra_id` separado do
   texto livre de `regra_aplicada`).

b) Exponha isso como `GET /memoria/{regra_id}/dependentes` (só humano,
   `X-Auditor`).

c) Ligue ao Exercício 1: quando `arquivar()` for chamado, ele deve **avisar**
   (retornar na resposta, não bloquear) quantas notas dependiam da regra
   arquivada. Ex.: `{"status": "arquivada", "notas_dependentes": 3}`.

d) **Reflexão:** se uma regra tem 200 notas dependentes, isso muda sua
   resposta pra "quem decide arquivar" do Exercício 1? Por quê?

**✅ Checkpoint:** arquivar uma regra que uma das notas semeadas usou mostra corretamente `notas_dependentes >= 1`?

---

### Exercício 3 — Taxa de devolução

**Pergunta que abre o exercício:** não é quantos documentos o agente
processou — é quantos ele **devolveu**. Se passar de 30%, o problema é a
regra, não o modelo.

O endpoint `GET /fila/metricas` já devolve contagens brutas por estado
(`api/servicos/fila.py::contagens()`). Sua tarefa:

a) Calcule a **taxa de devolução** = `(duplicada + excecao) / total`.

b) Se a taxa passar de **30%**, o endpoint `/fila/metricas` deve incluir um
   campo `alerta: "taxa de devolução acima de 30% — revisar regras, não o modelo"`.

c) Rode o lab semeando **mais notas ambíguas** (edite
   `gatilho/disparador.py::NOTAS_EXEMPLO` temporariamente, ou poste via
   `/notas/semear`) até estourar os 30% e confirme que o alerta aparece.

d) **Reflexão:** essa métrica devia olhar pra taxa **acumulada desde
   sempre**, ou uma **janela móvel** (ex.: últimos 7 dias)? O que muda pro
   Deva se as regras de política mudarem no meio do caminho?

**✅ Checkpoint:** o alerta aparece quando você força a taxa acima de 30%, e desaparece quando ela volta pra baixo?

---

## 🔴 Nível 3 (bônus) — Segunda opinião

### Exercício 4 — Um segundo agente critica a proposta

**Pergunta que abre o exercício:** ajuda, ou vira teatro?

Antes de uma proposta chegar em `MEMORIA-PENDENTE.md` (ou antes de um humano
aprová-la), um **segundo agente** — outra chamada ao Bedrock, com um prompt
diferente, focado em achar problemas — dá uma opinião sobre a proposta.

**Sua tarefa:**

a) Em [lab/agente/cliente_bedrock.py](lab/agente/cliente_bedrock.py),
   implemente `criticar_proposta(texto_proposta: str, contexto_nota: dict, mock: bool = True) -> dict`,
   devolvendo algo como
   `{"concorda": bool, "objecao": str | None}`. O prompt do segundo agente
   deve ser **adversarial**: instrua-o explicitamente a procurar por
   problemas (regra vaga demais, exceção disfarçada de regra geral, viés
   contra um fornecedor específico) — não peça uma opinião neutra.

b) Ligue essa segunda opinião no fluxo de `ciclo_do_agente.py`: quando o
   Deva propõe uma regra (o caminho de exceção), chame `criticar_proposta`
   antes de `memoria.propor(...)`. Se o segundo agente discordar, anexe a
   objeção ao texto da proposta (ex.: `"{texto} [objeção do revisor: {objecao}]"`)
   — a proposta ainda vai pra fila, mas o humano vê a objeção antes de aprovar.

c) Teste os dois caminhos: uma proposta que o segundo agente aprova sem
   objeção, e uma que ele objeta (pode ser com `--mock`, retornando valores
   fixos pros dois casos, ou com o Bedrock de verdade usando dois prompts
   claramente diferentes).

d) **Reflexão (a pergunta central do exercício):**
   - Rodar dois agentes custa 2x mais chamadas de modelo por proposta. Em
     que ponto isso deixa de valer a pena?
   - Se os dois agentes usam o **mesmo modelo com o mesmo viés de fundo**, a
     segunda opinião é uma checagem de verdade ou só uma ilusão de
     verificação? O que mudaria se o segundo agente usasse um **modelo
     diferente** (ex.: um modelo de outro provedor via a mesma interface)?
   - Quem revisa o revisor? Se o segundo agente também pudesse aprovar
     memória sozinho, você recriou o mesmo problema que a Atividade 4 do
     lab resolveu.

**✅ Checkpoint (bônus):** você tem uma proposta com objeção visível na fila, e consegue explicar em 3 frases se o custo extra de rodar dois agentes se pagou nesse caso.

---

## Sobre usar Bedrock de verdade nestes exercícios

Todos os exercícios acima funcionam inteiramente com o modo `--mock`
(heurística local, custo zero). Se quiser usar o Bedrock de verdade em
algum deles, confirme primeiro o acesso ao modelo (mesmo checkpoint das
Aulas 3/4):

```bash
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[].modelId" --output table
```

Se vier vazio ou `AccessDeniedException`, habilite `Anthropic Claude 3
Haiku` em **Model access** no console do Bedrock, ou avise o professor se a
conta do Academy não tiver Bedrock liberado — nenhum destes exercícios
depende disso pra ser corrigido/avaliado, o modo `--mock` é aceitável.
