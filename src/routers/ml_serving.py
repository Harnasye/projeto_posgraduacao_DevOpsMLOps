import os
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import pandas as pd
import mlflow.pyfunc

from src.models.database import get_db
from src.models.selic import SelicSerie

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
    últimos valores históricos (lags) e da média móvel de 7 dias
    informados manualmente no payload.
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


@router.post("/latest", response_model=PredictionResponse)
async def predict_latest(db: Session = Depends(get_db)):
    """
    Realiza uma predição do próximo valor da Taxa Selic, buscando
    automaticamente os últimos valores reais sincronizados no banco
    (sem precisar montar o payload manualmente).
    """
    if model is None:
        raise HTTPException(
            status_code=503, detail="Modelo de previsão da Selic não está disponível no momento."
        )

    # Busca os 7 valores mais recentes, do mais novo para o mais antigo
    registros = (
        db.query(SelicSerie)
        .order_by(SelicSerie.data.desc())
        .limit(7)
        .all()
    )

    if len(registros) < 7:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Dados insuficientes para calcular as features: encontrados apenas "
                f"{len(registros)} registros, mas são necessários pelo menos 7. "
                "Rode 'make sync' para sincronizar mais histórico."
            ),
        )

    # registros[0] é o mais recente; lag_1 = valor mais recente, lag_2 = anterior, etc.
    valores = [float(r.valor) for r in registros]

    features = {
        "lag_1": valores[0],
        "lag_2": valores[1],
        "lag_3": valores[2],
        "lag_4": valores[3],
        "lag_5": valores[4],
        "media_movel_7": sum(valores) / len(valores),
    }

    try:
        data = pd.DataFrame([features])
        prediction = model.predict(data)[0]

        return PredictionResponse(
            valor_previsto=float(prediction),
            message=(
                f"Predição realizada com sucesso, usando dados reais até "
                f"{registros[0].data.isoformat()}."
            ),
        )
    except Exception as e:
        logger.error(f"Erro durante predição: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar a predição.")