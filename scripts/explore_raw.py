"""
Script de exploração e validação da série histórica da Selic sincronizada.

NÃO modifica nenhum dado.
Lê a tabela selic_serie do PostgreSQL para:
  1. Verificar cobertura de datas (gaps no calendário de dias úteis)
  2. Detectar valores fora da faixa histórica plausível (0% a 50% a.a.)
  3. Estatísticas básicas: min, max, média, desvio padrão
  4. Verificar duplicatas de data (não deveriam existir, pois é PK)

Uso:
    python -m scripts.explore_raw
    python -m scripts.explore_raw --nrows 1000
"""

import argparse
import logging
import os
import sys

import pandas as pd

# Adiciona raiz ao path para importar src.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.database import SessionLocal
from src.models.selic import SelicSerie

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SEPARATOR = "─" * 70

# Faixa histórica plausível da Selic (% a.a.) — usada como sanity check
SELIC_MIN_ESPERADO = 0.0
SELIC_MAX_ESPERADO = 50.0


def explore_selic_serie(nrows: int = None) -> None:
    """
    Explora a série histórica da Selic sincronizada no banco,
    reportando cobertura de datas, valores fora da faixa e duplicatas.
    """
    db = SessionLocal()
    try:
        query = db.query(SelicSerie).order_by(SelicSerie.data)
        if nrows:
            query = query.limit(nrows)
        registros = query.all()
    finally:
        db.close()

    if not registros:
        logger.error("Nenhum dado encontrado em selic_serie. Rode 'make sync' primeiro.")
        sys.exit(1)

    df = pd.DataFrame([{"data": r.data, "valor": float(r.valor)} for r in registros])

    print(f"\n{SEPARATOR}")
    print("  EXPLORAÇÃO DA SÉRIE HISTÓRICA — TAXA SELIC")
    print(SEPARATOR)
    print(f"  Total de registros      : {len(df)}")
    print(f"  Data inicial             : {df['data'].min()}")
    print(f"  Data final               : {df['data'].max()}")
    print(f"  Valor mínimo             : {df['valor'].min():.4f} % a.a.")
    print(f"  Valor máximo             : {df['valor'].max():.4f} % a.a.")
    print(f"  Valor médio              : {df['valor'].mean():.4f} % a.a.")
    print(f"  Desvio padrão            : {df['valor'].std():.4f}")
    print(SEPARATOR)

    issues = []
    warnings = []

    # ── Check 1: valores fora da faixa plausível ──
    fora_da_faixa = df[
        (df["valor"] < SELIC_MIN_ESPERADO) | (df["valor"] > SELIC_MAX_ESPERADO)
    ]
    if not fora_da_faixa.empty:
        issues.append(
            f"{len(fora_da_faixa)} registros com valor fora da faixa "
            f"[{SELIC_MIN_ESPERADO}, {SELIC_MAX_ESPERADO}]% a.a."
        )

    # ── Check 2: duplicatas de data ──
    duplicatas = df[df.duplicated(subset=["data"], keep=False)]
    if not duplicatas.empty:
        issues.append(f"{len(duplicatas)} datas duplicadas encontradas (não deveria acontecer).")

    # ── Check 3: nulos ──
    nulos = df["valor"].isna().sum()
    if nulos > 0:
        issues.append(f"{nulos} valores nulos encontrados.")

    # ── Check 4: gaps grandes entre datas consecutivas (possível falha de sync) ──
    df_sorted = df.sort_values("data")
    df_sorted["gap_dias"] = df_sorted["data"].diff().dt.days
    gaps_grandes = df_sorted[df_sorted["gap_dias"] > 10]  # mais de 10 dias corridos sem dado
    if not gaps_grandes.empty:
        warnings.append(
            f"{len(gaps_grandes)} gaps de mais de 10 dias entre sincronizações consecutivas. "
            "Pode indicar falha de sync em algum período — considere rodar sync novamente "
            "cobrindo essas datas."
        )

    print("\n  RESULTADO DA VALIDAÇÃO")
    print(SEPARATOR)

    if issues:
        for issue in issues:
            print(f"  ❌ ISSUE: {issue}")
    if warnings:
        for w in warnings:
            print(f"  ⚠️  WARNING: {w}")

    if not issues and not warnings:
        print("  ✅ Série consistente, sem issues ou warnings detectados.")

    print(SEPARATOR)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Explora a série histórica da Selic sincronizada, sem modificar nada.",
        epilog="Exemplo: python -m scripts.explore_raw --nrows 1000",
    )
    parser.add_argument(
        "--nrows", type=int, default=None, help="Limitar a N registros mais antigos (padrão: todos)"
    )
    args = parser.parse_args()

    explore_selic_serie(nrows=args.nrows)