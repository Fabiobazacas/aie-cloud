#!/usr/bin/env bash
# Encerramento do lab — limpa o estado local e, se a camada opcional de
# nuvem tiver sido provisionada, derruba ela também. Rode isso ao final,
# mesmo no modo 100% local (custo já é zero, mas os dados ficam limpos pra
# a próxima turma/sessão).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Limpando estado local (notas.json, MEMORY.md, MEMORIA-PENDENTE.md, entrada/)..."
rm -f dados/notas.json dados/MEMORY.md dados/MEMORIA-PENDENTE.md
rm -rf dados/entrada/processadas
find dados/entrada -maxdepth 1 -name '*.json' -delete 2>/dev/null || true

if [ -d terraform/.terraform ] && [ -f terraform/terraform.tfstate ]; then
  echo "Camada de nuvem (S3+SQS) detectada — rodando terraform destroy..."
  (cd terraform && terraform destroy -auto-approve)
else
  echo "Nenhuma camada de nuvem provisionada (modo local) — nada a destruir na AWS."
fi

echo "Pronto. Custo desta sessão: \$0,00 (local) ou centavos de S3/SQS (se a camada de nuvem foi usada)."
