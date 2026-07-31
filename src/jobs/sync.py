"""
Job de sincronização da série histórica da Taxa Selic.

Consulta a API do Banco Central (SGS) para um intervalo de datas e
insere os valores novos na tabela selic_serie, evitando duplicatas.

Uso:
    python -m src.jobs.sync --data-inicial 01/01/2020 --data-final 31/12/2025
"""

import logging
from datetime import datetime

import requests
from sqlalchemy.orm import Session

from src.config import BCB_BASE_URL, SELIC_SERIE_CODE
from src.exceptions import DataDiscoveryError
from src.models.selic import SelicSerie
from src.models.sync_control import SyncControl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def sync_selic(db: Session, data_inicial: str, data_final: str) -> dict:
    """
    Baixa a série Selic entre duas datas (formato dd/MM/yyyy) e insere no banco.
    A API do BCB limita consultas a no máximo 10 anos por chamada, então
    intervalos maiores são automaticamente divididos em blocos de até 10 anos.
    """
    from datetime import datetime, timedelta

    dt_inicial = datetime.strptime(data_inicial, "%d/%m/%Y")
    dt_final = datetime.strptime(data_final, "%d/%m/%Y")

    total_inseridos = 0
    total_recebidos = 0
    total_ja_existentes = 0

    cursor = dt_inicial
    while cursor <= dt_final:
        # Bloco de até 10 anos menos 1 dia, respeitando o limite da API
        bloco_final = min(cursor.replace(year=cursor.year + 10) - timedelta(days=1), dt_final)

        bloco_inicial_str = cursor.strftime("%d/%m/%Y")
        bloco_final_str = bloco_final.strftime("%d/%m/%Y")

        logger.info(f"Sincronizando bloco: {bloco_inicial_str} a {bloco_final_str}")

        url = (
            f"{BCB_BASE_URL}/bcdata.sgs.{SELIC_SERIE_CODE}/dados"
            f"?formato=json&dataInicial={bloco_inicial_str}&dataFinal={bloco_final_str}"
        )

        response = requests.get(url, timeout=60)
        response.raise_for_status()
        dados = response.json()
        total_recebidos += len(dados)

        for item in dados:
            data_valor = datetime.strptime(item["data"], "%d/%m/%Y").date()
            existe = db.query(SelicSerie).filter(SelicSerie.data == data_valor).first()
            if existe:
                total_ja_existentes += 1
                continue

            registro = SelicSerie(
                data=data_valor,
                valor=float(item["valor"]),
                serie_codigo=SELIC_SERIE_CODE,
            )
            db.add(registro)
            total_inseridos += 1

        db.commit()
        cursor = bloco_final + timedelta(days=1)

    sync_record = SyncControl(
        serie_codigo=SELIC_SERIE_CODE,
        data_inicial=data_inicial,
        data_final=data_final,
        registros_inseridos=total_inseridos,
        status="synced",
    )
    db.add(sync_record)
    db.commit()

    logger.info(
        f"Sync concluído: {total_inseridos} novos registros, "
        f"{total_ja_existentes} já existentes (pulados)."
    )

    return {
        "data_inicial": data_inicial,
        "data_final": data_final,
        "registros_recebidos": total_recebidos,
        "registros_inseridos": total_inseridos,
        "registros_ja_existentes": total_ja_existentes,
    }


if __name__ == "__main__":
    import argparse
    from src.models.database import SessionLocal, init_db

    parser = argparse.ArgumentParser(
        description="Sincroniza a série histórica da Taxa Selic (BCB/SGS).",
        epilog="Exemplo: python -m src.jobs.sync --data-inicial 01/01/2020 --data-final 31/12/2025",
    )
    parser.add_argument("--data-inicial", required=True, help="Data inicial no formato dd/MM/yyyy")
    parser.add_argument("--data-final", required=True, help="Data final no formato dd/MM/yyyy")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        result = sync_selic(db, args.data_inicial, args.data_final)
        logger.info(f"Resultado: {result}")
    finally:
        db.close()

response = requests.get(url, timeout=60)
response.raise_for_status()

if not response.text.strip():
    logger.warning(f"API retornou vazio para o período {data_inicial} a {data_final} — sem dados nesse intervalo.")
    dados = []
else:
    dados = response.json()