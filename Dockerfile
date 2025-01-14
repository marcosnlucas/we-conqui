FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro para aproveitar cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Criar diretório para o SQLite e logs
RUN mkdir -p instance logs && \
    chown -R nobody:nogroup instance logs

# Usar usuário não-root
USER nobody

# Expor porta
EXPOSE 5001

# Comando para iniciar
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "3", "--timeout", "120", "app:app"]
