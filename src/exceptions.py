"""
Definição de exceções customizadas do sistema.
Centraliza o tratamento de erros para melhor monitoramento e padronização.
"""


class CnpjAppError(Exception):
    """Classe base para todas as exceções customizadas da aplicação."""

    pass


class DataDiscoveryError(CnpjAppError):
    """Levantada quando ocorre um problema na fase de discovery (ex: API do
    Banco Central fora do ar, instabilidade de rede, mudança no formato
    de resposta do serviço SGS)."""

    pass