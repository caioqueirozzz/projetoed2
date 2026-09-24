# Data

Os arquivos do FMA **não** são versionados (ver `.gitignore`). Baixe-os
localmente.

## `raw/`

Coloque aqui os arquivos brutos do **FMA Medium**:

- `tracks.csv` — metadados das faixas
- `features.csv` — features acústicas pré-calculadas (Librosa)
- `genres.csv` — gêneros
- áudio do FMA Medium (para reprodução)

Fonte: https://github.com/mdeff/fma (FMA Medium ≈ 25.000 faixas, ~30s cada).

## `processed/`

Saída do pipeline de pré-processamento
(`preprocessing/build_dataset.py`):

- `tracks_processed.csv` — id, título, artista, gênero e features normalizadas.

Este é o dataset consumido pelo núcleo C++ para construir a Skip List.
