# 8. Estratégia de Model Serving

Data: 2026-07-11

## Status

Aceito

## Contexto

Com o desenvolvimento do modelo de previsão da Taxa Selic (usando RandomForestRegressor) treinado sobre
a série histórica sincronizada do Banco Central e versionado via MLflow e DVC, precisávamos de uma forma
de expor o modelo para ser consumido por outras aplicações, sem quebrar ou interferir nas APIs existentes
(consulta do histórico da Selic, dashboard).

A aplicação atual usa FastAPI, que é altamente performática e projetada para requisições assíncronas,
o que a torna ideal também para machine learning serving leve.

## Decisão

Adotamos a estratégia de **Model Serving Embutido na API FastAPI**, onde o modelo preditivo atua como
mais um "Router" dentro da aplicação principal (na rota `/predict`), em vez de instanciar um serviço
isolado.

Como o modelo é carregado:
1. No evento de `startup` do FastAPI (`@router.on_event("startup")`), o modelo "SelicPredictor" é
   baixado da URI correspondente do MLflow (apontando para o Garage/S3 local).
2. O modelo (usando a classe `mlflow.pyfunc.load_model`) fica armazenado em memória (variável global
   do módulo router).
3. A rota `POST /predict/` aceita payloads no formato Pydantic contendo as features de série temporal
   (`lag_1` a `lag_5`, `media_movel_7`) e retorna o valor previsto para o próximo dia útil da Selic.
4. Para evitar que a API caia, envolvemos a carga do modelo num `try-except` de modo que, se o modelo
   não existir no repositório ainda (ex: treino nunca executado), o serviço devolve "503 Service
   Unavailable" na rota `/predict`, mas os outros endpoints de consulta da Selic continuam operantes.

## Consequências

**Positivas:**
- Redução da complexidade arquitetural: sem necessidade de orquestrar um container extra rodando o
  servidor próprio do MLflow (`mlflow models serve`) ou Seldon Core.
- Permite reaproveitar a infraestrutura, monitoramento e métricas de tráfego (middlewares) que já temos
  na API.
- Maior velocidade e menos "cold-starts" no tempo de resposta para inferência, pois o modelo fica
  carregado diretamente na memória da API base.
- Como o modelo de regressão é leve (RandomForestRegressor com poucas features), o tempo de carregamento
  no startup é rápido quando o MLflow está disponível.

**Negativas:**
- Se o MLflow estiver indisponível (ex: container pausado para economia de memória em ambiente de
  desenvolvimento), o startup da API pode demorar vários minutos devido às tentativas de retry com
  backoff exponencial da biblioteca de requisições do MLflow, antes de desistir e seguir com o serviço
  de previsão indisponível (503). Uma melhoria futura seria tornar essa carga assíncrona/não-bloqueante.
- Se o modelo for muito pesado, ele competirá por memória (RAM) e CPU com a API regular de consulta ao
  banco de dados, podendo impactar a escalabilidade do sistema transacional de dados. (Para este
  laboratório, o modelo é leve o suficiente para não representar perigo).