"""
API FastAPI — Previsão da Taxa Selic.

Endpoints:
- / — Info geral da API
- /health — Healthcheck para orquestradores
- /selic/* — Consulta do histórico e último valor da Selic (router)
- /admin/* — Dashboard e controle de sincronização/pipeline (router)
- /predict/* — Model Serving da previsão da Selic
- /ml/tracking/* — Gerenciamento de experimentos MLflow

Documentação automática: http://localhost:8000/docs
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.models.database import init_db
from src.routers import selic, admin, s3_status, ml_serving, ml_tracking

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa o banco de dados na startup da API."""
    init_db()
    yield

app = FastAPI(
    title="Previsão Selic API",
    description=(
        "API para ingestão, processamento e previsão da Taxa Selic "
        "usando dados públicos do Banco Central do Brasil (SGS).\n\n"
        "**Funcionalidades:**\n"
        "- 📊 Consulta do histórico da Selic\n"
        "- 🔄 Dashboard de sincronização para controle de dados\n"
        "- 📥 Sync incremental da série via API do BCB\n"
        "- 🤖 Model Serving para previsão do próximo valor da Selic\n"
        "- 🧪 Gerenciamento de testes e runs com MLflow Tracking\n\n"
        "**Fonte de dados:** [SGS — Banco Central do Brasil]"
        "(https://dadosabertos.bcb.gov.br/)"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Registrar routers
app.include_router(selic.router)
app.include_router(admin.router)
app.include_router(s3_status.router)
app.include_router(ml_serving.router)
app.include_router(ml_tracking.router)

# Timestamp de startup para cálculo de uptime
START_TIME = time.time()


@app.get("/", tags=["General"])
async def root():
    """
    Root endpoint com informações básicas da API.
    """
    return {
        "message": "Bem-vindo à API de Previsão da Taxa Selic!",
        "status": "Running",
        "documentation": "/docs",
        "endpoints": {
            "selic": "/selic",
            "admin_dashboard": "/admin/sync",
            "ml_tracking": "/ml/tracking",
            "predict": "/predict",
            "health": "/health",
        },
    }


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Health check endpoint para container orchestrators e Podman healthcheck.
    """
    uptime = time.time() - START_TIME
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "uptime_seconds": round(uptime, 2),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )