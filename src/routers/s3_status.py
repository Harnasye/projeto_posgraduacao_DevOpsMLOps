"""
Router de monitoramento do Garage S3 (Object Storage local).

Endpoints para verificar conectividade, listar objetos no bucket,
consultar metadados e comparar estado do S3 vs sync_control (gap analysis)
para o pipeline de dados da Selic.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.config import S3_BUCKET_NAME
from src.utils import format_bytes as _format_bytes, get_s3_client as _get_s3_client
from src.models.database import get_db
from src.models.sync_control import SyncControl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/s3", tags=["S3 — Object Storage"])


@router.get(
    "/status",
    summary="Status do Garage S3",
    description=(
        "Verifica conectividade com o Garage S3 e lista os buckets disponíveis. "
        "Útil para diagnóstico rápido do ambiente."
    ),
    response_description="Status de conectividade e lista de buckets.",
)
async def s3_status():
    """
    Verifica se o Garage S3 está acessível e lista os buckets.
    """
    try:
        s3 = _get_s3_client()
        response = s3.list_buckets()

        buckets = [
            {
                "name": b["Name"],
                "created": b["CreationDate"].isoformat() if b.get("CreationDate") else None,
            }
            for b in response.get("Buckets", [])
        ]

        target_bucket_exists = any(b["name"] == S3_BUCKET_NAME for b in buckets)

        return {
            "status": "connected",
            "endpoint": s3.meta.endpoint_url,
            "target_bucket": S3_BUCKET_NAME,
            "target_bucket_exists": target_bucket_exists,
            "buckets": buckets,
            "total_buckets": len(buckets),
        }

    except Exception as e:
        return {
            "status": "error",
            "endpoint": s3.meta.endpoint_url,
            "target_bucket": S3_BUCKET_NAME,
            "error": str(e),
            "hint": (
                "Verifique se o Garage está rodando (podman compose ps) "
                "e se as credenciais em .env estão corretas."
            ),
        }


@router.get(
    "/objects",
    summary="Listar objetos no bucket S3",
    description=(
        "Lista todos os objetos no bucket principal (cnpj-data) com metadados: "
        "tamanho, última modificação, ETag."
    ),
    response_description="Lista de objetos com metadados.",
)
async def list_objects(
    prefix: str = Query(default="", description="Filtrar por prefixo (ex: 'raw/selic/')"),
    max_keys: int = Query(default=100, ge=1, le=1000, description="Quantidade máxima de objetos"),
):
    """
    Lista objetos no bucket S3 do Garage.
    """
    try:
        s3 = _get_s3_client()

        kwargs = {
            "Bucket": S3_BUCKET_NAME,
            "MaxKeys": max_keys,
        }
        if prefix:
            kwargs["Prefix"] = prefix

        response = s3.list_objects_v2(**kwargs)

        objects = []
        total_size = 0

        for obj in response.get("Contents", []):
            size = obj.get("Size", 0)
            total_size += size
            objects.append(
                {
                    "key": obj["Key"],
                    "size_bytes": size,
                    "size_human": _format_bytes(size),
                    "last_modified": obj["LastModified"].isoformat()
                    if obj.get("LastModified")
                    else None,
                    "etag": obj.get("ETag", "").strip('"'),
                    "storage_class": obj.get("StorageClass", "STANDARD"),
                }
            )

        return {
            "bucket": S3_BUCKET_NAME,
            "prefix": prefix or "(raiz)",
            "total_objects": len(objects),
            "total_size_bytes": total_size,
            "total_size_human": _format_bytes(total_size),
            "is_truncated": response.get("IsTruncated", False),
            "objects": objects,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar objetos no S3: {str(e)}",
        )


@router.get(
    "/objects/{key:path}",
    summary="Metadados de um objeto S3",
    description="Retorna metadados detalhados de um objeto específico no bucket.",
    response_description="Metadados completos do objeto.",
)
async def object_metadata(key: str):
    """
    Retorna metadados detalhados de um objeto no S3.
    """
    try:
        s3 = _get_s3_client()
        response = s3.head_object(Bucket=S3_BUCKET_NAME, Key=key)

        return {
            "bucket": S3_BUCKET_NAME,
            "key": key,
            "size_bytes": response.get("ContentLength", 0),
            "size_human": _format_bytes(response.get("ContentLength", 0)),
            "content_type": response.get("ContentType", ""),
            "last_modified": response["LastModified"].isoformat()
            if response.get("LastModified")
            else None,
            "etag": response.get("ETag", "").strip('"'),
            "metadata": response.get("Metadata", {}),
        }

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Objeto '{key}' não encontrado no bucket '{S3_BUCKET_NAME}': {str(e)}",
        )


@router.get(
    "/compare",
    summary="Gap analysis: S3 vs sync_control",
    description=(
        "Compara o que está no S3 (raw/selic e processed/selic) com o "
        "que está registrado em sync_control."
    ),
    response_description="Análise comparativa S3 vs banco de dados.",
)
async def compare_s3_vs_db(db: Session = Depends(get_db)):
    """
    Faz gap analysis entre o que existe no Garage S3 e o que está
    registrado no sync_control.
    """
    try:
        s3 = _get_s3_client()
        response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, MaxKeys=1000)

        s3_objects = {}
        s3_total_size = 0
        for obj in response.get("Contents", []):
            key = obj["Key"]
            size = obj.get("Size", 0)
            s3_total_size += size

            parts = key.split("/")
            if len(parts) >= 2 and parts[0] in ("raw", "processed"):
                layer = f"{parts[0]}/{parts[1]}" if len(parts) > 1 else parts[0]
            else:
                layer = "ROOT"

            if layer not in s3_objects:
                s3_objects[layer] = []
            s3_objects[layer].append(
                {
                    "key": key,
                    "size_bytes": size,
                    "size_human": _format_bytes(size),
                }
            )

    except Exception as e:
        s3_objects = {}
        s3_total_size = 0
        logger.warning(f"Erro ao acessar S3 para comparação: {e}")

    total_syncs = db.query(SyncControl).count()

    return {
        "summary": {
            "total_sincronizacoes_registradas": total_syncs,
            "s3_total_objects": sum(len(v) for v in s3_objects.values()),
            "s3_total_size_human": _format_bytes(s3_total_size),
        },
        "s3_details": {layer: objects for layer, objects in sorted(s3_objects.items())},
    }