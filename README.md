# Adaptive Music Explorer

Busca musical adaptativa sobre o dataset **FMA Medium**, construída em torno de
duas estruturas de dados protagonistas:

- **Skip List** — índice acústico probabilístico que reduz o espaço de busca e
  recupera candidatos acusticamente próximos.
- **Splay Tree** — estrutura autoajustável que modela o perfil de reprodução do
  usuário, aproximando da raiz as músicas acessadas recentemente.

O núcleo de estruturas é escrito em **C++**; o pré-processamento dos dados e a
interface (**Streamlit**) são escritos em **Python**. O foco do projeto está nas
estruturas de dados — a interface e o dataset existem para demonstrá-las.

Veja o plano completo em `docs/plano_implementacao.md`.

## Estrutura do repositório

```
core/          Núcleo C++ (Skip List, Splay Tree, similaridade, Acoustic Key)
preprocessing/ Pipeline Python de preparação do FMA -> tracks_processed.csv
app/           Aplicação Streamlit (4 páginas)
benchmark/     Benchmarks C++ (Skip List e Splay Tree) + resultados CSV
tests/         Testes unitários do núcleo C++
data/          raw/ (FMA baixado) e processed/ (dataset gerado)
docs/          Plano e documentação experimental
```

## Build do núcleo C++

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure   # roda os testes
```

Binários gerados em `build/`:
`ame_core_app`, `benchmark_skiplist`, `benchmark_splay`, `benchmark_similarity`.

## Dataset: FMA Medium (Kaggle)

Baixe os arquivos em [FMA — Small & Medium no Kaggle](https://www.kaggle.com/datasets/imsparsh/fma-free-music-archive-small-medium).
São necessários os metadados (`tracks.csv`, `features.csv`, `genres.csv`) e os
áudios de `fma_medium`. O Medium inclui as faixas rotuladas `small` e `medium`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r preprocessing/requirements.txt -r app/requirements.txt
python preprocessing/build_dataset.py --import-zip "/caminho/archive.zip"
```

O pipeline produz o CSV com 44 características, parâmetros de normalização e
um relatório de faixas/áudios ausentes. Também aceita pastas extraídas e áudios
em outro disco. Veja [data/README.md](data/README.md) para as opções de importação,
validação dos áudios e instruções completas.

## Interface (Streamlit)

```bash
pip install -r app/requirements.txt
streamlit run app/app.py
```

## Estado atual e validação

As estruturas C++, o pipeline FMA e a ponte Streamlit estão implementados.
A interface oferece busca no catálogo completo, reprodução da faixa e das
recomendações e registro explícito de acessos na Splay Tree. A personalização
do ranking pelo perfil continua opcional e não está implementada.

O dataset não é distribuído neste repositório: é necessário baixá-lo e executar
a importação. Os testes usam amostras sintéticas no formato oficial FMA;
qualidade de recomendação e reprodução de todos os áudios devem ser avaliadas
com os arquivos reais.

```bash
python -m unittest discover -s tests -p 'test_dataset.py' -v
./build/benchmark_similarity  # usa o CSV processado, executado na raiz
```

O benchmark gera Recall@10 e tempos para diferentes janelas, incluindo busca
exaustiva. Structures Lab exibe os resultados salvos. Para uma demonstração
sintética separada, use `./build/benchmark_similarity --synthetic`.

## Equipe

Cinco integrantes, com divisão de responsabilidades descrita no plano (§39):
Skip List / Acoustic Key, Splay Tree, processamento do FMA, Streamlit, e
benchmarks / integração.
