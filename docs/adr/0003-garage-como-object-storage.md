# ADR 0003 — Garage como Object Storage S3-compatível

- **Data:** 2026-06-26
- **Status:** Aceito
- **Decisores:** Equipe do Projeto

## Contexto

O pipeline de dados precisa de um object storage compatível com a API S3 para armazenar artefatos brutos
(arquivos `.zip` da Receita Federal) e dados processados (arquivos `.parquet`). Esse storage simula um
data lake local durante o desenvolvimento, antes de migrar para soluções cloud (AWS S3, GCS, Azure Blob).

As opções avaliadas foram:

| Ferramenta | Licença | Status | Observações |
|---|---|---|---|
| **MinIO** | AGPLv3 (restritiva) | Mudança de licença e descontinuação parcial | Problemas de licenciamento para uso comercial |
| **Garage** | AGPLv3 | Ativo, mantido pela Deuxfleurs | Leve, S3-compatível, ideal para dev/edge |
| **LocalStack** | Freemium | Ativo | Emula toda a AWS, overkill para nosso caso |

## Decisão

Adotamos **Garage** como object storage S3-compatível para desenvolvimento local.

## Justificativa

1. **S3-compatível:** Suporta as operações essenciais da API S3 (PutObject, GetObject, ListBucket),
   permitindo uso direto com `boto3` e qualquer SDK S3.
2. **Leve e rápido:** Binário único, sem JVM, sem dependências pesadas. Ideal para subir via compose
   em segundos.
3. **Projetado para edge/self-hosted:** Diferente do MinIO (focado em enterprise), Garage é projetado
   para cenários de baixo recurso — perfeito para ambiente de desenvolvimento local.
4. **Ativo e mantido:** Projeto open-source ativo, com releases regulares e documentação clara.
5. **Configuração simples:** Um único container com variáveis de ambiente para credenciais e porta.

## Consequências

### Positivas
- Alunos aprendem a interagir com API S3 usando `boto3`, skill diretamente transferível para AWS/GCP.
- Ambiente local completo sem dependência de cloud.
- Container leve, compose sobe rápido.

### Negativas
- Garage não suporta todas as features avançadas do S3 (ex: lifecycle policies, versioning avançado).
- Menor comunidade e ecossistema comparado ao MinIO (historicamente).
- Requer configuração inicial de cluster (mesmo que single-node para dev).

### Riscos
- Se o projeto precisar de features S3 avançadas no futuro, pode ser necessário migrar para outra solução.

## Referências

- [Garage — S3-compatible Object Storage](https://garagehq.deuxfleurs.fr/)
- [Garage Quick Start](https://garagehq.deuxfleurs.fr/documentation/quick-start/)
- Aula 01, §1.3 — Orquestração Local: Podman Compose
