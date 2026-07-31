"""
Inicialização do pacote models.
Importando todos os models aqui garante que o SQLAlchemy Base os conheça
antes de rodar o Base.metadata.create_all().
"""

from src.models.sync_control import SyncControl
from src.models.selic import SelicSerie, SelicFeatures

__all__ = [
    "SyncControl",
    "SelicSerie",
    "SelicFeatures",
]