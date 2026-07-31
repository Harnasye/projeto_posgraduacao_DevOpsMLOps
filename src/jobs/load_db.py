"""
Job de carga das features transformadas para PostgreSQL.

Lê o Parquet de features em data/processed/selic_features.parquet e
persiste na tabela selic_features. Como o volume de dados da Selic é
pequeno (uma linha por dia útil), usamos inserção direta via pandas,
sem necessidade da lógica de chunking usada em datasets maiores.
"""

import logging
import os

import pandas as pd
from sqlalchemy.orm import Session

from src.config import DATA_PROCESSED_DIR
from src.models.selic import SelicFeatures

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_features_to_postgres(
    db: Session,
    filename: str = "selic_features.parquet",
    if_exists: str = "replace",
) -> int:
    """
    Carrega o Parquet de features no PostgreSQL (tabela selic_features).

    Parâmetros:
    - db        : Sessão SQLAlchemy
    - filename  : Nome do arquivo Parquet em DATA_PROCESSED_DIR
    - if_exists : 'replace' (padrão, apaga e recarrega tudo) ou 'append'

    Retorna a quantidade de linhas inseridas.
    """
    path = os.path.join(DATA_PROCESSED_DIR, filename)

    if not os.path.exists(path):
        logger.warning(f"Arquivo {path} não encontrado. Rode o transform primeiro.")
        return 0

    df = pd.read_parquet(path)

    if if_exists == "replace":
        deleted = db.query(SelicFeatures).delete()
        db.commit()
        logger.info(f"🗑️  {deleted} registros antigos removidos de selic_features.")

    registros = [
        SelicFeatures(
            data=row["data"],
            lag_1=row["lag_1"],
            lag_2=row["lag_2"],
            lag_3=row["lag_3"],
            lag_4=row["lag_4"],
            lag_5=row["lag_5"],
            media_movel_7=row["media_movel_7"],
            target=row["target"],
        )
        for _, row in df.iterrows()
    ]

    db.bulk_save_objects(registros)
    db.commit()

    logger.info(f"✅ {len(registros):,} linhas inseridas em selic_features.")
    return len(registros)


if __name__ == "__main__":
    import argparse
    from src.models.database import SessionLocal, init_db

    parser = argparse.ArgumentParser(description="Carrega features da Selic no PostgreSQL.")
    parser.add_argument(
        "--if-exists",
        choices=["append", "replace"],
        default="replace",
        help="Comportamento se a tabela já tem dados (padrão: replace)",
    )
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        rows = load_features_to_postgres(db=db, if_exists=args.if_exists)
        logger.info(f"Resultado: {rows} linhas carregadas.")
    finally:
        db.close()