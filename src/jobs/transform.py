"""
Job de transformação: constrói features de série temporal a partir da
tabela selic_serie, para uso no treinamento e no serving do modelo de ML.

Features geradas:
- lag_1 a lag_5: valores dos últimos dias úteis
- media_movel_7: média móvel de 7 dias
- target: valor do próximo dia (usado apenas no treino)
"""

import logging
import os

import pandas as pd
from sqlalchemy.orm import Session

from src.config import DATA_PROCESSED_DIR
from src.models.selic import SelicSerie

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

N_LAGS = 5
JANELA_MEDIA_MOVEL = 7


def build_features(db: Session, n_lags: int = N_LAGS) -> pd.DataFrame:
    """
    Constrói o dataset de features de série temporal a partir da selic_serie.

    Retorna um DataFrame com colunas: data, valor, lag_1..lag_n,
    media_movel_7, target.
    """
    registros = db.query(SelicSerie).order_by(SelicSerie.data).all()

    if not registros:
        logger.warning("Nenhum dado encontrado em selic_serie. Rode o sync primeiro.")
        return pd.DataFrame()

    df = pd.DataFrame([{"data": r.data, "valor": float(r.valor)} for r in registros])

    for lag in range(1, n_lags + 1):
        df[f"lag_{lag}"] = df["valor"].shift(lag)

    df["media_movel_7"] = df["valor"].rolling(window=JANELA_MEDIA_MOVEL).mean()
    df["target"] = df["valor"].shift(-1)  # valor do dia seguinte

    df = df.dropna().reset_index(drop=True)

    logger.info(f"Dataset de features construído: {df.shape[0]} linhas, {df.shape[1]} colunas")
    return df


def save_features_parquet(df: pd.DataFrame, filename: str = "selic_features.parquet") -> str:
    """Salva o DataFrame de features em Parquet, em DATA_PROCESSED_DIR."""
    os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
    path = os.path.join(DATA_PROCESSED_DIR, filename)
    df.to_parquet(path, index=False)
    logger.info(f"Features salvas em: {path}")
    return path


if __name__ == "__main__":
    from src.models.database import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        df = build_features(db)
        if not df.empty:
            save_features_parquet(df)
    finally:
        db.close()