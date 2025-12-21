FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema (incluindo cairo para pycairo)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar script de inicialização
RUN echo '#!/bin/bash\n\
echo "🚀 Iniciando Petitio..."\n\
python init_db.py\n\
echo "✅ Banco inicializado"\n\
exec "$@"' > /app/start.sh && chmod +x /app/start.sh

# Expor porta
EXPOSE 8080

# Variáveis de ambiente
ENV FLASK_ENV=production
ENV PORT=8080

# Comando de inicialização
CMD ["/app/start.sh", "gunicorn", "run:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120"]
