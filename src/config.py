"""
Configurações centralizadas do projeto.

Todas as variáveis de ambiente são lidas aqui e expostas como constantes
para uso tanto pela API (live) quanto pelos jobs batch.

Referência: 12-Factor App — https://12factor.net/config
"""

import os


# === Banco de Dados (PostgreSQL) ===
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/selic")

# === Object Storage (Garage S3) ===
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:3900")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "selic-data")

# === Banco Central (SGS - Sistema Gerenciador de Séries Temporais) ===
BCB_BASE_URL = os.getenv("BCB_BASE_URL", "https://api.bcb.gov.br/dados/serie")
SELIC_SERIE_CODE = os.getenv("SELIC_SERIE_CODE", "432")  # Meta Selic definida pelo Copom

# === Diretórios Locais ===
DATA_RAW_DIR = os.getenv("DATA_RAW_DIR", "data/raw")
DATA_PROCESSED_DIR = os.getenv("DATA_PROCESSED_DIR", "data/processed")

# === Aplicação ===
ENV = os.getenv("ENV", "development")
