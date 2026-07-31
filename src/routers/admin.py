"""
Router de administração e dashboard de sincronização — Previsão da Selic.

Permite visualizar o histórico de sincronizações com a API do Banco Central,
disparar syncs por período, acompanhar transformação de features,
carga no PostgreSQL e upload para o Garage S3.

Diferente do pipeline original (Receita Federal), aqui não existem "meses"
com múltiplos arquivos — a série da Selic é contínua, então o controle é
feito por sincronização (sync_id) cobrindo um intervalo de datas.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.database import get_db, SessionLocal
from src.models.sync_control import SyncControl

router = APIRouter(prefix="/admin", tags=["Admin — Sincronização"])


# ─────────────────────────────────────────────────────────────────
# Sync — controle via API
# ─────────────────────────────────────────────────────────────────


@router.get(
    "/sync",
    summary="Dashboard de sincronização",
    description=(
        "Visão geral do histórico de sincronizações com a API do Banco Central. "
        "Mostra quantas sincronizações foram feitas, quantos registros cada "
        "uma trouxe e o status de cada uma (pendente, sincronizando, "
        "concluída ou com erro)."
    ),
    response_description="Resumo do histórico de sincronizações.",
)
async def dashboard_sync(db: Session = Depends(get_db)):
    """
    Retorna o estado completo das sincronizações, agrupado por status.
    """
    stats = (
        db.query(
            SyncControl.status,
            func.count(SyncControl.id).label("count"),
            func.sum(SyncControl.registros_inseridos).label("total_registros"),
        )
        .group_by(SyncControl.status)
        .all()
    )

    by_status = {
        row.status: {
            "count": row.count,
            "total_registros_inseridos": row.total_registros or 0,
        }
        for row in stats
    }

    total_syncs = sum(v["count"] for v in by_status.values())
    total_registros = sum(v["total_registros_inseridos"] for v in by_status.values())

    ultimas = (
        db.query(SyncControl)
        .order_by(SyncControl.id.desc())
        .limit(10)
        .all()
    )

    return {
        "summary": {
            "total_sincronizacoes": total_syncs,
            "total_registros_inseridos": total_registros,
            "by_status": by_status,
        },
        "ultimas_sincronizacoes": [
            {
                "id": s.id,
                "data_inicial": s.data_inicial,
                "data_final": s.data_final,
                "registros_inseridos": s.registros_inseridos,
                "status": s.status,
                "discovered_at": s.discovered_at.isoformat() if s.discovered_at else None,
                "synced_at": s.synced_at.isoformat() if s.synced_at else None,
            }
            for s in ultimas
        ],
    }


@router.get(
    "/sync/{sync_id}",
    summary="Detalhes de uma sincronização",
    description="Retorna os detalhes completos de uma sincronização específica pelo seu ID.",
    response_description="Detalhes da sincronização.",
)
async def detalhes_sync(
    sync_id: int,
    db: Session = Depends(get_db),
):
    """
    Detalhes de uma sincronização específica.

    - **sync_id**: ID do registro em sync_control
    """
    record = db.query(SyncControl).filter(SyncControl.id == sync_id).first()

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Sincronização com id={sync_id} não encontrada.",
        )

    return {
        "id": record.id,
        "serie_codigo": record.serie_codigo,
        "data_inicial": record.data_inicial,
        "data_final": record.data_final,
        "registros_inseridos": record.registros_inseridos,
        "status": record.status,
        "discovered_at": record.discovered_at.isoformat() if record.discovered_at else None,
        "synced_at": record.synced_at.isoformat() if record.synced_at else None,
        "error_message": record.error_message,
    }


@router.post(
    "/sync/discover",
    summary="Verificar disponibilidade da API do BCB",
    description=(
        "Consulta a API do Banco Central (SGS) para verificar se o serviço "
        "está acessível e retorna a data/valor mais recente disponível "
        "para a série da Selic."
    ),
    response_description="Resultado da verificação de disponibilidade.",
)
async def trigger_discovery():
    """
    Dispara a verificação de disponibilidade da série Selic na API do BCB.

    Não existe "descoberta de pastas" nesse domínio — a série é contínua,
    então esse endpoint apenas confirma que a API responde e mostra
    o último valor publicado.
    """
    from src.jobs.discovery import discover_available_data

    try:
        result = discover_available_data()
        return {
            "status": "success",
            "message": "API do Banco Central acessível.",
            "ultima_data": result.get("ultima_data"),
            "ultimo_valor": result.get("ultimo_valor"),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro na verificação: {str(e)}")


@router.post(
    "/sync",
    summary="Sincronizar série Selic para um período (assíncrono)",
    description=(
        "Dispara a sincronização da série histórica da Selic para um "
        "intervalo de datas, em segundo plano, para não travar a API."
    ),
    response_description="Confirmação do agendamento.",
)
async def trigger_sync(
    background_tasks: BackgroundTasks,
    data_inicial: str = Query(..., description="Data inicial no formato dd/MM/yyyy"),
    data_final: str = Query(..., description="Data final no formato dd/MM/yyyy"),
):
    """
    Dispara a sincronização (download) da série Selic para um período, em background.

    - **data_inicial**: Data inicial no formato dd/MM/yyyy
    - **data_final**: Data final no formato dd/MM/yyyy
    """

    def run_sync_in_background(inicio: str, fim: str):
        from src.jobs.sync import sync_selic

        bg_db = SessionLocal()
        try:
            sync_selic(bg_db, inicio, fim)
        finally:
            bg_db.close()

    background_tasks.add_task(run_sync_in_background, data_inicial, data_final)

    return {
        "status": "accepted",
        "message": f"Sincronização de {data_inicial} a {data_final} agendada em segundo plano.",
        "data_inicial": data_inicial,
        "data_final": data_final,
        "tip": "Acompanhe em GET /admin/sync",
    }


@router.post(
    "/sync/verify",
    summary="Verificar integridade da série local vs API do BCB",
    description=(
        "Compara o último valor disponível na API do Banco Central com o "
        "último valor sincronizado localmente, para detectar defasagem."
    ),
    response_description="Resultado da verificação de integridade.",
)
async def verify_integrity(db: Session = Depends(get_db)):
    """
    Verifica se a base local está desatualizada em relação à API do BCB.
    """
    from src.jobs.discovery import discover_available_data
    from src.models.selic import SelicSerie

    try:
        remoto = discover_available_data()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao consultar API do BCB: {str(e)}")

    ultimo_local = (
        db.query(SelicSerie).order_by(SelicSerie.data.desc()).first()
    )

    if not ultimo_local:
        return {
            "integrity": "sem_dados_locais",
            "message": "Nenhum dado sincronizado ainda. Rode /admin/sync primeiro.",
            "remoto": remoto,
        }

    return {
        "integrity": "ok" if str(ultimo_local.data) in remoto["ultima_data"] else "desatualizado",
        "ultimo_valor_local": {
            "data": ultimo_local.data.isoformat(),
            "valor": float(ultimo_local.valor),
        },
        "ultimo_valor_remoto": remoto,
    }


# ─────────────────────────────────────────────────────────────────
# Transform — controle via API
# ─────────────────────────────────────────────────────────────────


@router.post(
    "/transform",
    summary="Construir features de série temporal",
    description=(
        "Dispara a construção das features (lags + média móvel) a partir "
        "da série Selic sincronizada, em segundo plano, e salva o "
        "resultado em Parquet."
    ),
)
async def trigger_transform(background_tasks: BackgroundTasks):
    def run_transform_bg():
        from src.jobs.transform import build_features, save_features_parquet

        bg_db = SessionLocal()
        try:
            df = build_features(bg_db)
            if not df.empty:
                save_features_parquet(df)
        finally:
            bg_db.close()

    background_tasks.add_task(run_transform_bg)

    return {
        "status": "accepted",
        "message": "Transform agendado em segundo plano.",
        "tip": "Acompanhe em GET /admin/transform/status",
    }


@router.get(
    "/transform/status",
    summary="Status das features transformadas",
    description=(
        "Verifica se o arquivo de features (selic_features.parquet) existe, "
        "seu tamanho e quantidade de linhas."
    ),
)
async def transform_status():
    import os
    import pyarrow.parquet as pq
    from src.config import DATA_PROCESSED_DIR

    path = os.path.join(DATA_PROCESSED_DIR, "selic_features.parquet")
    existe = os.path.exists(path)

    row_count = None
    if existe:
        try:
            row_count = pq.read_metadata(path).num_rows
        except Exception:
            row_count = None

    return {
        "arquivo": path,
        "existe": existe,
        "tamanho_bytes": os.path.getsize(path) if existe else None,
        "row_count": row_count,
    }


# ─────────────────────────────────────────────────────────────────
# Load DB — controle via API
# ─────────────────────────────────────────────────────────────────


@router.post(
    "/load-db",
    summary="Carregar features no PostgreSQL",
    description=(
        "Carrega o Parquet de features (selic_features.parquet) na tabela "
        "selic_features, em segundo plano. Use ?if_exists=replace (padrão) "
        "para recarregar tudo, ou ?if_exists=append para acumular."
    ),
)
async def trigger_load_db(
    background_tasks: BackgroundTasks,
    if_exists: str = "replace",
):
    if if_exists not in ("append", "replace"):
        raise HTTPException(status_code=400, detail="if_exists deve ser 'append' ou 'replace'.")

    import os
    from src.config import DATA_PROCESSED_DIR

    path = os.path.join(DATA_PROCESSED_DIR, "selic_features.parquet")
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="Arquivo de features não encontrado. Rode /admin/transform primeiro.",
        )

    def run_load_db_bg(mode: str):
        from src.jobs.load_db import load_features_to_postgres

        bg_db = SessionLocal()
        try:
            load_features_to_postgres(db=bg_db, if_exists=mode)
        finally:
            bg_db.close()

    background_tasks.add_task(run_load_db_bg, if_exists)

    return {
        "status": "accepted",
        "message": f"Carga PostgreSQL agendada em segundo plano [if_exists={if_exists}].",
        "if_exists": if_exists,
        "tip": "Acompanhe em GET /admin/load-db/status",
    }


@router.get(
    "/load-db/status",
    summary="Status da carga PostgreSQL",
    description="Mostra quantos registros a tabela selic_features tem no PostgreSQL.",
)
async def load_db_status(db: Session = Depends(get_db)):
    from src.models.selic import SelicFeatures

    total = db.query(SelicFeatures).count()
    ultimo = db.query(SelicFeatures).order_by(SelicFeatures.data.desc()).first()

    return {
        "total_registros_selic_features": total,
        "ultima_data_carregada": ultimo.data.isoformat() if ultimo else None,
    }


# ─────────────────────────────────────────────────────────────────
# Load S3 — controle via API
# ─────────────────────────────────────────────────────────────────


@router.post(
    "/load-s3",
    summary="Upload para Garage S3 (raw + processed)",
    description=(
        "Envia dados para o S3 organizados em camadas:\n"
        "- `raw/selic/selic_serie.csv` — snapshot bruto da série completa\n"
        "- `processed/selic/selic_features.parquet` — features prontas para ML\n\n"
        "Use ?layer=raw para enviar apenas o snapshot, ?layer=processed para "
        "as features, ou ?layer=both (padrão) para ambos."
    ),
)
async def trigger_load_s3(
    background_tasks: BackgroundTasks,
    layer: str = "both",
):
    if layer not in ("raw", "processed", "both"):
        raise HTTPException(status_code=400, detail="layer deve ser 'raw', 'processed' ou 'both'.")

    def run_s3_bg(target_layer: str):
        from src.jobs.load_s3 import upload_raw_snapshot_to_s3, upload_processed_to_s3

        bg_db = SessionLocal()
        try:
            if target_layer in ("raw", "both"):
                upload_raw_snapshot_to_s3(bg_db)
            if target_layer in ("processed", "both"):
                upload_processed_to_s3()
        finally:
            bg_db.close()

    background_tasks.add_task(run_s3_bg, layer)

    return {
        "status": "accepted",
        "message": f"Upload S3 agendado (layer={layer}).",
        "layer": layer,
        "tip": "Acompanhe em GET /s3/objects?prefix=raw/selic/ ou GET /s3/objects?prefix=processed/selic/",
    }


@router.get(
    "/load-s3/status",
    summary="Status do S3 (raw + processed)",
    description="Verifica se os arquivos esperados estão presentes no bucket S3.",
)
async def load_s3_status():
    from src.utils import get_s3_client
    from src.config import S3_BUCKET_NAME

    s3 = get_s3_client()

    def _check(key: str) -> dict:
        try:
            meta = s3.head_object(Bucket=S3_BUCKET_NAME, Key=key)
            return {"exists": True, "size_bytes": meta.get("ContentLength", 0)}
        except Exception:
            return {"exists": False, "size_bytes": None}

    return {
        "raw": {"key": "raw/selic/selic_serie.csv", **_check("raw/selic/selic_serie.csv")},
        "processed": {
            "key": "processed/selic/selic_features.parquet",
            **_check("processed/selic/selic_features.parquet"),
        },
    }