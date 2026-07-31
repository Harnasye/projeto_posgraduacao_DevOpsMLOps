"""
Model SQLAlchemy para a tabela sync_control.

Controla o estado de sincronização da série histórica da Selic com a
API do Banco Central (SGS). Cada registro representa uma janela de
datas sincronizada, com seu status no pipeline.
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func

from src.models.database import Base


class SyncControl(Base):
    """Controle de sincronização da série Selic com o Banco Central."""

    __tablename__ = "sync_control"

    id = Column(Integer, primary_key=True, autoincrement=True)
    serie_codigo = Column(
        String(10), nullable=False, index=True, comment="Código da série SGS (ex: 432)"
    )
    data_inicial = Column(String(10), nullable=True, comment="Data inicial sincronizada (dd/MM/yyyy)")
    data_final = Column(String(10), nullable=True, comment="Data final sincronizada (dd/MM/yyyy)")
    registros_inseridos = Column(
        Integer, default=0, comment="Quantidade de novos registros inseridos nesta sincronização"
    )
    discovered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp de quando a sincronização foi registrada",
    )
    synced_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp de quando a sincronização foi concluída",
    )
    status = Column(
        Enum(
            "pending",
            "syncing",
            "synced",
            "error",
            name="sync_status",
        ),
        nullable=False,
        default="pending",
        comment="Estado atual da sincronização",
    )
    error_message = Column(String(1000), nullable=True, comment="Mensagem de erro, se houver")

    def __repr__(self):
        return (
            f"<SyncControl(serie_codigo='{self.serie_codigo}', "
            f"data_inicial='{self.data_inicial}', data_final='{self.data_final}', "
            f"status='{self.status}')>"
        )