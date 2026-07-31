# ADR 0005: Processamento Chunked com PyArrow para Arquivos Massivos

## Status
Superado *(ver nota de contexto abaixo)*

## Contexto histórico

Este ADR foi escrito durante a fase do projeto voltada à ingestão de dados de CNPJ da Receita Federal.
Os arquivos CSV públicos (como "Simples.zip" ou "Estabelecimentos") chegavam, descompactados, a vários
Gigabytes. Carregar esses dataframes inteiros no Pandas resultava em *Out Of Memory* (OOM) no container
da API.

## Decisão (original)

Implementamos uma leitura assíncrona baseada em chunks de 50.000 linhas usando o iterador nativo do Pandas.
Cada chunk passava pelas regras de negócio e era incrementado em um arquivo físico Parquet local via
`pyarrow.parquet.ParquetWriter`.

## Consequências (originais)

- **Positivas**: Uso estável e baixo de RAM. Arquivos infinitamente grandes podiam ser convertidos
  localmente sem estourar a máquina.
- **Negativas**: O progresso era assíncrono, então a leitura dos metadados (como *row_count*) pela API
  de status só funcionava *após* a finalização total da escrita (com fechamento do writer). Isso causou
  bugs temporários visuais na interface.

## Nota de atualização — Migração para Previsão da Taxa Selic

Com a migração do projeto para o domínio de previsão da Taxa Selic (dados do Banco Central via API SGS),
o volume de dados mudou radicalmente de escala: a série histórica completa possui uma linha por dia útil
(dezenas de milhares de registros no total, não bilhões), cabendo facilmente em memória.

Por esse motivo, o `src/jobs/transform.py` atual **não usa mais chunking com PyArrow** — as features de
série temporal (lags, médias móveis) são construídas com um único `pandas.DataFrame` em memória, sem
necessidade de processamento incremental.

Este ADR é mantido no repositório por seu valor histórico e didático (demonstra como lidar com datasets
que não cabem em memória), mas a técnica descrita **não se aplica ao pipeline atual**. Caso o projeto
volte a lidar com datasets de grande volume no futuro (ex: séries de alta frequência, tick-by-tick),
esta decisão deve ser revisitada.

## Referências

- Aula 01, §1.5 — Processamento de Grandes Volumes de Dados