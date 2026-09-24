# Multi-stage build para imagem leve.
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/install -r requirements.txt

# Imagem final
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.11/site-packages
COPY app.py .

EXPOSE 8080

# Invoca uvicorn como MÓDULO: o pip install --target só copia os pacotes para
# site-packages, não o executável 'uvicorn' para o PATH. "python -m uvicorn"
# usa o pacote diretamente e evita o erro "uvicorn: executable file not found".
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
