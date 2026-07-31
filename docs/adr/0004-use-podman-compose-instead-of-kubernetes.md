# ADR 0004: Uso de Podman e Compose em vez de Kubernetes

## Status
Aceito

## Contexto
O projeto avalia pipelines de engenharia de dados (Dataops e MLOps). Embora as orientações iniciais mencionem ferramentas como Kubernetes e Kind para orquestração, operar esses clusters consome bastante recurso de máquina e adiciona complexidade desnecessária à fase de ingestão e experimentação. 

## Decisão
Decidimos utilizar **Podman** e **Podman Compose** para toda a stack local de dados (PostgreSQL, Garage S3, FastAPI, Metabase, MLflow). 

## Consequências
- **Positivas**: Redução drástica de uso de RAM e CPU. Ambiente reproduzível mais rápido e familiar aos desenvolvedores.
- **Negativas**: Perde-se a experiência real de gerenciar _Deployments_ e _Pods_ no Kubernetes, mas atinge-se o mesmo objetivo de um ambiente containerizado imutável para a disciplina.
