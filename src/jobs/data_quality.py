"""
Job de qualidade de dados (Data Quality) para a série da Selic.

Roda verificações no PostgreSQL usando Great Expectations v1.0+,
garantindo que os valores da Selic estejam dentro de faixas plausíveis
e sem nulos antes de seguir para transform/train.
"""

import sys
import logging
import great_expectations as gx
import great_expectations.expectations as gxe
from src.config import DATABASE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_data_quality_checks():
    """
    Roda verificações de qualidade de dados na tabela selic_serie
    usando Great Expectations v1.0+.
    """
    logger.info("Inicializando contexto do Great Expectations (em memória)...")
    context = gx.get_context(mode="ephemeral")

    connection_string = DATABASE_URL
    if connection_string.startswith("postgresql://"):
        connection_string = connection_string.replace("postgresql://", "postgresql+psycopg2://", 1)

    # 1. Configurar Datasource
    datasource_name = "selic_postgres_db"
    datasource = context.data_sources.add_postgres(
        name=datasource_name,
        connection_string=connection_string,
    )

    # 2. Configurar Asset e Batch Definition
    asset_selic = datasource.add_table_asset(name="asset_selic_serie", table_name="selic_serie")
    batch_def_selic = asset_selic.add_batch_definition_whole_table("bd_selic_serie")

    # 3. Criar Expectation Suite
    suite_selic = gx.ExpectationSuite(name="selic_suite")
    suite_selic.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="valor"))
    suite_selic.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="data"))
    # A Selic historicamente ficou entre 0% e 50% a.a. — faixa de sanidade
    suite_selic.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(column="valor", min_value=0, max_value=50)
    )
    suite_selic = context.suites.add(suite_selic)

    # 4. Configurar Validation Definition
    vd_selic = context.validation_definitions.add(
        gx.ValidationDefinition(name="vd_selic_serie", data=batch_def_selic, suite=suite_selic)
    )

    # 5. Criar e rodar o Checkpoint
    checkpoint = gx.Checkpoint(
        name="selic_checkpoint",
        validation_definitions=[vd_selic],
    )
    checkpoint = context.checkpoints.add(checkpoint)

    logger.info("Executando Checkpoint v1.0+...")
    result = checkpoint.run()

    if not result.success:
        logger.error("Falha nos testes de Qualidade de Dados (Great Expectations v1.0+).")
        logger.error(str(result))
        sys.exit(1)

    logger.info("✅ Todos os Data Quality Checks passaram com sucesso!")


if __name__ == "__main__":
    run_data_quality_checks()