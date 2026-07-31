# ADR 0002 — Estrutura da API, Jobs Batch e Código Compartilhado

- **Data:** 2026-06-26
- **Status:** Aceito
- **Decisores:** Equipe do Projeto

## Contexto

O projeto possui dois modos de execução distintos:

1. **API (live):** Servidor FastAPI que atende requisições HTTP em tempo real — consultas de dados CNPJ
   e dashboard administrativo de sincronização.
2. **Jobs batch:** Scripts executados sob demanda ou agendados que realizam operações pesadas — descoberta
   de dados disponíveis, download, transformação e carga.

Ambos compartilham modelos de dados (SQLAlchemy) e configuração (variáveis de ambiente). Precisamos de uma
estrutura que evite duplicação de código, mantenha separação de responsabilidades e seja fácil de navegar
para alunos com diferentes níveis de experiência.

## Decisão

Adotamos a seguinte estrutura dentro de `src/`:

```
src/
├── main.py              # Entrypoint da API FastAPI
├── config.py            # Settings centralizados (env vars)
├── models/              # SQLAlchemy models (compartilhados)
│   ├── database.py      # Engine, Session, Base
│   ├── empresa.py       # Tabela cnpj_empresas
│   └── sync_control.py  # Tabela sync_control
├── routers/             # Endpoints da API (live)
│   ├── empresas.py      # Consultas CNPJ
│   └── admin.py         # Dashboard de sincronização
├── jobs/                # Scripts batch (offline)
│   ├── discovery.py     # Descobre universo de dados
│   ├── sync.py          # Download seletivo
│   ├── transform.py     # Transformação pandas
│   ├── load_db.py       # Carga para PostgreSQL
│   └── load_s3.py       # Upload para Garage S3
└── ingest.py            # Orquestrador do pipeline batch
```

## Justificativa

1. **Separação clara:** `routers/` contém apenas lógica HTTP; `jobs/` contém apenas lógica batch.
   Nenhum job importa FastAPI, nenhum router importa lógica de download/transformação.
2. **Modelos compartilhados:** `models/` é importado por ambos os lados, garantindo uma única fonte
   de verdade para schemas de banco.
3. **Config centralizado:** `config.py` usa variáveis de ambiente, alinhado com o 12-Factor App.
   O mesmo arquivo é usado por API e jobs, evitando duplicação de credenciais.
4. **Entrypoints independentes:**
   - API: `uvicorn src.main:app` (rodando via container)
   - Pipeline batch: `python -m src.ingest --year-month 2023-05` (rodando via `make ingest`)
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
