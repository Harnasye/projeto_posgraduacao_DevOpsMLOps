# 7. Estratégia de Versionamento de Dados (DVC)

Data: 2026-07-11

## Status

Aceito

## Contexto

Com a integração de processos de Machine Learning ao projeto de previsão da Taxa Selic (MLOps),
tornou-se necessário gerenciar as versões dos datasets utilizados para o treinamento do modelo. Dados
(em formatos `.csv`, `.parquet` e afins) frequentemente ultrapassam os limites razoáveis de tamanho do
Git e não devem ser "commitados" diretamente no repositório — mesmo a série da Selic sendo relativamente
pequena, mantém-se a boa prática de não versionar dados brutos/processados via Git. O uso do Git LFS
(Large File Storage) poderia ser uma alternativa, mas carece de funcionalidades avançadas para pipelines
de dados e machine learning.

Para garantir a reprodutibilidade dos experimentos, precisávamos de uma solução que vinculasse os dados
armazenados fora do repositório Git com as versões do código.

## Decisão

Adotamos o **DVC (Data Version Control)** como ferramenta padrão de versionamento de dados no projeto,
integrado ao **Garage (S3-compatible Object Storage)** local.

As seguintes regras se aplicam:
1. O diretório de snapshots brutos (`data/raw/selic/`) passa a ser gerenciado pelo DVC.
2. Os dados de fato (*payloads*) serão enviados (pushed) para o bucket `selic-data` do Garage via API S3
   (`http://storage:3900`).
3. Somente os arquivos de metadados (`.dvc`) gerados pelo DVC serão armazenados no Git.
4. Qualquer script de Machine Learning ou transformação que dependa dos dados deverá garantir que os
   dados corretos foram previamente sincronizados (via `dvc pull`).

## Consequências

**Positivas:**
- Reprodutibilidade de modelos garantida: a hash do arquivo de dados fica "congelada" no commit exato
  do código que treinou o modelo.
- Economia de armazenamento no Git.
- Uso transparente da nossa infraestrutura existente do S3 (Garage).
- DVC funciona nativamente no ecossistema Python sem a necessidade de infraestruturas servidoras pesadas
  (como DVC Studio) para casos iniciais.

**Negativas:**
- Adiciona uma leve sobrecarga cognitiva aos desenvolvedores, que agora precisam rodar `dvc push/pull`
  juntamente com `git push/pull`.
- Requer que o ambiente local (ou o container com suporte a DVC) tenha as credenciais do Garage
  configuradas para empurrar dados, além de acesso ao Git (o DVC exige um repositório Git inicializado
  para funcionar em modo padrão).