"""
Pipeline de treinamento do modelo de previsão da Taxa Selic.

Usa as features de série temporal (lags + média móvel) construídas em
transform.py e treina um modelo de regressão (RandomForestRegressor)
para prever o valor da Selic do próximo dia útil.

Métricas e modelo são registrados no MLflow.
"""

import os
import logging

import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.models.database import SessionLocal
from src.jobs.transform import build_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# MLflow tracking URL — no compose está mapeado para localhost:5001, mas
# internamente no container da API usamos o nome do serviço (http://mlflow:5000)
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")

FEATURE_COLUMNS = ["lag_1", "lag_2", "lag_3", "lag_4", "lag_5", "media_movel_7"]


def load_training_data():
    """Carrega as features de série temporal da Selic a partir do PostgreSQL."""
    logger.info("Conectando ao banco de dados e construindo features para treino...")
    db = SessionLocal()
    try:
        df = build_features(db)
    finally:
        db.close()

    logger.info(f"Dados carregados: {df.shape[0]} linhas.")
    return df


def run_training():
    logger.info("Iniciando pipeline de treinamento da previsão da Selic...")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("Selic_Previsao")

    df = load_training_data()
    if df.empty:
        logger.error("Nenhum dado disponível! Rode o sync e o transform antes do treino.")
        return

    X = df[FEATURE_COLUMNS]
    y = df["target"]

    # shuffle=False é essencial em série temporal: nunca embaralhar,
    # senão o modelo "vê o futuro" durante o treino.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    # Hiperparâmetros
    n_estimators = 200
    max_depth = 8

    with mlflow.start_run() as run:
        logger.info("Treinando modelo RandomForestRegressor...")
        model = RandomForestRegressor(
            n_estimators=n_estimators, max_depth=max_depth, random_state=42
        )
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = mean_squared_error(y_test, y_pred) ** 0.5
        r2 = r2_score(y_test, y_pred)

        logger.info(f"Métricas do modelo: MAE={mae:.4f}, RMSE={rmse:.4f}, R²={r2:.4f}")

        # Log no MLflow
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("max_depth", max_depth)
        mlflow.log_param("n_lags", len(FEATURE_COLUMNS) - 1)
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("r2", r2)

        # Logar o modelo
        logger.info("Salvando modelo no MLflow...")
        model_info = mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="random_forest_selic",
        )

        logger.info("Registrando modelo no MLflow Registry...")
        mlflow.register_model(
            model_uri=model_info.model_uri,
            name="SelicPredictor",
        )

        logger.info(f"Treinamento finalizado com sucesso! Run ID: {run.info.run_id}")
        logger.info(f"URI do Modelo: {model_info.model_uri}")


if __name__ == "__main__":
    run_training()