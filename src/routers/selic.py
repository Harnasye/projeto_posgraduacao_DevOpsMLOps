"""
Router de consulta da série histórica da Taxa Selic.

Endpoints para consultar o histórico e o último valor sincronizado
da Meta Selic, armazenados a partir da API do Banco Central (SGS).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.models.database import get_db
from src.models.selic import SelicSerie

router = APIRouter(prefix="/selic", tags=["Selic"])


@router.get(
    "/historico",
    summary="Histórico da Taxa Selic",
    description="Retorna os valores mais recentes da série histórica da Selic, em ordem decrescente de data.",
    response_description="Lista de valores históricos da Selic.",
)
async def historico(
    limit: int = Query(default=30, ge=1, le=1000, description="Quantidade de registros a retornar"),
    db: Session = Depends(get_db),
):
    """
    Lista o histórico da Selic, do mais recente para o mais antigo.

    - **limit**: Quantidade máxima de registros (1-1000, padrão: 30)
    """
    registros = (
        db.query(SelicSerie).order_by(SelicSerie.data.desc()).limit(limit).all()
    )

    return {
        "total": len(registros),
        "data": [
            {"data": r.data.isoformat(), "valor": float(r.valor)}
            for r in registros
        ],
    }


@router.get(
    "/ultimo",
    summary="Último valor sincronizado da Selic",
    description="Retorna o valor mais recente já sincronizado na base local.",
    response_description="Último valor da Selic disponível localmente.",
)
async def ultimo(db: Session = Depends(get_db)):
    """
    Retorna o registro mais recente da Selic disponível no banco local.
    """
    registro = db.query(SelicSerie).order_by(SelicSerie.data.desc()).first()

    if not registro:
        raise HTTPException(
            status_code=404,
            detail="Nenhum dado sincronizado ainda. Rode o job de sync primeiro.",
        )

    return {"data": registro.data.isoformat(), "valor": float(registro.valor)}


@router.get(
    "/periodo",
    summary="Buscar Selic por período",
    description="Retorna os valores da Selic dentro de um intervalo de datas.",
    response_description="Lista de valores da Selic no período informado.",
)
async def periodo(
    data_inicial: str = Query(..., description="Data inicial no formato YYYY-MM-DD"),
    data_final: str = Query(..., description="Data final no formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """
    Busca valores da Selic num intervalo de datas.

    - **data_inicial**: Formato YYYY-MM-DD
    - **data_final**: Formato YYYY-MM-DD
    """
    registros = (
        db.query(SelicSerie)
        .filter(SelicSerie.data >= data_inicial, SelicSerie.data <= data_final)
        .order_by(SelicSerie.data)
        .all()
    )

    return {
        "data_inicial": data_inicial,
        "data_final": data_final,
        "total": len(registros),
        "data": [
            {"data": r.data.isoformat(), "valor": float(r.valor)}
            for r in registros
        ],
    }