# pos-ia-eng-devops 🚀

![Python](https://img.shields.io/badge/python-3.14-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.137.0.svg?logo=fastapi)
![Docker](https://img.shields.io/badge/Podman-ready-blue?logo=podman)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)
<!-- TODO: Pesquise sobre https://shields.io/ e aprenda a usar badges reais. Eles ajudam a comunicar o status, versão e qualidade do seu projeto de forma profissional! -->

> [!NOTE]
> Este repositório utiliza ferramentas de Inteligência Artificial para apoiar seu desenvolvimento. Durante as aulas para fins educativos, testamos as habilidades de "Vibe Code" e exploramos a preparação do repositório orientada a **Spec Driven Development**.

Repositório base para o projeto da disciplina de **DevOps e MLOps Aplicado a Engenharia de Dados**.
Pipeline completo de dados públicos da Taxa Selic (Banco Central) — da ingestão à previsão.

---

## 🎯 Objetivo do Projeto

Criar um pipeline de dados completo e robusto que:
1. Verifica disponibilidade e sincroniza a série histórica da Taxa Selic via API do Banco Central (SGS).
2. Constrói features de série temporal (lags + médias móveis) a partir dos dados sincronizados (transform).
3. Carrega as features no PostgreSQL para consulta e analytics (load-db).
4. Persiste snapshots brutos e features processadas no Garage S3 em camadas (load-s3).
5. Expõe API REST (FastAPI) para controle de todo o pipeline e consulta do histórico.
6. Treina um modelo de regressão (RandomForest) para prever o próximo valor da Selic, rastreado via MLflow.
7. Oferece dashboards via Metabase conectado ao PostgreSQL.
8. É orquestrado e conteinerizado localmente com Podman e Podman-Compose.

---

## 🏗️ Arquitetura

```text
┌──────────────────┐
│  Banco Central   │
│  API SGS (REST)  │
└────────┬─────────┘
         │ discovery + sync
         ▼
┌──────────────────┐     ┌─────────────────────────────────────┐
│  /tmp/data/raw/  │────▶│  Garage S3 (selic-data bucket)      │
│  selic_serie.csv │     │  ├── raw/selic/*.csv     (snapshot) │
└────────┬─────────┘     │  └── processed/selic/*.parquet      │
         │ transform     └─────────────────────────────────────┘
         ▼
┌──────────────────┐     ┌─────────────────────┐
│  /tmp/processed/ │────▶│  PostgreSQL 17       │
│  *.parquet       │     │  selic_serie         │
│  (staging)       │     │  selic_features      │
└──────────────────┘     │  sync_control        │
                         └────────┬──────────────┘
                                  │
                         ┌────────▼──────────────┐
                         │  Metabase (:3000)     │
                         │  FastAPI  (:8000/docs)│
                         │  MLflow   (:5001)     │
                         └───────────────────────┘
```

> **DVC**: Snapshots brutos em `data/raw/selic/` são versionados usando DVC, com o `Garage S3` como remote de storage (`dvc push/pull`).
> **MLflow**: Usado para rastrear o treinamento do modelo de regressão (RandomForestRegressor), suas métricas (MAE, RMSE, R²) e gerenciar os artefatos (Model Registry). O FastAPI carrega a versão `latest` do modelo na inicialização.

---

## 🏗️ Estrutura do Repositório

```
├── ContainerFile          # Multi-stage build + usuário rootless (appuser)
├── Makefile               # Targets para todo o pipeline
├── compose.yaml           # API, PostgreSQL, Garage S3, Metabase, MLflow
├── config/garage.toml     # Configuração do Garage S3
├── docs/adr/              # Decisões de Arquitetura (ADRs)
├── k8s/                   # 🔜 Kubernetes Manifests (Lab 2.3) — não utilizado, ver ADR 0004
├── scripts/
│   ├── explore_raw.py     # Exploração da série Selic sincronizada, sem modificar
│   └── init_garage.sh     # Setup manual do Garage (se necessário)
├── src/
│   ├── config.py          # Configurações via variáveis de ambiente (12-Factor)
│   ├── exceptions.py      # Exceções customizadas
│   ├── ingest.py          # Orquestrador do pipeline batch
│   ├── main.py            # API FastAPI com documentação OpenAPI
│   ├── utils.py           # Funções utilitárias compartilhadas
│   ├── jobs/              # Tarefas do pipeline
│   │   ├── discovery.py   # Verifica disponibilidade da API do BCB
│   │   ├── sync.py        # Sincroniza a série histórica da Selic
│   │   ├── transform.py   # Constrói features de série temporal (lags, médias móveis)
│   │   ├── load_db.py     # Features → PostgreSQL
│   │   ├── load_s3.py     # Upload para Garage S3 (raw + processed)
│   │   ├── data_quality.py# Data Quality com Great Expectations
│   │   └── train.py       # Pipeline de Treino (RandomForestRegressor + MLflow)
│   ├── models/            # SQLAlchemy
│   │   ├── database.py    # Engine, Session, Base
│   │   ├── selic.py       # Models: SelicSerie, SelicFeatures
│   │   └── sync_control.py# Controle de sincronização (estado do pipeline)
│   └── routers/           # Endpoints HTTP
│       ├── admin.py       # Dashboard, sync, transform, load-db, load-s3
│       ├── selic.py       # Consulta do histórico da Selic
│       ├── s3_status.py   # Status do Garage S3 e gap analysis
│       ├── ml_serving.py  # Model Serving (carrega de MLflow no startup)
│       └── ml_tracking.py # Gerenciamento de experimentos MLflow
└── tests/
    ├── test_unit.py       # Testes unitários (features de série temporal)
    └── test_e2e.py        # Testes E2E (API endpoints)
```
---

## 💻 Como Iniciar

### Pré-requisitos
- [Podman](https://podman.io/) instalado.
- [Podman Compose](https://github.com/containers/podman-compose).
- Make (opcional, porém recomendado).
- [DVC](https://dvc.org/) (opcional, para versionamento de dados).

### Pipeline Completo

```bash
# 1. Subir todos os serviços
make up

# 2. Verificar disponibilidade da API do Banco Central
make discover

# 3. Sincronizar a série histórica da Selic
# Atenção: a API do BCB limita consultas a intervalos de até 10 anos por chamada
make sync START=01/01/2015 END=31/12/2025

# 4. Construir as features de série temporal (lags + média móvel)
make transform

# 5. Carregar as features no PostgreSQL
make load-db

# 6. Upload para Garage S3 (raw + processed)
make load-s3

# 7. Rodar Data Quality Checks
make data-quality

# 8. Treinar o modelo de previsão com MLflow
make train
```

### Monitoramento

```bash
# Status do transform
make transform-status

# Status da carga PostgreSQL
make load-db-status

# Listar objetos no S3
make s3-list PREFIX=raw/selic/

# Dashboard de sincronizações
curl -s http://localhost:8000/admin/sync | python3 -m json.tool
```

### Acessos

| Serviço | URL |
|---|---|
| **API (Swagger UI)** | http://localhost:8000/docs |
| **Metabase** | http://localhost:3000 |
| **PostgreSQL** | `localhost:5432` (user: postgres, db: selic) |
| **Garage S3** | `localhost:3900` |
| **MLflow** | http://localhost:5001 |

---

## 📡 API — Endpoints Principais

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/admin/sync` | Dashboard de sincronização |
| `POST` | `/admin/sync/discover` | Verificar disponibilidade da API do BCB |
| `POST` | `/admin/sync?data_inicial=...&data_final=...` | Sincronizar período (background) |
| `POST` | `/admin/sync/verify` | Verificar integridade local vs API do BCB |
| `POST` | `/admin/transform` | Construir features de série temporal |
| `GET` | `/admin/transform/status` | Status das features transformadas |
| `POST` | `/admin/load-db` | Carregar features no PostgreSQL |
| `POST` | `/admin/load-s3` | Upload S3 (raw + processed) |
| `GET` | `/s3/objects` | Listar objetos no bucket |
| `GET` | `/selic/historico` | Histórico recente da Selic |
| `GET` | `/selic/ultimo` | Último valor sincronizado |
| `GET` | `/selic/periodo?data_inicial=...&data_final=...` | Busca por intervalo de datas |
| `POST` | `/predict/` | Previsão do próximo valor da Selic via modelo carregado do MLflow |

Documentação completa com exemplos: **http://localhost:8000/docs**

---

## 📐 Decisões de Arquitetura

Consulte os ADRs em `docs/adr/`:
- [ADR 0001](docs/adr/0001-usar-podman-em-vez-de-docker.md) — Podman em vez de Docker
- [ADR 0002](docs/adr/0002-estrutura-api-e-jobs-batch.md) — Estrutura API + Jobs batch
- [ADR 0003](docs/adr/0003-garage-como-object-storage.md) — Garage como Object Storage
- [ADR 0004](docs/adr/0004-use-podman-compose-instead-of-kubernetes.md) — Podman em vez de Kubernetes
- [ADR 0005](docs/adr/0005-use-pyarrow-for-large-files.md) — Processamento de dados (contexto histórico do dataset CNPJ)
- [ADR 0006](docs/adr/0006-use-great-expectations-for-data-quality.md) — Validação de qualidade com Great Expectations
- [ADR 0007](docs/adr/0007-estrategia-de-versionamento-de-dados-dvc.md) — Estratégia de Versionamento com DVC
- [ADR 0008](docs/adr/0008-estrategia-de-model-serving.md) — Estratégia de Model Serving com MLflow

---

## ⚠️ Notas sobre a API do Banco Central (SGS)

- Consultas por período são **limitadas a 10 anos** por chamada — intervalos maiores retornam erro HTTP 406. O `sync.py` deve ser chamado em blocos de até 10 anos.
- Períodos sem dados disponíveis podem retornar uma resposta HTTP 200 com corpo vazio, em vez de uma lista JSON vazia — o job de sync trata esse caso como "sem dados", não como erro.
- Documentação oficial: [dadosabertos.bcb.gov.br](https://dadosabertos.bcb.gov.br/)

---

> 💡 **OBS**: Use `make help` para ver todos os targets disponíveis no Makefile.