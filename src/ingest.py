"""
Orquestrador do pipeline de ingestão e previsão da Taxa Selic.

Coordena a execução dos jobs na ordem correta:
1. Discovery — verifica disponibilidade da API do Banco Central (SGS)
2. Sync — baixa o histórico da série Selic para um intervalo de datas
3. Transform — constrói features de série temporal (lags, médias móveis)
4. Load DB — persiste as features numa tabela para consulta via API
5. Load S3 — envia snapshots (raw + features) para o Garage S3
6. Train — treina o modelo de regressão e registra no MLflow (opcional)

Uso:
    # Pipeline completo para um intervalo de datas:
    python -m src.ingest --data-inicial 01/01/2020 --data-final 31/12/2025

    # Apenas discovery (sem download):
    python -m src.ingest --discover-only
"""

import argparse
import logging

from src.models.database import init_db, SessionLocal
from src.jobs.discovery import discover_available_data
from src.jobs.sync import sync_selic
from src.jobs.transform import build_features, save_features_parquet
from src.jobs.load_db import load_features_to_postgres
from src.jobs.load_s3 import upload_processed_to_s3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline(
    data_inicial: str = None,
    data_final: str = None,
    discover_only: bool = False,
):
    """
    Executa o pipeline completo de ingestão e preparação de dados da Selic.

    Parâmetros:
    - data_inicial: Data inicial no formato dd/MM/yyyy. Se None, faz apenas discovery.
    - data_final: Data final no formato dd/MM/yyyy.
    - discover_only: Se True, executa apenas o discovery sem download.
    """
    logger.info("=" * 60)
    logger.info("PIPELINE DE PREVISÃO — TAXA SELIC (BANCO CENTRAL)")
    logger.info("=" * 60)

    # Inicializa banco de dados (cria tabelas se não existirem)
    init_db()
    logger.info("✅ Banco de dados inicializado.")

    db = SessionLocal()

    try:
        # Step 1: Discovery
        logger.info("\n📌 Step 1/5 — Discovery")
        discovery_result = discover_available_data()
        logger.info(f"Discovery: {discovery_result}")

        if discover_only:
            logger.info("Flag --discover-only ativada. Parando aqui.")
            return

        if not data_inicial or not data_final:
            logger.info(
                "Nenhum intervalo de datas especificado. Execute novamente com "
                "--data-inicial e --data-final para sincronizar."
            )
            return

        # Step 2: Sync
        logger.info(f"\n📌 Step 2/5 — Sync ({data_inicial} a {data_final})")
        sync_result = sync_selic(db, data_inicial, data_final)
        logger.info(f"Sync: {sync_result}")

        # Step 3: Transform
        logger.info("\n📌 Step 3/5 — Transform (features de série temporal)")
        df_features = build_features(db)
        save_features_parquet(df_features)
        logger.info(f"Transform concluído: {df_features.shape[0]} linhas de features.")

        # Step 4: Load DB
        logger.info("\n📌 Step 4/5 — Load PostgreSQL (features)")
        rows = load_features_to_postgres(db=db)
        logger.info(f"Load DB: {rows:,} registros inseridos em selic_features")

        # Step 5: Load S3
        logger.info("\n📌 Step 5/5 — Load S3")
        s3_result = upload_processed_to_s3()
        logger.info(f"Load S3: {s3_result.get('uploaded', 0)} arquivos enviados")

        logger.info("\n" + "=" * 60)
        logger.info("✅ PIPELINE CONCLUÍDO COM SUCESSO")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ PIPELINE FALHOU: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline de previsão da Taxa Selic com dados do Banco Central.",
        epilog="Exemplo: python -m src.ingest --data-inicial 01/01/2020 --data-final 31/12/2025",
    )
    parser.add_argument("--data-inicial", help="Data inicial no formato dd/MM/yyyy")
    parser.add_argument("--data-final", help="Data final no formato dd/MM/yyyy")
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Executa apenas discovery (sem download/transformação/carga)",
    )
    args = parser.parse_args()

    run_pipeline(
        data_inicial=args.data_inicial,
        data_final=args.data_final,
        discover_only=args.discover_only,
    )