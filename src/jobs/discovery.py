"""
Job de descoberta de dados disponíveis na API do Banco Central (SGS).

Diferente da Receita Federal, a API do BCB não exige "descoberta de pastas":
os dados já estão organizados numa série temporal contínua. Este job apenas
verifica se o serviço está acessível e retorna a data mais recente disponível.

URL base: https://api.bcb.gov.br/dados/serie
Documentação: https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom
"""

import logging

import requests

from src.config import BCB_BASE_URL, SELIC_SERIE_CODE
from src.exceptions import DataDiscoveryError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def discover_available_data() -> dict:
    """
    Verifica conectividade com a API do Banco Central e retorna o
    último valor disponível da série Selic.
    """
    url = f"{BCB_BASE_URL}/bcdata.sgs.{SELIC_SERIE_CODE}/dados/ultimos/1?formato=json"
    logger.info(f"Verificando disponibilidade da série Selic (BCB): {url}")

    try:
        response = requests.get(url, timeout=30)
    except requests.RequestException as e:
        raise DataDiscoveryError(f"Falha de conexão com a API do BCB: {e}")

    if response.status_code != 200:
        raise DataDiscoveryError(
            f"API do BCB retornou status inesperado: {response.status_code}"
        )

    try:
        dados = response.json()
    except ValueError as e:
        raise DataDiscoveryError(f"Resposta inválida (não é JSON) da API do BCB: {e}")

    if not dados:
        raise DataDiscoveryError("API do BCB retornou lista vazia para a série Selic.")

    ultimo = dados[0]
    logger.info(f"Última data disponível: {ultimo['data']} — valor: {ultimo['valor']}")

    return {
        "serie_codigo": SELIC_SERIE_CODE,
        "ultima_data": ultimo["data"],
        "ultimo_valor": ultimo["valor"],
    }


if __name__ == "__main__":
    result = discover_available_data()
    logger.info(f"Resultado: {result}")