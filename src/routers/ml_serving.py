import os
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import mlflow.pyfunc

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/predict",
    tags=["Model Serving"],
)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Variável global para armazenar o modelo carregado
model = None


class PredictionRequest(BaseModel):
    lag_1: float
    lag_2: float
    lag_3: float
    lag_4: float
    lag_5: float
    media_movel_7: float


class PredictionResponse(BaseModel):
    valor_previsto: float
    message: str


def load_model():
    """Carrega o modelo mais recente do MLflow Registry na inicialização."""
    global model
    model_name = "SelicPredictor"
    model_uri = f"models:/{model_name}/latest"
    try:
        logger.info(f"Carregando modelo MLflow de {model_uri}")
        model = mlflow.pyfunc.load_model(model_uri)
        logger.info("Modelo carregado com sucesso.")
    except Exception as e:
        logger.error(f"Falha ao carregar modelo MLflow: {e}")
        # A API pode subir mesmo se o modelo ainda não tiver sido treinado


@router.on_event("startup")
async def startup_event():
    load_model()


@router.post("/", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Realiza uma predição do próximo valor da Taxa Selic, a partir dos
    últimos valores históricos (lags) e da média móvel de 7 dias.
    """
    if model is None:
        raise HTTPException(
            status_code=503, detail="Modelo de previsão da Selic não está disponível no momento."
        )

    try:
        data = pd.DataFrame([request.dict()])
        prediction = model.predict(data)[0]

        return PredictionResponse(
            valor_previsto=float(prediction),
            message="Predição realizada com sucesso.",
        )
    except Exception as e:
        logger.error(f"Erro durante predição: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar a predição.")