# ADR 0002 — Estrutura da API, Jobs Batch e Código Compartilhado

- **Data:** 2026-06-26
- **Status:** Aceito
- **Decisores:** Equipe do Projeto

## Contexto

O projeto possui dois modos de execução distintos:

1. **API (live):** Servidor FastAPI que atende requisições HTTP em tempo real — consultas do histórico
   da Taxa Selic, previsão via modelo de ML e dashboard administrativo de sincronização.
2. **Jobs batch:** Scripts executados sob demanda ou agendados que realizam operações pesadas — verificação
   de disponibilidade na API do Banco Central, sincronização da série histórica, construção de features e
   treinamento do modelo.

Ambos compartilham modelos de dados (SQLAlchemy) e configuração (variáveis de ambiente). Precisamos de uma
estrutura que evite duplicação de código, mantenha separação de responsabilidades e seja fácil de navegar
para alunos com diferentes níveis de experiência.

## Decisão

Adotamos a seguinte estrutura dentro de `src/`:

src/
├── main.py # Entrypoint da API FastAPI
├── config.py # Settings centralizados (env vars)
├── models/ # SQLAlchemy models (compartilhados)
│ ├── database.py # Engine, Session, Base
│ ├── selic.py # Tabelas selic_serie e selic_features
│ └── sync_control.py # Tabela sync_control
├── routers/ # Endpoints da API (live)
│ ├── selic.py # Consultas do histórico da Selic
│ ├── admin.py # Dashboard de sincronização
│ ├── ml_serving.py # Model Serving (previsão)
│ └── ml_tracking.py # Gerenciamento de experimentos MLflow
├── jobs/ # Scripts batch (offline)
│ ├── discovery.py # Verifica disponibilidade da API do BCB
│ ├── sync.py # Sincronização incremental da série
│ ├── transform.py # Construção de features de série temporal
│ ├── load_db.py # Carga das features para PostgreSQL
│ ├── load_s3.py # Upload para Garage S3
│ └── train.py # Treinamento do modelo de regressão
└── ingest.py # Orquestrador do pipeline batch

## Justificativa

1. **Separação clara:** `routers/` contém apenas lógica HTTP; `jobs/` contém apenas lógica batch.
   Nenhum job importa FastAPI, nenhum router importa lógica de sincronização/transformação diretamente
   (a exceção é o `admin.py`, que dispara jobs em background via `BackgroundTasks`).
2. **Modelos compartilhados:** `models/` é importado por ambos os lados, garantindo uma única fonte
   de verdade para os schemas de banco (`selic_serie`, `selic_features`, `sync_control`).
3. **Config centralizado:** `config.py` usa variáveis de ambiente, alinhado com o 12-Factor App.
   O mesmo arquivo é usado por API e jobs, evitando duplicação de credenciais e da URL da API do BCB.
4. **Entrypoints independentes:**
   - API: `uvicorn src.main:app` (rodando via container)
   - Pipeline batch: `python -m src.ingest --data-inicial 01/01/2015 --data-final 31/12/2025` (via `make ingest`)
5. **Escalabilidade didática:** A estrutura é simples o suficiente para a Aula 01, mas comporta
   extensões futuras (Aula 02: testes em `tests/`, Aula 03: MLflow, DVC).

## Consequências

### Positivas
- Alunos entendem visualmente onde cada responsabilidade mora.
- Jobs podem rodar em containers separados (ex: CronJob no Kubernetes na Aula 02).
- Fácil de testar unitariamente (cada job é uma função pura, cada router é um endpoint isolado).

### Negativas
- Mais arquivos para navegar comparado a um `main.py` monolítico.
- Alunos iniciantes podem se confundir com a quantidade de módulos no início.

## Referências

- [FastAPI Project Structure](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [12-Factor App — Config](https://12factor.net/config)
- Aula 01, §1.6 — Architecture Decision Records