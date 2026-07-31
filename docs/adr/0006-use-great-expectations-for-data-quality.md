# ADR 0006: Validação de Qualidade de Dados com Great Expectations

## Status
Aceito

## Contexto
O processo de ingestão insere os dados sincronizados da API do Banco Central diretamente na tabela
`selic_serie` do PostgreSQL. Para atender aos critérios do Encontro 02 ("Data quality checks"),
precisávamos de uma ferramenta que validasse os dados no pós-carga — por exemplo, garantindo que os
valores da Selic estejam dentro de uma faixa plausível e sem datas nulas. Inicialmente o *Soda Core*
havia sido considerado, porém a equipe prefere ferramentas 100% integráveis em ecossistemas Python
nativos para padronização.

## Decisão
Adotamos o **Great Expectations (GX)** para rodar verificações de Data Quality (DQ) direto na tabela
`selic_serie` do PostgreSQL. As regras estão estruturadas via código nativo no script
`src/jobs/data_quality.py`, configurando *Datasources*, *Expectation Suites* e *Checkpoints*
programaticamente (em memória). As expectativas incluem: ausência de nulos em `data` e `valor`, e
valores de `valor` dentro da faixa histórica plausível (0% a 50% a.a.).

## Consequências
- **Positivas**: Como o Great Expectations é 100% Python, não precisamos de arquivos YAML desconexos
  (como no Soda). Isso facilita testes unitários e a manipulação dinâmica de expectativas.
- **Negativas**: A curva de aprendizado inicial da API do GX pode ser mais alta, e a execução em banco
  exige que a sincronização no Postgres já tenha sido concluída (verificação reativa).