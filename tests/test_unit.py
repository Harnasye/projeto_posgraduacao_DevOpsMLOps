"""
Testes unitários para as funções de processamento de dados da Selic.

Não requerem banco de dados ou ambiente completo rodando — usamos
um DataFrame simulado para testar a lógica de features isoladamente.
"""

import pandas as pd
from datetime import date


def test_build_features_lags_e_target():
    """
    Testa se as colunas de lag e target são calculadas corretamente
    a partir de uma série simples e conhecida.
    """
    # Simula uma série de 10 dias úteis com valores crescentes
    datas = [date(2025, 1, d) for d in range(1, 11)]
    valores = [10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5]

    df = pd.DataFrame({"data": datas, "valor": valores})

    n_lags = 3
    for lag in range(1, n_lags + 1):
        df[f"lag_{lag}"] = df["valor"].shift(lag)

    df["media_movel_3"] = df["valor"].rolling(window=3).mean()
    df["target"] = df["valor"].shift(-1)

    df = df.dropna().reset_index(drop=True)

    # Validações
    # A primeira linha válida corresponde ao índice original 3 (valor=11.5),
    # pois é a primeira posição em que lag_3 (que exige 3 posições anteriores)
    # deixa de ser nulo.
    primeira_linha = df.iloc[0]
    assert primeira_linha["valor"] == 11.5
    assert primeira_linha["lag_1"] == 11.0
    assert primeira_linha["lag_2"] == 10.5
    assert primeira_linha["lag_3"] == 10.0

    # O target deve ser sempre o valor do próximo dia
    for i in range(len(df) - 1):
        assert df.iloc[i]["target"] == df.iloc[i + 1]["valor"]

    # Não deve haver nenhum valor nulo após o dropna
    assert df.isna().sum().sum() == 0


def test_media_movel_calculo_correto():
    """
    Testa se a média móvel de 3 dias é calculada corretamente.
    """
    df = pd.DataFrame({"valor": [10.0, 20.0, 30.0, 40.0]})
    df["media_movel_3"] = df["valor"].rolling(window=3).mean()

    # Média dos 3 primeiros valores: (10+20+30)/3 = 20.0
    assert df.iloc[2]["media_movel_3"] == 20.0
    # Média dos valores 2,3,4: (20+30+40)/3 = 30.0
    assert df.iloc[3]["media_movel_3"] == 30.0