"""
Job de upload de dados para Garage (S3-compatível).

Organiza o bucket em camadas:
  s3://cnpj-data/raw/selic/selic_serie.csv          ← snapshot bruto da série
  s3://cnpj-data/processed/selic/selic_features.parquet  ← features prontas para ML

Todos os uploads usam boto3 upload_file (streaming do disco, sem carregar na RAM).
"""

import logging
import os

import pandas as pd
from botocore.exceptions import ClientError

from src.utils import format_bytes as _format_bytes, get_s3_client
from src.config import S3_BUCKET_NAME, DATA_RAW_DIR, DATA_PROCESSED_DIR
from src.models.selic import SelicSerie

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _ensure_bucket_exists(s3_client, bucket_name: str):
    """Cria o bucket se não existir."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        logger.info(f"Criando bucket '{bucket_name}'...")
        s3_client.create_bucket(Bucket=bucket_name)
        logger.info(f"Bucket '{bucket_name}' criado.")


def upload_raw_snapshot_to_s3(db) -> dict:
    """
    Exporta a tabela selic_serie inteira para CSV e envia para
    s3://bucket/raw/selic/selic_serie.csv.
    """
    os.makedirs(os.path.join(DATA_RAW_DIR, "selic"), exist_ok=True)
    local_path = os.path.join(DATA_RAW_DIR, "selic", "selic_serie.csv")

    registros = db.query(SelicSerie).order_by(SelicSerie.data).all()
    df = pd.DataFrame(
        [{"data": r.data, "valor": float(r.valor), "serie_codigo": r.serie_codigo} for r in registros]
    )
    df.to_csv(local_path, index=False)

    s3_client = get_s3_client()
    _ensure_bucket_exists(s3_client, S3_BUCKET_NAME)

    s3_key = "raw/selic/selic_serie.csv"
    local_size = os.path.getsize(local_path)

    logger.info(f"📤 Enviando snapshot raw ({_format_bytes(local_size)}) para {s3_key}...")
    s3_client.upload_file(local_path, S3_BUCKET_NAME, s3_key)
    logger.info(f"✅ s3://{S3_BUCKET_NAME}/{s3_key}")

    return {"uploaded": 1, "s3_key": s3_key, "size_bytes": local_size}


def upload_processed_to_s3(filename: str = "selic_features.parquet") -> dict:
    """
    Envia o Parquet de features processadas para
    s3://bucket/processed/selic/{filename}.
    """
    local_path = os.path.join(DATA_PROCESSED_DIR, filename)

    if not os.path.exists(local_path):
        logger.warning(f"Arquivo {local_path} não encontrado.")
        return {"error": "file_not_found"}

    s3_client = get_s3_client()
    _ensure_bucket_exists(s3_client, S3_BUCKET_NAME)

    s3_key = f"processed/selic/{filename}"
    local_size = os.path.getsize(local_path)

    logger.info(f"📤 Enviando features processadas ({_format_bytes(local_size)}) para {s3_key}...")
    s3_client.upload_file(local_path, S3_BUCKET_NAME, s3_key)
    logger.info(f"✅ s3://{S3_BUCKET_NAME}/{s3_key}")

    return {"uploaded": 1, "s3_key": s3_key, "size_bytes": local_size}


if __name__ == "__main__":
    import argparse
    from src.models.database import SessionLocal, init_db

    parser = argparse.ArgumentParser(description="Envia dados da Selic para o Garage S3.")
    parser.add_argument(
        "--layer",
        choices=["raw", "processed", "both"],
        default="both",
        help="Camada a enviar: raw (snapshot CSV), processed (features Parquet), both",
    )
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        if args.layer in ("raw", "both"):
            upload_raw_snapshot_to_s3(db)
        if args.layer in ("processed", "both"):
            upload_processed_to_s3()
    finally:
        db.close()