.PHONY: help build up down test clean clean-volumes discover sync ingest logs lint format s3-status s3-list transform transform-status load-db load-db-status load-s3 train data-quality
.DEFAULT_GOAL := help

# Detecta se podman está disponível, caso contrário usa docker (útil para CI)
DOCKER_CMD ?= $(shell command -v podman 2> /dev/null || echo docker)
COMPOSE_CMD ?= $(shell command -v podman-compose 2> /dev/null || echo "$(DOCKER_CMD) compose")

help: ## Mostra os comandos disponíveis
	@echo "Uso: make [comando]"
	@echo ""
	@echo "Comandos Disponíveis:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
	@echo ""

build: ## Constrói a imagem do container
	@echo "🔨 Construindo a imagem com $(DOCKER_CMD)..."
	$(DOCKER_CMD) build -f ContainerFile -t fastapi-selic .

up: ## Sobe o ambiente completo (API + PostgreSQL + Garage + MLflow + Metabase)
	@echo "🚀 Subindo o ambiente..."
	$(COMPOSE_CMD) up -d --build

down: ## Derruba o ambiente local
	@echo "🛑 Derrubando o ambiente..."
	$(COMPOSE_CMD) down

test: ## Executa os testes automatizados (requer 'make up' antes)
	@echo "🧪 Executando testes (certifique-se que executou 'make up' antes)..."
	$(COMPOSE_CMD) exec api python -m pytest tests/ -v

lint: ## Executa análise estática de código e formatação com Ruff (modo check)
	@echo "🧹 Executando Ruff (Linter & Formatter Check)..."
	$(COMPOSE_CMD) exec -u root api ruff check .
	$(COMPOSE_CMD) exec -u root api ruff format --check .

format: ## Aplica as formatações recomendadas pelo Ruff
	@echo "✨ Formatando código com Ruff..."
	$(COMPOSE_CMD) exec -u root api ruff format .
	$(COMPOSE_CMD) exec -u root api ruff check --fix .

clean: ## Para containers e remove imagens órfãs (NÃO apaga volumes/dados)
	@echo "🧹 Parando containers e removendo imagens órfãs..."
	$(COMPOSE_CMD) down --remove-orphans
	$(DOCKER_CMD) image prune -f
	@echo "ℹ️  Volumes preservados. Use 'make clean-volumes' para apagar dados."

clean-volumes: ## ⚠️  DESTRÓI todos os volumes (postgres + garage). DADOS SERÃO PERDIDOS!
	@echo "⚠️  ATENÇÃO: Isso vai apagar TODOS os dados (PostgreSQL + Garage S3)."
	@read -p "Digite 'sim' para confirmar: " confirm && [ "$$confirm" = "sim" ] || (echo "Cancelado." && exit 1)
	$(COMPOSE_CMD) down -v --remove-orphans
	$(DOCKER_CMD) system prune -f
	@echo "✅ Volumes e dados removidos."

discover: ## Verifica disponibilidade da série Selic na API do Banco Central
	@echo "🔍 Verificando disponibilidade da série Selic (BCB)..."
	$(COMPOSE_CMD) exec api python -m src.jobs.discovery

sync: ## Sincroniza a série Selic (ex: make sync START=01/01/2020 END=31/12/2025)
	@echo "📥 Sincronizando série Selic de $(START) a $(END)..."
	$(COMPOSE_CMD) exec api python -m src.jobs.sync --data-inicial $(START) --data-final $(END)

ingest: ## Executa o pipeline completo (ex: make ingest START=01/01/2020 END=31/12/2025)
	@echo "⚙️ Executando pipeline completo..."
	$(COMPOSE_CMD) exec api python -m src.ingest --data-inicial $(START) --data-final $(END)

transform: ## Constrói as features de série temporal via API
	@echo "⚙️  Disparando transform via API..."
	@curl -s -X POST "http://localhost:8000/admin/transform" | python3 -m json.tool

transform-status: ## Status do arquivo de features transformadas
	@echo "📊 Status do transform..."
	@curl -s "http://localhost:8000/admin/transform/status" | python3 -m json.tool

load-db: ## Carrega features no PostgreSQL (ex: make load-db MODE=replace)
	@echo "🐘 Disparando carga PostgreSQL [mode=$(or $(MODE),replace)]..."
	@curl -s -X POST "http://localhost:8000/admin/load-db?if_exists=$(or $(MODE),replace)" | python3 -m json.tool

load-db-status: ## Status da carga PostgreSQL
	@echo "📊 Status da carga PostgreSQL..."
	@curl -s "http://localhost:8000/admin/load-db/status" | python3 -m json.tool

load-s3: ## Upload de snapshot raw + features processadas para o Garage S3
	@echo "☁️  Disparando upload S3..."
	@curl -s -X POST "http://localhost:8000/admin/load-s3" | python3 -m json.tool

train: ## Treina o modelo de previsão da Selic e registra no MLflow
	@echo "🤖 Treinando modelo de previsão da Selic..."
	$(COMPOSE_CMD) exec api python -m src.jobs.train

s3-status: ## Mostra status de conectividade do Garage S3
	@echo "🪣 Verificando status do Garage S3..."
	@curl -s http://localhost:8000/s3/status | python3 -m json.tool

s3-list: ## Lista objetos no bucket S3 (ex: make s3-list PREFIX=raw/selic/)
	@echo "📋 Listando objetos no S3..."
	@curl -s "http://localhost:8000/s3/objects$(if $(PREFIX),?prefix=$(PREFIX),)" | python3 -m json.tool

logs: ## Mostra logs em tempo real
	$(COMPOSE_CMD) logs -f

data-quality: ## Executa testes de qualidade de dados com Great Expectations
	@echo "🧪 Executando Great Expectations Checks..."
	$(COMPOSE_CMD) exec api python -m src.jobs.data_quality