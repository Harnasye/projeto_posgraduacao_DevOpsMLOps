"""
Models SQLAlchemy para os dados da Taxa Selic.

- SelicSerie: valores brutos da série histórica, direto da API do BCB (SGS).
- SelicFeatures: features derivadas (lags, médias móveis) usadas no treino
  do modelo de ML, persistidas para consulta rápida via API.

Referência: https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom
"""

from sqlalchemy import Column, Date, Numeric, String, Integer

from src.models.database import Base


class SelicSerie(Base):
    """Valores históricos da Meta Selic definida pelo Copom (série SGS 432)."""

    __tablename__ = "selic_serie"

    data = Column(Date, primary_key=True, comment="Data de referência do valor")
    valor = Column(Numeric(10, 6), nullable=False, comment="Taxa Selic (% a.a.)")
    serie_codigo = Column(String(10), nullable=False, default="432", comment="Código da série SGS")

    def __repr__(self):
        return f"<SelicSerie(data='{self.data}', valor={self.valor})>"


class SelicFeatures(Base):
    """
    Features de série temporal derivadas da SelicSerie, usadas para treino
    e serving do modelo de previsão (lags + média móvel).
    """

    __tablename__ = "selic_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(Date, nullable=False, index=True, comment="Data de referência da linha")
    lag_1 = Column(Numeric(10, 6), comment="Valor da Selic 1 dia útil atrás")
    lag_2 = Column(Numeric(10, 6), comment="Valor da Selic 2 dias úteis atrás")
    lag_3 = Column(Numeric(10, 6), comment="Valor da Selic 3 dias úteis atrás")
    lag_4 = Column(Numeric(10, 6), comment="Valor da Selic 4 dias úteis atrás")
    lag_5 = Column(Numeric(10, 6), comment="Valor da Selic 5 dias úteis atrás")
    media_movel_7 = Column(Numeric(10, 6), comment="Média móvel de 7 dias")
    target = Column(Numeric(10, 6), comment="Valor real do dia seguinte (usado no treino)")

    def __repr__(self):
        return f"<SelicFeatures(data='{self.data}', target={self.target})>"