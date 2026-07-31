# ADR 0001 — Usar Podman em vez de Docker

- **Data:** 2026-06-26
- **Status:** Aceito
- **Decisores:** Equipe do Projeto

## Contexto

O projeto precisa de um runtime de containers OCI para construir e executar o pipeline de dados localmente.
As duas opções mais populares no mercado são **Docker** e **Podman**.

Em ambientes corporativos e educacionais, a segurança e a simplicidade operacional são prioritárias.
Docker exige um daemon com privilégios elevados (`dockerd` rodando como root), o que representa um
ponto único de falha e um vetor de ataque. Além disso, mudanças recentes no licenciamento do Docker Desktop
impõem custos para empresas com mais de 250 funcionários.

## Decisão

Adotamos **Podman** como runtime de containers para o projeto.

## Justificativa

1. **Rootless por padrão:** Podman roda sem privilégios de administrador, reduzindo a superfície de ataque.
2. **Daemonless:** Não existe processo central persistente. Cada comando `podman` é um processo independente,
   eliminando o ponto único de falha do daemon Docker.
3. **Compatibilidade OCI:** Podman segue os padrões da Open Container Initiative (OCI), garantindo que
   imagens construídas com Podman funcionem em qualquer runtime compatível (Docker, Kubernetes, etc.).
4. **Drop-in replacement:** `alias docker=podman` funciona para a maioria dos casos de uso, facilitando a
   migração de times que já conhecem Docker.
5. **Licenciamento livre:** Podman é software livre (Apache 2.0), sem restrições de uso corporativo.
6. **Podman Compose:** Suporta o formato `compose.yaml` via `podman-compose`, mantendo a mesma experiência
   de orquestração local.

## Consequências

### Positivas
- Maior segurança no ambiente de desenvolvimento local.
- Sem custo de licenciamento.
- Alunos aprendem práticas de segurança desde o início.

### Negativas
- Menor ecossistema de plugins e integrações comparado ao Docker.
- Algumas ferramentas de CI (como GitHub Actions) usam Docker nativamente; o runner não terá Podman
  instalado por padrão, exigindo `docker build` no CI (compatível com OCI).
- Documentação e tutoriais da comunidade ainda são majoritariamente voltados para Docker.

### Riscos
- Incompatibilidades pontuais entre Podman Compose e Docker Compose em features avançadas (profiles, etc.).

## Referências

- [Podman Docs](https://podman.io/docs)
- [Open Container Initiative](https://opencontainers.org/)
- Aula 01, §1.2 — Containers: OCI, Podman e Boas Práticas
