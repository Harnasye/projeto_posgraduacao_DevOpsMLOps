"""
Testes End-to-End (E2E) para a API de Previsão da Selic.

Requerem o banco de dados rodando e a aplicação acessível.
Utilizamos o TestClient do FastAPI para simular requisições HTTP
no ambiente isolado (dentro do container).
"""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """
    Testa se o endpoint de health check está respondendo corretamente.
    Valida a integração básica da API.
    """
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "timestamp" in data


def test_root_endpoint():
    """
    Testa se o endpoint raiz retorna as informações da API.
    """
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "Running"
    assert "selic" in data.get("endpoints", {})


def test_admin_sync_dashboard_empty_db():
    """
    Testa o endpoint do dashboard admin.
    Mesmo com banco vazio ou parcialmente populado, deve retornar estrutura correta.
    """
    response = client.get("/admin/sync")
    assert response.status_code == 200

    data = response.json()
    assert "summary" in data
    assert "total_sincronizacoes" in data["summary"]
    assert "ultimas_sincronizacoes" in data


def test_selic_ultimo_sem_dados():
    """
    Testa o endpoint /selic/ultimo quando ainda não há dados sincronizados.
    Deve retornar 404 de forma controlada, não quebrar.
    """
    response = client.get("/selic/ultimo")
    # Pode ser 200 (se já houver dados de outro teste) ou 404 (banco vazio)
    assert response.status_code in (200, 404)