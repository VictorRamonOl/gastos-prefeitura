# ── Build stage ──────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Evita arquivos .pyc e garante logs sem buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do sistema necessárias para mysql-connector e bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python primeiro (camada cacheável)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────
COPY . .

# Cria diretório de uploads (será montado como volume no docker-compose)
RUN mkdir -p data/uploads

# Porta exposta pelo Streamlit
EXPOSE 8501

# Health check — Streamlit expõe /_stcore/health
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Ponto de entrada
ENTRYPOINT ["streamlit", "run", "app/app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true"]
